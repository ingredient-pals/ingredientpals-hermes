# IngredientPals agent plugin

A drop-in tool bundle that lets a tool-using LLM &mdash; Nous Hermes, OpenClaw,
OpenAI function-calling models, Claude with tool use, Llama, Mistral,
Gemini, Qwen &mdash; search, create, remix, and cook recipes on
[IngredientPals](https://ingredientpals.com).

Creation and remixing produce **drafts**. The agent iterates the draft with
the user via additional prompts, then publishes when the user is happy. See
[`skill.md`](./skill.md) for the full loop.

## Contents

| File | Purpose |
|---|---|
| [`tools.json`](./tools.json) | OpenAI-style tool/function schemas for all 7 API operations. |
| [`manifest.json`](./manifest.json) | Plugin metadata (name, description, auth scheme, base URL). |
| [`client.ts`](./client.ts) | Zero-dependency TypeScript client (Node 18+ / Bun / Deno). |
| [`skill.md`](./skill.md) | System prompt that teaches the agent the draft &rarr; publish loop and cooking mode. |

## Install

### 1. Clone this repo

```bash
git clone https://github.com/ingredient-pals/ingredientpals-hermes.git
cd ingredientpals-hermes
```

### 2. Mint an API key

Log in to [IngredientPals](https://ingredientpals.com) in your browser, click
your avatar in the bottom-left of the sidebar (or bottom-right on mobile),
choose **API Keys**, and click **New key**. Copy the `ipk_...` string &mdash;
you'll only see it once.

```bash
export INGREDIENTPALS_API_KEY=ipk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
export INGREDIENTPALS_BASE_URL=https://ingredientpals.com
```

### 3a. Register the tools with your agent

Most tool-calling LLMs accept OpenAI-style schemas directly:

```ts
import fs from "node:fs/promises";
import OpenAI from "openai";

const tools = JSON.parse(await fs.readFile("./tools.json", "utf8"));
const skill = await fs.readFile("./skill.md", "utf8");

// Works against any OpenAI-compatible endpoint that serves Hermes.
// OpenRouter example:
const client = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: process.env.OPENROUTER_API_KEY,
});

const completion = await client.chat.completions.create({
  model: "nousresearch/hermes-4-405b",
  tools,
  messages: [
    { role: "system", content: skill },
    { role: "user", content: "Create a 20-min weeknight shakshuka for two" },
  ],
});

// Dispatch each tool_call to $INGREDIENTPALS_BASE_URL/api/v1/... with
// Authorization: Bearer $INGREDIENTPALS_API_KEY — or let the typed client
// do it for you (see 3b).
```

### 3b. Or use the typed client

```ts
import { IngredientPalsClient } from "./client";

const ip = new IngredientPalsClient({
  baseUrl: process.env.INGREDIENTPALS_BASE_URL!,
  apiKey: process.env.INGREDIENTPALS_API_KEY!,
});

// 1. Create a draft
let { draft } = await ip.createRecipeDraft({
  source: { type: "prompt", prompt: "20-min weeknight shakshuka for 2" },
});

// 2. Show draft to the human; iterate on feedback
({ draft } = await ip.createRecipeDraft({
  source: { type: "prompt", prompt: "less spicy, add feta on top" },
}));

// 3. Publish
const { recipe } = await ip.publishDraft();

// --- Remix flow ---
const rm = await ip.remixRecipeDraft({ id: 42, prompt: "make it vegan" });
await ip.publishDraft({
  sourceRecipeId: rm.sourceRecipeId,
  remixPrompt: rm.remixPrompt,
});
```

### 4. Load the cooking-mode skill

`skill.md` also teaches the agent how to step a user through an existing
recipe. Load it as a system message whenever the conversation is about
cooking, creating, or remixing &mdash; it covers all three modes.

## Tool reference (summary)

| Tool | Purpose |
|---|---|
| `search_recipes` | Search published recipes |
| `get_recipe` | Fetch one published recipe |
| `create_recipe_draft` | Create or iterate the active draft |
| `remix_recipe_draft` | Create or iterate a remix draft from a source recipe |
| `get_current_draft` | Read back the active draft |
| `discard_draft` | Throw the draft away |
| `publish_draft` | Publish the draft as a real recipe |

See [`tools.json`](./tools.json) for full schemas. Full endpoint reference
lives at <https://ingredientpals.com> under the API Keys page.

## Example end-to-end conversation

```
user:      I want a one-pan weeknight dinner with chicken thighs
assistant: [create_recipe_draft({ source: { type: "prompt",
             prompt: "one-pan weeknight chicken thighs" } })]
           Here's a draft: "One-Pan Lemon-Herb Chicken Thighs", 35 min,
           4 servings.
             Ingredients: ...
             Instructions: ...
           Want to tweak anything or publish?
user:      Swap lemon for orange and add rosemary
assistant: [create_recipe_draft({ source: { type: "prompt",
             prompt: "swap lemon for orange, add fresh rosemary" } })]
           Updated draft — now orange-rosemary. Publish?
user:      Yes
assistant: [publish_draft({})]
           Published as recipe #1234 (pending moderation). Want to cook it
           tonight? I can walk you through it.
```

## Rate limits

- Reads: 100 requests / minute per key.
- Writes (draft create / remix / publish / discard): 30 requests / minute per
  key.

## Security notes

- API keys are only shown in plaintext at creation time &mdash; the server
  stores only a sha256 hash.
- Anything an agent creates or publishes with the key is attributed to the
  account that minted the key. Revoke keys any time from the API Keys page
  or via `DELETE /api/keys/:id`.
- All recipes published via the agent API are subject to the same moderation
  pipeline as the web UI; expect `moderationStatus: "pending"` on fresh
  publishes.

## License

MIT.
