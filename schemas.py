"""Tool schemas for the IngredientPals Hermes plugin.

These are what the LLM sees when deciding which tool to call. The names are
namespaced with an `ingredientpals_` prefix to avoid collisions with other
plugins / built-in tools. Descriptions are written so a tool-using model can
tell when to reach for each one without reading skill.md first.
"""

SEARCH_RECIPES = {
    "name": "ingredientpals_search_recipes",
    "description": (
        "Search IngredientPals for PUBLISHED recipes. Supports free-text "
        "queries and structured filters. Use this to look up existing "
        "recipes before creating a new one, or when the user names a dish "
        "they want to cook."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "q": {
                "type": "string",
                "description": (
                    "Free-text query matched against title, description, "
                    "ingredients, instructions, and tags. Omit or leave "
                    "empty to browse."
                ),
            },
            "mealTypes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by meal type (breakfast, dinner, dessert, ...).",
            },
            "dietary": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dietary restrictions (vegan, gluten-free, keto, ...).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "User tags (italian, weeknight, quick, ...).",
            },
            "minRating": {"type": "integer", "minimum": 0, "maximum": 5},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            "offset": {"type": "integer", "minimum": 0, "default": 0},
        },
    },
}

GET_RECIPE = {
    "name": "ingredientpals_get_recipe",
    "description": (
        "Fetch the full details of a single PUBLISHED recipe by numeric id. "
        "Call this before entering cooking mode so you have every "
        "ingredient and instruction."
    ),
    "parameters": {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "integer", "description": "Published recipe id."}
        },
    },
}

CREATE_RECIPE_DRAFT = {
    "name": "ingredientpals_create_recipe_draft",
    "description": (
        "Create or iteratively update the user's active DRAFT recipe from "
        "exactly ONE source: a text prompt, a remote image URL, an inline "
        "base64 image, a web URL, or a YouTube URL. The result is a DRAFT, "
        "NOT a published recipe. Call this multiple times to iterate: each "
        "call merges the new input with the existing draft via AI. Present "
        "the draft to the human, let them request more prompts, then call "
        "ingredientpals_publish_draft when they are happy."
    ),
    "parameters": {
        "type": "object",
        "required": ["source"],
        "properties": {
            "source": {
                "description": (
                    "Exactly one source. Set `type` to one of: 'prompt', "
                    "'imageUrl', 'imageBase64', 'url', 'youtube'. Include "
                    "the matching fields: `prompt` for prompt; `imageUrl` "
                    "for imageUrl; `data` + `mimeType` for imageBase64; "
                    "`url` for url and youtube."
                ),
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["prompt", "imageUrl", "imageBase64", "url", "youtube"],
                    },
                    "prompt": {
                        "type": "string",
                        "minLength": 3,
                        "maxLength": 4000,
                        "description": (
                            "Free-text instruction. On first call: the "
                            "initial recipe idea. On later calls: a tweak "
                            "('less spicy', 'swap beef for mushroom')."
                        ),
                    },
                    "imageUrl": {
                        "type": "string",
                        "description": "http(s) URL of a PNG/JPEG/WebP image showing a recipe.",
                    },
                    "data": {
                        "type": "string",
                        "description": "Base64-encoded image bytes (data: prefix tolerated). Max 8 MB decoded.",
                    },
                    "mimeType": {
                        "type": "string",
                        "enum": ["image/png", "image/jpeg", "image/webp"],
                    },
                    "url": {
                        "type": "string",
                        "description": "http(s) URL. Use with type='url' for a recipe web page or type='youtube' for a cooking video.",
                    },
                },
                "required": ["type"],
            }
        },
    },
}

REMIX_RECIPE_DRAFT = {
    "name": "ingredientpals_remix_recipe_draft",
    "description": (
        "Create an iterative DRAFT that remixes an existing published "
        "recipe. On first call, the base is the published source recipe; "
        "on later calls, the base is the latest draft. The response "
        "returns sourceRecipeId and remixPrompt — remember these and pass "
        "them to ingredientpals_publish_draft so the published recipe is "
        "linked to its source."
    ),
    "parameters": {
        "type": "object",
        "required": ["id", "prompt"],
        "properties": {
            "id": {
                "type": "integer",
                "description": "Source (published) recipe id to remix.",
            },
            "prompt": {
                "type": "string",
                "minLength": 3,
                "maxLength": 2000,
                "description": "Plain-language remix instruction ('make it vegan', 'halve the sugar, add ginger').",
            },
        },
    },
}

GET_CURRENT_DRAFT = {
    "name": "ingredientpals_get_current_draft",
    "description": (
        "Fetch the current active draft for this user. Returns "
        "{ draft: null } if there is none. Use this to re-read the draft "
        "when presenting it to the human or to check what was last generated."
    ),
    "parameters": {"type": "object", "properties": {}},
}

DISCARD_DRAFT = {
    "name": "ingredientpals_discard_draft",
    "description": (
        "Delete the current active draft without publishing. Use when the "
        "user wants to start over or abandon the work."
    ),
    "parameters": {"type": "object", "properties": {}},
}

PUBLISH_DRAFT = {
    "name": "ingredientpals_publish_draft",
    "description": (
        "Publish the current active draft as a real recipe owned by the "
        "user. The published recipe is queued for moderation. If the draft "
        "was produced by ingredientpals_remix_recipe_draft, pass "
        "sourceRecipeId and remixPrompt (returned by the last remix call) "
        "so the server records the remix linkage."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sourceRecipeId": {
                "type": "integer",
                "description": "Optional. Set only when publishing a remix.",
            },
            "remixPrompt": {
                "type": "string",
                "description": "Optional. The remix instruction text. Pair with sourceRecipeId.",
            },
            "autoGenerateImage": {
                "type": "boolean",
                "default": True,
                "description": "Whether to auto-generate an image if the draft has none.",
            },
        },
    },
}
