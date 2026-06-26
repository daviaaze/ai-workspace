/**
 * OpenCLI Bridge Extension
 *
 * Registers browser-based research tools powered by @jackwener/opencli.
 * Lets the agent navigate, extract content, screenshot, and interact with
 * real websites using your logged-in Chrome profile.
 *
 * Security: Uses execFileSync with argument arrays — no shell injection risk.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFileSync } from "node:child_process";

function opencli(args: string[], timeoutMs = 30000): { stdout: string; stderr: string } {
  try {
    const stdout = execFileSync("opencli", args, {
      encoding: "utf-8",
      timeout: timeoutMs,
      maxBuffer: 10 * 1024 * 1024,
    });
    return { stdout, stderr: "" };
  } catch (e: any) {
    return {
      stdout: e.stdout?.toString() || "",
      stderr: e.stderr?.toString() || e.message || "Unknown error",
    };
  }
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "opencli_browser",
    label: "OpenCLI Browser",
    description:
      "Interact with real websites using your logged-in Chrome browser. Use for sites requiring authentication, JavaScript-rendered content, or interactive workflows. Actions: open (navigate to URL), extract (get content), screenshot, click, type, scroll, find.",
    promptSnippet: "Open URL, extract content, or interact with websites via logged-in Chrome",
    parameters: Type.Object({
      action: Type.String({
        description:
          "Action: 'open' URL, 'extract' content (optionally with CSS selector), 'screenshot', 'click' selector, 'type' into selector, 'scroll', 'find' text, or 'wait' ms",
      }),
      url: Type.Optional(Type.String({ description: "URL for 'open' action" })),
      selector: Type.Optional(
        Type.String({ description: "CSS selector for click/type/extract" })
      ),
      text: Type.Optional(Type.String({ description: "Text for type/find actions" })),
      value: Type.Optional(Type.String({ description: "Value for scroll/wait (px or ms)" })),
    }),
    async execute(_toolCallId, params) {
      const { action, url, selector, text, value } = params;

      let args: string[];
      switch (action) {
        case "open":
          if (!url) return { content: [{ type: "text", text: "Error: url required for open" }], details: {} };
          args = ["browser", "open", url];
          break;
        case "extract":
          args = selector ? ["browser", "extract", selector] : ["browser", "extract"];
          break;
        case "screenshot":
          args = ["browser", "screenshot"];
          break;
        case "click":
          if (!selector) return { content: [{ type: "text", text: "Error: selector required for click" }], details: {} };
          args = ["browser", "click", selector];
          break;
        case "type":
          if (!selector || !text) return { content: [{ type: "text", text: "Error: selector and text required for type" }], details: {} };
          args = ["browser", "type", selector, text];
          break;
        case "scroll":
          args = value ? ["browser", "scroll", value] : ["browser", "scroll", "--down", "300"];
          break;
        case "find":
          if (!text) return { content: [{ type: "text", text: "Error: text required for find" }], details: {} };
          args = ["browser", "find", text];
          break;
        case "wait":
          args = value ? ["browser", "wait", value] : ["browser", "wait", "1000"];
          break;
        default:
          return {
            content: [{ type: "text", text: `Unknown action: ${action}. Use: open, extract, screenshot, click, type, scroll, find, wait` }],
            details: {},
          };
      }

      const { stdout, stderr } = opencli(args, 25000);
      const output = stdout || stderr || "(no output)";

      const truncated = output.length > 8000
        ? output.substring(0, 8000) + "\n... (truncated, use extract with selector for specific content)"
        : output;

      return {
        content: [{ type: "text", text: truncated }],
        details: { action, url, selector },
      };
    },
  });
}
