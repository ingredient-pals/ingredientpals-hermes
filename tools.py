"""Tool handlers for the IngredientPals Hermes plugin.

Each handler follows the Hermes contract:
    def handler(args: dict, **kwargs) -> str

Returns a JSON string on every path (success and error alike). Never raises.

HTTP is done with the standard library only so the plugin has zero external
dependencies.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.ingredientpals.com"
DEFAULT_TIMEOUT_S = 120
MAX_REDIRECTS = 5


def _base_url() -> str:
    return (os.environ.get("INGREDIENTPALS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _api_key() -> str | None:
    return os.environ.get("INGREDIENTPALS_API_KEY")


def _request(method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
    """Make a JSON HTTP request to the IngredientPals API.

    Returns (status_code, parsed_payload). Never raises — errors from the
    transport layer are turned into a synthetic payload.
    """
    api_key = _api_key()
    if not api_key:
        return 0, {
            "error": {
                "code": "missing_api_key",
                "message": (
                    "INGREDIENTPALS_API_KEY is not set. Mint a key at "
                    "https://ingredientpals.com (user menu -> API Keys) and "
                    "run `hermes plugins install ingredient-pals/"
                    "ingredientpals-hermes` or add it to ~/.hermes/.env."
                ),
            }
        }

    url = f"{_base_url()}{path}"
    data: bytes | None = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "ingredientpals-hermes-plugin/1.0.0",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    # Follow redirects manually so POST/DELETE are preserved with body on
    # 307/308 responses. Python's stdlib redirect handler converts POST to
    # GET on 301/302/303 (which is correct) but raises on 307/308 from
    # non-GET methods, which is what the IngredientPals apex-to-www
    # redirect used to trigger.
    current_url = url
    current_method = method
    current_data = data
    raw = ""
    status = 0
    for hop in range(MAX_REDIRECTS + 1):
        req = urllib_request.Request(
            url=current_url, data=current_data, method=current_method, headers=headers
        )
        try:
            with urllib_request.urlopen(req, timeout=DEFAULT_TIMEOUT_S) as resp:
                status = resp.getcode()
                raw = resp.read().decode("utf-8", errors="replace")
                break
        except urllib_error.HTTPError as e:
            status = e.code
            if status in (301, 302, 303, 307, 308) and hop < MAX_REDIRECTS:
                location = e.headers.get("Location") if e.headers else None
                if location:
                    next_url = urllib_parse.urljoin(current_url, location)
                    # 301/302/303 convert POST/PUT/DELETE to GET; 307/308
                    # preserve method and body.
                    if status in (301, 302, 303) and current_method != "HEAD":
                        current_method = "GET"
                        current_data = None
                        headers.pop("Content-Type", None)
                    current_url = next_url
                    continue
            try:
                raw = e.read().decode("utf-8", errors="replace")
            except Exception:
                raw = ""
            break
        except urllib_error.URLError as e:
            return 0, {
                "error": {
                    "code": "network_error",
                    "message": f"Could not reach {current_url}: {e.reason}",
                }
            }
        except Exception as e:  # noqa: BLE001
            return 0, {
                "error": {"code": "unexpected_error", "message": str(e)},
            }


    if not raw:
        return status, None
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, {"raw": raw}


def _result(status: int, payload: Any) -> str:
    """Standardize a response payload for the LLM."""
    if status and 200 <= status < 300:
        return json.dumps(payload if payload is not None else {"ok": True})

    # Error path — bubble up code/message if the server provided them.
    err = (payload or {}).get("error") if isinstance(payload, dict) else None
    if isinstance(err, dict):
        out = {
            "error": {
                "code": err.get("code") or "http_error",
                "message": err.get("message") or f"HTTP {status}",
                "status": status,
            }
        }
        if "details" in err:
            out["error"]["details"] = err["details"]
        return json.dumps(out)

    return json.dumps({
        "error": {
            "code": "http_error",
            "message": f"HTTP {status}" if status else "Request failed",
            "status": status,
            "body": payload,
        }
    })


# --- Search / read -------------------------------------------------------

def search_recipes(args: dict, **kwargs) -> str:
    qs: list[tuple[str, str]] = []
    q = args.get("q")
    if isinstance(q, str) and q:
        qs.append(("q", q))
    for key in ("mealTypes", "dietary", "tags"):
        v = args.get(key)
        if isinstance(v, list) and v:
            qs.append((key, ",".join(str(item) for item in v)))
    for key in ("minRating", "limit", "offset"):
        v = args.get(key)
        if isinstance(v, (int, float)):
            qs.append((key, str(int(v))))
    suffix = f"?{urllib_parse.urlencode(qs)}" if qs else ""
    status, payload = _request("GET", f"/api/v1/recipes/search{suffix}")
    return _result(status, payload)


def get_recipe(args: dict, **kwargs) -> str:
    recipe_id = args.get("id")
    if not isinstance(recipe_id, int):
        return json.dumps({"error": {"code": "bad_request", "message": "`id` (integer) is required."}})
    status, payload = _request("GET", f"/api/v1/recipes/{recipe_id}")
    return _result(status, payload)


# --- Drafts --------------------------------------------------------------

_ALLOWED_SOURCE_TYPES = {"prompt", "imageUrl", "imageBase64", "url", "youtube"}


def _sanitize_source(source: Any) -> dict | str:
    """Return a server-acceptable source dict, or an error message string."""
    if not isinstance(source, dict):
        return "`source` must be an object."
    t = source.get("type")
    if t not in _ALLOWED_SOURCE_TYPES:
        return f"`source.type` must be one of {sorted(_ALLOWED_SOURCE_TYPES)}."

    if t == "prompt":
        if not isinstance(source.get("prompt"), str) or not source["prompt"].strip():
            return "source.type='prompt' requires a non-empty `prompt` string."
        return {"type": "prompt", "prompt": source["prompt"]}
    if t == "imageUrl":
        if not isinstance(source.get("imageUrl"), str):
            return "source.type='imageUrl' requires an `imageUrl` string."
        return {"type": "imageUrl", "imageUrl": source["imageUrl"]}
    if t == "imageBase64":
        if not isinstance(source.get("data"), str) or not isinstance(source.get("mimeType"), str):
            return "source.type='imageBase64' requires `data` and `mimeType`."
        return {
            "type": "imageBase64",
            "data": source["data"],
            "mimeType": source["mimeType"],
        }
    if t in ("url", "youtube"):
        if not isinstance(source.get("url"), str):
            return f"source.type='{t}' requires a `url` string."
        return {"type": t, "url": source["url"]}
    return f"Unhandled source type: {t}"


def create_recipe_draft(args: dict, **kwargs) -> str:
    source = _sanitize_source(args.get("source"))
    if isinstance(source, str):
        return json.dumps({"error": {"code": "bad_request", "message": source}})
    status, payload = _request("POST", "/api/v1/recipes", {"source": source})
    return _result(status, payload)


def remix_recipe_draft(args: dict, **kwargs) -> str:
    recipe_id = args.get("id")
    prompt = args.get("prompt")
    if not isinstance(recipe_id, int):
        return json.dumps({"error": {"code": "bad_request", "message": "`id` (integer) is required."}})
    if not isinstance(prompt, str) or not prompt.strip():
        return json.dumps({"error": {"code": "bad_request", "message": "`prompt` (non-empty string) is required."}})
    status, payload = _request("POST", f"/api/v1/recipes/{recipe_id}/remix", {"prompt": prompt})
    return _result(status, payload)


def get_current_draft(args: dict, **kwargs) -> str:
    status, payload = _request("GET", "/api/v1/drafts/current")
    return _result(status, payload)


def discard_draft(args: dict, **kwargs) -> str:
    status, payload = _request("DELETE", "/api/v1/drafts/current")
    return _result(status, payload)


def publish_draft(args: dict, **kwargs) -> str:
    body: dict[str, Any] = {}
    if isinstance(args.get("sourceRecipeId"), int):
        body["sourceRecipeId"] = args["sourceRecipeId"]
    if isinstance(args.get("remixPrompt"), str):
        body["remixPrompt"] = args["remixPrompt"]
    if isinstance(args.get("autoGenerateImage"), bool):
        body["autoGenerateImage"] = args["autoGenerateImage"]
    status, payload = _request("POST", "/api/v1/drafts/publish", body)
    return _result(status, payload)
