/**
 * Atlas Cloud — auto-populated provider
 *
 * Fetches the model list from https://api.atlascloud.ai/v1/models on every
 * pi startup and registers all models dynamically. When Atlas Cloud adds new
 * models, they appear automatically after a pi restart.
 *
 * The API key is resolved from auth.json (saved via /login) or $ATLAS_CLOUD_API_KEY.
 */

import type { ExtensionAPI, ProviderModelConfig } from "@earendil-works/pi-coding-agent";

const BASE_URL = "https://api.atlascloud.ai/v1";
const API = "openai-completions";

// ─── Model-family overrides ────────────────────────────────────────────────
// These are applied based on the model ID prefix. The API returns context
// window, max tokens, pricing, modalities, and reasoning support — so we only
// need to fill in pi-specific compat fields.

type FamilyOverride = Partial<ProviderModelConfig> & {
  /** thinkingFormat to set when reasoning is supported */
  thinkingFormatOnReasoning?: string;
};

const FAMILY_OVERRIDES: Record<string, FamilyOverride> = {
  "deepseek-ai/": {
    compat: { supportsDeveloperRole: false, supportsReasoningEffort: true },
    thinkingFormatOnReasoning: "deepseek",
    reasoning: true,
    thinkingLevelMap: {
      off: null,
      minimal: "low",
      low: "medium",
      medium: "high",
      high: "high",
      xhigh: "high",
    },
  },
  "qwen/": {
    compat: { supportsDeveloperRole: false },
    thinkingFormatOnReasoning: "qwen",
    thinkingLevelMap: {
      off: null,
      minimal: "low",
      low: "medium",
      medium: "high",
      high: "high",
      xhigh: "high",
    },
  },
  "moonshotai/kimi-": {
    compat: { supportsDeveloperRole: false, supportsReasoningEffort: false },
  },
  "zai-org/": {
    compat: { supportsDeveloperRole: false },
  },
  "minimaxai/": {
    compat: { supportsDeveloperRole: false },
  },
  "openai/": {
    // OpenAI defaults work fine — no overrides needed
  },
  "google/": {
    // Geminis routed through OpenAI-compatible API — defaults work fine
  },
  "anthropic/": {
    // Claude routed through OpenAI-compatible API — defaults work fine
  },
  "xai/": {
    compat: { supportsDeveloperRole: false },
  },
  "bytedance/": {},
  "kwaipilot/": {
    compat: { supportsDeveloperRole: false },
  },
};

function findFamilyOverride(modelId: string): FamilyOverride | undefined {
  for (const [prefix, override] of Object.entries(FAMILY_OVERRIDES)) {
    if (modelId.startsWith(prefix) || modelId.toLowerCase().startsWith(prefix)) {
      return override;
    }
  }
  return undefined;
}

// ─── Pricing helpers ───────────────────────────────────────────────────────

function parsePricing(value: string | undefined): number {
  if (!value) return 0;
  return parseFloat(value) * 1_000_000; // per-token → $/M tokens
}

// ─── Extension ─────────────────────────────────────────────────────────────

export default async function (pi: ExtensionAPI) {
  try {
    const response = await fetch(`${BASE_URL}/models`);
    if (!response.ok) {
      console.warn(`[atlas-cloud] Failed to fetch models: ${response.status}`);
      return;
    }

    const payload = (await response.json()) as {
      data: Array<{
        id: string;
        name?: string;
        context_length?: number;
        max_output_length?: number;
        input_modalities?: string[];
        supported_features?: string[];
        is_ready?: boolean;
        pricing?: {
          prompt?: string;
          completion?: string;
          input_cache_read?: string;
        };
      }>;
    };

    const models: ProviderModelConfig[] = [];

    for (const m of payload.data) {
      // Skip models that aren't ready yet
      // if (m.is_ready === false) continue;

      const family = findFamilyOverride(m.id);
      const hasReasoning = m.supported_features?.includes("reasoning") ?? false;
      const modalities = m.input_modalities ?? ["text"];
      const pricing = m.pricing ?? {};

      const model: ProviderModelConfig = {
        id: m.id,
        name: m.name ?? m.id,
        contextWindow: m.context_length ?? 128000,
        maxTokens: m.max_output_length ?? 65536,
        input: modalities.includes("image") ? ["text", "image"] : ["text"],
        reasoning: family?.reasoning ?? hasReasoning,
        cost: {
          input: parsePricing(pricing.prompt),
          output: parsePricing(pricing.completion),
          cacheRead: parsePricing(pricing.input_cache_read),
          cacheWrite: 0,
        },
        compat: {
          ...family?.compat,
        },
      };

      // Apply thinkingFormat when reasoning is supported
      if (hasReasoning && family?.thinkingFormatOnReasoning) {
        model.compat = {
          ...model.compat,
          thinkingFormat: family.thinkingFormatOnReasoning as any,
        };
      }

      // Apply thinkingLevelMap if defined
      if (family?.thinkingLevelMap) {
        model.thinkingLevelMap = family.thinkingLevelMap;
      }

      models.push(model);
    }

    pi.registerProvider("atlas-cloud", {
      baseUrl: BASE_URL,
      api: API,
      apiKey: "$ATLAS_CLOUD_API_KEY",
      models,
    });
  } catch (error) {
    console.warn(`[atlas-cloud] Error fetching models:`, error);
  }
}
