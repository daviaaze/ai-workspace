/**
 * LongCat — custom provider
 *
 * OpenAI-compatible API for LongCat models.
 * Uses DeepSeek-style thinking format (`thinking: { type: "enabled" }`).
 *
 * Values (context window, pricing) sourced from the authoritative API
 * platform as of the model response:
 *   prompt: 2, completion: 8, cached_tokens: 0.04, context_length: 1,048,576
 *
 * API docs: https://longcat.chat/platform/docs/api/chat
 * Pricing:   https://longcat.chat/platform/docs/pricing/long-cat-2.0
 *
 * Set your API key in the LONGCAT_API_KEY environment variable,
 * or use /login longcat to save it to auth.json.
 */

import type { ExtensionAPI, ProviderModelConfig } from "@earendil-works/pi-coding-agent";

const BASE_URL = "https://api.longcat.chat/openai/v1";
const API = "openai-completions";

const MODELS: ProviderModelConfig[] = [
  {
    id: "LongCat-2.0",
    name: "LongCat 2.0",
    reasoning: true,
    input: ["text"],
    cost: {
      input: 2,
      output: 8,
      cacheRead: 0.04,
      cacheWrite: 0,
    },
    contextWindow: 1_048_576,  // 1M tokens (from API)
    maxTokens: 131_072,         // 128K (from docs)
    compat: {
      thinkingFormat: "deepseek",
      supportsDeveloperRole: false,
    },
    thinkingLevelMap: {
      off: null,
      minimal: null,
      low: null,
      medium: "enabled",
      high: "enabled",
      xhigh: "enabled",
      max: "enabled",
    },
  },
];

export default function (pi: ExtensionAPI) {
  pi.registerProvider("longcat", {
    name: "LongCat",
    baseUrl: BASE_URL,
    api: API,
    apiKey: "$LONGCAT_API_KEY",
    models: MODELS,
  });
}
