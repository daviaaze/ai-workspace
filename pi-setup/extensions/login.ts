/**
 * Login Extension for Atlas Cloud and other providers
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

interface AuthConfig {
  [provider: string]: {
    type: "api_key";
    key: string;
  };
}

async function getAuthConfig(pi: ExtensionAPI): Promise<AuthConfig> {
  const authPath = join(pi.paths.agent, "auth.json");
  try {
    const content = await readFile(authPath, "utf-8");
    return JSON.parse(content);
  } catch {
    return {};
  }
}

async function saveAuthConfig(pi: ExtensionAPI, config: AuthConfig): Promise<void> {
  const authPath = join(pi.paths.agent, "auth.json");
  await writeFile(authPath, JSON.stringify(config, null, 2), "utf-8");
}

export default function (pi: ExtensionAPI) {
  pi.registerCommand("set-key", {
    description: "Store API key for a provider (e.g., /set-key atlas-cloud <api-key>)",
    handler: async (args, ctx) => {
      if (!args) {
        ctx.ui.notify(
          "Usage: /set-key <provider> <api-key>\n" +
          "Example: /set-key atlas-cloud sk-...\n\n" +
          "Supported providers for config:\n" +
          "- atlas-cloud\n" +
          "- openai\n" +
          "- anthropic\n" +
          "- google",
          "info"
        );
        return;
      }

      const [provider, apiKey] = args.trim().split(/\s+/);

      if (!provider || !apiKey) {
        ctx.ui.notify("Error: Provider and API key are required.\nUsage: /set-key <provider> <api-key>", "error");
        return;
      }

      try {
        const config = await getAuthConfig(pi);
        config[provider] = {
          type: "api_key",
          key: apiKey,
        };
        
        await saveAuthConfig(pi, config);
        ctx.ui.notify(`Successfully saved key for ${provider}!`, "info");
      } catch (error: any) {
        ctx.ui.notify(`Save failed: ${error.message}`, "error");
      }
    },
  });
}
