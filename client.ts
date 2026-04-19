/**
 * Minimal, zero-dependency TypeScript client for the IngredientPals agent API.
 *
 * Design: creation & remixing produce DRAFTS. Iterate via further prompts,
 * show the draft to the human, then call `publishDraft()` when they're happy.
 *
 *   const client = new IngredientPalsClient({
 *     baseUrl: "https://ingredientpals.com",
 *     apiKey: process.env.INGREDIENTPALS_API_KEY!,
 *   });
 *
 *   let { draft } = await client.createRecipeDraft({
 *     source: { type: "prompt", prompt: "20-min weeknight shakshuka for 2" },
 *   });
 *   // show draft to human, get feedback...
 *   ({ draft } = await client.createRecipeDraft({
 *     source: { type: "prompt", prompt: "less spicy, add feta on top" },
 *   }));
 *   const { recipe } = await client.publishDraft();
 */

export interface PublicRecipe {
  id: number;
  title: string;
  description: string;
  imageUrl: string | null;
  prepTime: number;
  servings: number;
  ingredients: string[];
  instructions: string[];
  mealType: string[];
  dietaryRestrictions: string[];
  userTags: string[];
  author: { username: string };
  sourceRecipeId?: number;
  remixPrompt?: string;
  createdAt: string;
  moderationStatus?: string;
}

export interface PublicDraft {
  id: number;
  title: string;
  description: string;
  imageUrl: string | null;
  prepTime: number;
  servings: number;
  ingredients: string[];
  instructions: string[];
  mealType: string[];
  dietaryRestrictions: string[];
  userTags: string[];
  versionNumber: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SearchResult {
  recipes: PublicRecipe[];
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface SearchParams {
  q?: string;
  mealTypes?: string[];
  dietary?: string[];
  tags?: string[];
  minRating?: number;
  limit?: number;
  offset?: number;
}

export type RecipeSource =
  | { type: "prompt"; prompt: string }
  | { type: "imageUrl"; imageUrl: string }
  | { type: "imageBase64"; data: string; mimeType: "image/png" | "image/jpeg" | "image/webp" }
  | { type: "url"; url: string }
  | { type: "youtube"; url: string };

export interface CreateDraftParams {
  source: RecipeSource;
}

export interface RemixDraftParams {
  id: number;
  prompt: string;
}

export interface DraftResponse {
  draft: PublicDraft;
  sourceRecipeId?: number;
  remixPrompt?: string;
}

export interface CurrentDraftResponse {
  draft: PublicDraft | null;
}

export interface PublishParams {
  sourceRecipeId?: number;
  remixPrompt?: string;
  autoGenerateImage?: boolean;
}

export interface PublishResponse {
  recipe: PublicRecipe;
  moderationStatus: string;
}

export interface ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
}

export interface ClientOptions {
  baseUrl: string;
  apiKey: string;
  fetch?: typeof fetch;
  timeoutMs?: number;
}

export class IngredientPalsClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchImpl: typeof fetch;
  private readonly timeoutMs: number;

  constructor(opts: ClientOptions) {
    if (!opts.baseUrl) throw new Error("baseUrl is required");
    if (!opts.apiKey) throw new Error("apiKey is required");
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.apiKey = opts.apiKey;
    this.fetchImpl = opts.fetch ?? (globalThis as any).fetch;
    if (!this.fetchImpl) {
      throw new Error("No fetch implementation available. Pass one via opts.fetch.");
    }
    this.timeoutMs = opts.timeoutMs ?? 120_000;
  }

  // --- Read ------------------------------------------------------------

  async searchRecipes(params: SearchParams = {}): Promise<SearchResult> {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.mealTypes?.length) qs.set("mealTypes", params.mealTypes.join(","));
    if (params.dietary?.length) qs.set("dietary", params.dietary.join(","));
    if (params.tags?.length) qs.set("tags", params.tags.join(","));
    if (typeof params.minRating === "number") qs.set("minRating", String(params.minRating));
    if (typeof params.limit === "number") qs.set("limit", String(params.limit));
    if (typeof params.offset === "number") qs.set("offset", String(params.offset));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return this.request<SearchResult>("GET", `/api/v1/recipes/search${suffix}`);
  }

  async getRecipe(id: number): Promise<PublicRecipe> {
    const { recipe } = await this.request<{ recipe: PublicRecipe }>("GET", `/api/v1/recipes/${id}`);
    return recipe;
  }

  // --- Drafts ---------------------------------------------------------

  /**
   * Create or iteratively update the active draft. Each call extends the
   * previous draft by running AI with the new source as additional context.
   */
  async createRecipeDraft(params: CreateDraftParams): Promise<DraftResponse> {
    return this.request<DraftResponse>("POST", "/api/v1/recipes", {
      body: JSON.stringify(params),
      headers: { "Content-Type": "application/json" },
    });
  }

  /** Upload a raw image (Buffer / Blob / ArrayBuffer) as a draft source. */
  async createRecipeDraftFromImageFile(
    image: Uint8Array | Blob | ArrayBuffer,
    mimeType: "image/png" | "image/jpeg" | "image/webp",
    opts: { filename?: string } = {},
  ): Promise<DraftResponse> {
    const form = new FormData();
    let blob: Blob;
    if (image instanceof Blob) blob = image;
    else if (image instanceof ArrayBuffer) blob = new Blob([image], { type: mimeType });
    else blob = new Blob([image], { type: mimeType });
    form.append("image", blob, opts.filename ?? `recipe.${mimeType.split("/")[1]}`);
    return this.request<DraftResponse>("POST", "/api/v1/recipes", { body: form });
  }

  /**
   * Create a remix draft based on a published recipe. The returned
   * `sourceRecipeId` and `remixPrompt` should be passed to `publishDraft` so
   * the server records the remix linkage.
   */
  async remixRecipeDraft(params: RemixDraftParams): Promise<DraftResponse> {
    const { id, ...body } = params;
    return this.request<DraftResponse>("POST", `/api/v1/recipes/${id}/remix`, {
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    });
  }

  async getCurrentDraft(): Promise<CurrentDraftResponse> {
    return this.request<CurrentDraftResponse>("GET", "/api/v1/drafts/current");
  }

  async discardDraft(): Promise<{ deleted: boolean }> {
    return this.request<{ deleted: boolean }>("DELETE", "/api/v1/drafts/current");
  }

  async publishDraft(params: PublishParams = {}): Promise<PublishResponse> {
    return this.request<PublishResponse>("POST", "/api/v1/drafts/publish", {
      body: JSON.stringify(params),
      headers: { "Content-Type": "application/json" },
    });
  }

  // --- Internals ------------------------------------------------------

  private async request<T>(
    method: string,
    path: string,
    init: { body?: BodyInit; headers?: Record<string, string> } = {},
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          Accept: "application/json",
          ...init.headers,
        },
        body: init.body,
        signal: controller.signal,
      });
      const text = await resp.text();
      let payload: any = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = { raw: text };
        }
      }
      if (!resp.ok) {
        const code = payload?.error?.code || "http_error";
        const message = payload?.error?.message || `HTTP ${resp.status}`;
        const err = new Error(message) as ApiError;
        err.status = resp.status;
        err.code = code;
        err.details = payload?.error?.details;
        throw err;
      }
      return payload as T;
    } finally {
      clearTimeout(timer);
    }
  }
}
