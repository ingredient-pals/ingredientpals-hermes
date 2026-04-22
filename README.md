# IngredientPals Hermes plugin

A [Hermes Agent](https://hermes-agent.nousresearch.com) plugin that lets the
agent search, create, remix, and cook recipes on
[IngredientPals](https://ingredientpals.com).

Creation and remixing produce **drafts**. The agent iterates the draft with
the user via additional prompts, then publishes when the user is happy. See
[`skills/recipes/SKILL.md`](./skills/recipes/SKILL.md) for the
full loop.

## Contents

| File | Purpose |
|---|---|
| [`plugin.yaml`](./plugin.yaml) | Hermes plugin manifest — name, version, declared tools, required env vars. |
| [`__init__.py`](./__init__.py) | `register(ctx)` — wires schemas to handlers and registers the bundled skill. |
| [`schemas.py`](./schemas.py) | Tool schemas (what the LLM sees). |
| [`tools.py`](./tools.py) | Tool handlers — zero-dep Python client for the IngredientPals API. |
| [`skills/recipes/SKILL.md`](./skills/recipes/SKILL.md) | Bundled skill that teaches the agent the draft → publish loop and cooking mode. Loadable as `skill_view("ingredientpals:recipes")`. |

## Install

### 1. Add the plugin to Hermes

```bash
hermes plugins install ingredient-pals/ingredientpals-hermes
```

Hermes will prompt you for `INGREDIENTPALS_API_KEY` during install and save
it to `~/.hermes/.env`. You can mint a key in your browser:

1. Log in to [IngredientPals](https://ingredientpals.com).
2. Click your avatar (bottom-left of the sidebar, or bottom-right on mobile)
   and choose **API Keys**.
3. Click **New key**, copy the `ipk_...` string. You'll only see it once.

To install and enable in one step:

```bash
hermes plugins install ingredient-pals/ingredientpals-hermes --enable
```

Otherwise, enable it afterwards with:

```bash
hermes plugins enable ingredientpals
```

### 2. (Optional) point at a different backend

The default base URL is `https://ingredientpals.com`. Override with:

```bash
export INGREDIENTPALS_BASE_URL=https://staging.ingredientpals.com
```

### 3. Use it

Start Hermes and try:

```
Find me a weeknight shakshuka for two
Create a recipe for one-pan lemon-herb chicken thighs
Remix recipe 42 to be vegan
What's on recipe 1234? I want to cook it tonight.
```

The agent has access to seven tools (all prefixed `ingredientpals_`) and can
load the bundled skill on demand via `skill_view("ingredientpals:recipes")`
for the full draft-iterate-publish loop and cooking-mode playbook.

## Tool reference

| Tool | Purpose |
|---|---|
| `ingredientpals_search_recipes` | Search published recipes |
| `ingredientpals_get_recipe` | Fetch one published recipe |
| `ingredientpals_create_recipe_draft` | Create or iterate the active draft |
| `ingredientpals_remix_recipe_draft` | Create or iterate a remix draft from a source recipe |
| `ingredientpals_get_current_draft` | Read back the active draft |
| `ingredientpals_discard_draft` | Throw the draft away |
| `ingredientpals_publish_draft` | Publish the draft as a real recipe |

Full schemas live in [`schemas.py`](./schemas.py). Full endpoint reference
lives at <https://ingredientpals.com> under the API Keys page.

## Example end-to-end conversation

```
user:      I want a one-pan weeknight dinner with chicken thighs
assistant: [ingredientpals_create_recipe_draft({ source: { type: "prompt",
             prompt: "one-pan weeknight chicken thighs" } })]
           Here's a draft: "One-Pan Lemon-Herb Chicken Thighs", 35 min,
           4 servings.
             Ingredients: ...
             Instructions: ...
           Want to tweak anything or publish?
user:      Swap lemon for orange and add rosemary
assistant: [ingredientpals_create_recipe_draft({ source: { type: "prompt",
             prompt: "swap lemon for orange, add fresh rosemary" } })]
           Updated draft — now orange-rosemary. Publish?
user:      Yes
assistant: [ingredientpals_publish_draft({})]
           Published as recipe #1234 (pending moderation). Want to cook it
           tonight? I can walk you through it.
```

## Rate limits

- Reads: 100 requests / minute per key.
- Writes (draft create / remix / publish / discard): 30 requests / minute per
  key.

## Security notes

- API keys are only shown in plaintext at creation time — the server stores
  only a sha256 hash.
- Anything the agent creates or publishes with the key is attributed to the
  account that minted the key. Revoke keys any time from the API Keys page
  or via `DELETE /api/keys/:id`.
- All recipes published via the agent API are subject to the same moderation
  pipeline as the web UI; expect `moderationStatus: "pending"` on fresh
  publishes.

## License

MIT.
