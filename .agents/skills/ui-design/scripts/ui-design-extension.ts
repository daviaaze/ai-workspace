/**
 * UI Design Extension
 *
 * Registers MCP-powered UI design tools for pi: component generation,
 * accessibility audits, design system lookups, and code scaffolding.
 * Connects to the aiw MCP server for knowledge base and file operations.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execSync } from "node:child_process";

// ── MCP Client (stdio-based, talks to aiw MCP server) ──

function mcpCall(tool: string, args: Record<string, unknown>): string {
  try {
    const payload = JSON.stringify({ method: "tools/call", params: { name: tool, arguments: args } });
    const result = execSync(
      `python -m ai_workspace.mcp_server`,
      {
        input: payload + "\n",
        encoding: "utf-8",
        timeout: 15000,
        cwd: process.env.AIW_WORKSPACE || process.cwd(),
      }
    );
    return result;
  } catch (e: any) {
    return `Error: ${e.stderr || e.message}`;
  }
}

// ── Tool Definitions ──

export default function (pi: ExtensionAPI) {
  // 1. UI Component Lookup
  pi.registerTool({
    name: "ui_component_lookup",
    label: "UI Component Lookup",
    description:
      "Look up UI component patterns, design system references, and implementation examples. Use when designing a new component, choosing a component library, or finding the right pattern for a UI problem.",
    promptSnippet: "Look up UI component patterns and implementation examples",
    promptGuidelines: [
      "Use ui_component_lookup to find existing component patterns before building new ones. This avoids reinventing common patterns.",
    ],
    parameters: Type.Object({
      component: Type.String({
        description: "Component type: 'card', 'table', 'form', 'modal', 'nav', 'dashboard', 'empty-state', 'loading', 'error', 'toast', 'dialog', 'sidebar', 'dropdown', or a general UI pattern",
      }),
      stack: Type.Optional(
        Type.String({
          description: "Target stack: 'react-tailwind', 'shadcn', 'streamlit', 'textual', 'html-css', or 'any' (default)",
        })
      ),
    }),
    async execute(_toolCallId, params) {
      const { component, stack } = params;
      const stackFilter = stack || "any";

      let result = `## ${component} — ${stackFilter}\n\n`;

      // Pattern lookup table
      const patterns: Record<string, Record<string, string>> = {
        card: {
          "react-tailwind": `
\`\`\`tsx
// Card component with loading, error, and empty states
interface CardProps {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyMessage?: string;
}

function Card({ title, children, loading, error, empty, emptyMessage }: CardProps) {
  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <div className="p-6">
        <h3 className="text-lg font-semibold">{title}</h3>
        {loading ? (
          <div className="mt-4 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : error ? (
          <div className="mt-4 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        ) : empty ? (
          <div className="mt-4 text-center text-sm text-muted-foreground">
            {emptyMessage || "No data available"}
          </div>
        ) : (
          <div className="mt-4">{children}</div>
        )}
      </div>
    </div>
  );
}
\`\`\`
`,
          shadcn: `Use shadcn/ui's built-in \`<Card>\`, \`<CardHeader>\`, \`<CardContent>\`, \`<CardFooter>\` components. Add \`<Skeleton>\` for loading states.`,
          streamlit: `Use \`st.container(border=True)\` or organize with \`st.columns()\`. Use \`st.metric()\` for stat cards.`,
          textual: `Use \`Vertical\` container with border styling. Rich renderables for content. Custom widget for complex cards.`,
        },
        table: {
          "react-tailwind": `Use @tanstack/react-table with shadcn/ui DataTable wrapper. Supports sorting, filtering, pagination, row selection.`,
          shadcn: `\`npx shadcn@latest add table\` — fully featured data table with sorting, filtering, pagination.`,
          streamlit: `\`st.dataframe()\` for interactive tables, \`st.data_editor()\` for editable tables with row selection.`,
          textual: `Use \`DataTable\` widget. Supports sorting, cursor navigation, custom cell renderers.`,
        },
        form: {
          "react-tailwind": `Use react-hook-form + zod validation. Form components with label, input, error message pattern.`,
          shadcn: `\`npx shadcn@latest add form input select checkbox radio textarea\`. Built-in react-hook-form + zod integration.`,
          streamlit: `\`st.form()\` for grouped inputs with submit button. \`st.text_input()\`, \`st.selectbox()\`, etc.`,
          textual: `\`Input\`, \`Select\`, \`Checkbox\`, \`RadioButton\` widgets. Use \`Screen\` with modal layer for form dialogs.`,
        },
        modal: {
          "react-tailwind": `Use shadcn/ui <Dialog> for modals, <Sheet> for slide-outs, <AlertDialog> for confirmations.`,
          shadcn: `\`npx shadcn@latest add dialog sheet alert-dialog\`. Trap focus, ESC to close, click outside to close (optional).`,
          streamlit: `\`st.dialog()\` (Streamlit 1.38+). For older: use \`st.expander()\` or session state toggle.`,
          textual: `Use \`Screen\` with modal layer. Overlay with dimmed background. Return focus on close.`,
        },
        nav: {
          "react-tailwind": `Sidebar + top nav pattern. Collapse on mobile. Use \`<Sheet>\` for mobile nav.`,
          shadcn: `Sidebar: fixed left, 16rem width. Mobile: Sheet component. Active state with accent color.`,
          streamlit: `\`st.sidebar\` for navigation, \`st.page_link()\` for multi-page apps.`,
          textual: `Left panel with navigation links. Use \`TabbedContent\` or sidebar pattern with \`Vertical\`.`,
        },
        dashboard: {
          "react-tailwind": `Grid layout: \`grid-cols-1 md:grid-cols-2 lg:grid-cols-4\`. Stat cards, charts (recharts), data table.`,
          shadcn: `Card + recharts/Chart components. Responsive grid. Filter bar + date range picker.`,
          streamlit: `\`st.columns()\` for grid, \`st.metric()\` for KPIs, \`st.plotly_chart()\` for charts. \`layout="wide"\`.`,
          textual: `Grid layout with \`Grid\` container. StatCard widgets. Live updating with \`set_interval()\`.`,
        },
        "empty-state": {
          "react-tailwind": `Centered flex column with icon, title, description, CTA button. Use for: no data, no results, no access, error recovery.`,
          shadcn: `Use \`<Card>\` with centered content. Icons from lucide-react. Action button for primary CTA.`,
          streamlit: `\`st.info()\` or custom container with centered text and button.`,
          textual: `Centered static text with Rich markup for icon. Button for action.`,
        },
        loading: {
          "react-tailwind": `Skeleton components (shape-based), spinner (indeterminate), progress bar (determinate). Use skeleton in content area, spinner for button states.`,
          shadcn: `\`npx shadcn@latest add skeleton\`. \`<Skeleton className="h-4 w-[250px]" />\` for text lines.`,
          streamlit: `\`st.spinner()\` for full-page loading, \`st.progress()\` for determinate. \`st.status\` for async ops.`,
          textual: `Loading indicator widget or rich progress bar. \`set_interval()\` for polling.`,
        },
      };

      const componentPatterns = patterns[component];
      if (componentPatterns) {
        if (componentPatterns[stackFilter]) {
          result += componentPatterns[stackFilter];
        } else {
          // Show all stacks for this component
          for (const [s, code] of Object.entries(componentPatterns)) {
            result += `### ${s}\n${code}\n\n`;
          }
        }
      } else {
        // Generic pattern lookup — search knowledge base
        result += `Pattern not in quick reference. Searching knowledge base for "${component}"...\n`;
        const kb = mcpCall("search_knowledge", { query: `UI ${component} pattern design`, limit: 3 });
        result += kb;
      }

      return {
        content: [{ type: "text", text: result }],
        details: { component, stack: stackFilter },
      };
    },
  });

  // 2. Generate UI Code
  pi.registerTool({
    name: "ui_generate_code",
    label: "Generate UI Code",
    description:
      "Generate production-ready UI component code with proper states (loading, empty, error, loaded), accessibility, and responsive design. Use when implementing a UI component after design is complete.",
    promptSnippet: "Generate UI component code with full state handling and accessibility",
    promptGuidelines: [
      "Use ui_generate_code to produce implementation code for a designed component. Always run ui_component_lookup first to check existing patterns.",
    ],
    parameters: Type.Object({
      description: Type.String({
        description: "Description of the component to generate. Include: name, purpose, props needed, states, and any special behavior.",
      }),
      stack: Type.String({
        description: "Target: 'react-shadcn', 'react-tailwind', 'streamlit', 'textual-tui', or 'html-tailwind'",
      }),
      includeTests: Type.Optional(
        Type.Boolean({ description: "Also generate test file (default: false)" })
      ),
    }),
    async execute(_toolCallId, params) {
      const { description, stack, includeTests } = params;

      // This tool guides the LLM through code generation with a structured prompt
      const prompt = `Generate a complete UI component based on the following specification.

**Component Description:** ${description}
**Target Stack:** ${stack}
**Generate Tests:** ${includeTests ? "Yes" : "No"}

Requirements:
1. Include ALL states: loading, empty, error, and loaded/display
2. Handle edge cases: long text, missing data, rapid clicks
3. Accessibility: semantic HTML, ARIA labels, focus management, keyboard nav
4. Responsive: mobile-first, test at 320px and 1440px
5. Dark mode support (if using Tailwind)
6. Use design tokens (CSS variables or Tailwind classes), never hardcode colors
7. Loading state uses skeleton, not spinner
8. Error state includes retry action
9. Empty state includes helpful guidance + CTA
10. Follow the existing codebase patterns (read existing components first)

Output format:
- File path and name
- Complete component code
- Props interface/type
- Brief usage example`;

      // Write the spec to a temp file for reference
      const specPath = `/tmp/ui-component-spec-${Date.now()}.md`;
      try {
        execSync(`cat > ${specPath} << 'SPECEOF'\n${prompt}\nSPECEOF`, { encoding: "utf-8" });
      } catch {
        // Write via Node if shell fails
        const fs = require("node:fs");
        fs.writeFileSync(specPath, prompt);
      }

      return {
        content: [
          {
            type: "text",
            text: `## UI Component Spec\n\n${prompt}\n\n---\nSpec saved to: ${specPath}\n\nFollow the UI Design workflow (see .agents/skills/ui-design/SKILL.md). Use this spec to guide implementation. Read existing components in the project first to match patterns.`,
          },
        ],
        details: { specPath, stack },
      };
    },
  });

  // 3. Accessibility Audit
  pi.registerTool({
    name: "ui_accessibility_audit",
    label: "Accessibility Audit",
    description:
      "Audit UI code for accessibility issues. Checks semantic HTML, ARIA usage, color contrast, focus management, and keyboard navigation. Use before shipping any UI component.",
    promptSnippet: "Check UI code for accessibility issues (WCAG 2.1 AA)",
    promptGuidelines: [
      "Use ui_accessibility_audit to check every new UI component before it's committed. Fix all issues it finds.",
    ],
    parameters: Type.Object({
      code: Type.Optional(
        Type.String({ description: "UI code to audit (HTML, TSX, JSX). If omitted, reads the most recently modified component files." })
      ),
      file: Type.Optional(
        Type.String({ description: "File path to audit (instead of inline code)" })
      ),
    }),
    async execute(_toolCallId, params) {
      let code = params.code || "";
      const file = params.file;

      if (file && !code) {
        try {
          code = execSync(`cat "${file}"`, { encoding: "utf-8", timeout: 5000 });
        } catch {
          return {
            content: [{ type: "text", text: `Error: could not read file: ${file}` }],
            details: {},
          };
        }
      }

      if (!code && !file) {
        return {
          content: [
            {
              type: "text",
              text: "No code or file provided. Use the 'code' or 'file' parameter to specify what to audit.",
            },
          ],
          details: {},
        };
      }

      // Static analysis of common accessibility issues
      const issues: string[] = [];

      // Check 1: Semantic HTML
      if (code.includes('<div onclick') || code.includes('<div onKeyDown')) {
        issues.push("❌ DIV used as button — use <button> element instead");
      }
      if (code.includes('<div role="button"') && !code.includes("tabindex")) {
        issues.push("❌ DIV button missing tabindex — add tabindex=\"0\"");
      }

      // Check 2: Labels
      if ((code.includes("<input") || code.includes("<select") || code.includes("<textarea")) &&
          !code.includes("<label") && !code.includes("aria-label") && !code.includes("aria-labelledby")) {
        issues.push("❌ Form input missing label — add <label> or aria-label");
      }

      // Check 3: Alt text
      if (code.includes("<img ") && !code.includes("alt=")) {
        issues.push("❌ Image missing alt attribute — add descriptive alt text or alt=\"\" for decorative");
      }

      // Check 4: Focus (worst offense)
      if (code.includes("outline-none") && !code.includes("ring") && !code.includes("focus")) {
        issues.push("❌ outline-none without replacement focus style — add focus-visible:ring-2");
      }
      if (code.includes("outline: none") && !code.includes("focus")) {
        issues.push("❌ outline:none without replacement focus style");
      }

      // Check 5: ARIA
      if (code.includes("aria-") && !code.includes('role=')) {
        // Not necessarily wrong, but worth noting
      }
      if (code.includes("aria-hidden=\"true\"") && code.includes("focusable")) {
        issues.push("⚠️ aria-hidden=\"true\" on focusable element — remove or make unfocusable");
      }

      // Check 6: Color contrast hints
      if (code.includes("text-gray-400") || code.includes("text-slate-400") || code.includes("text-muted")) {
        issues.push("⚠️ Light text color (slate-400) — verify contrast ≥ 4.5:1, consider using slate-500+ for body text");
      }

      // Check 7: red/green only
      if ((code.includes("text-red") || code.includes("text-green")) &&
          !code.includes("text-") && !code.includes("icon")) {
        issues.push("⚠️ Color-only status indicator — add icon or text label alongside color");
      }

      // Check 8: Touch targets
      if (code.includes("w-6 h-6") || code.includes("w-8 h-8") || code.includes("size-8")) {
        issues.push("⚠️ Small touch target — ensure ≥ 44×44px on mobile. Add padding to increase hit area.");
      }

      // Check 9: motion
      if (code.includes("animate-") && !code.includes("prefers-reduced-motion")) {
        issues.push("⚠️ Animation without reduced-motion check — wrap in @media (prefers-reduced-motion: no-preference)");
      }

      // Check 10: lang attribute (only for full HTML docs)
      if (code.startsWith("<!DOCTYPE") || code.startsWith("<html")) {
        if (!code.includes('lang=')) {
          issues.push("❌ Missing lang attribute on <html> — add lang=\"en\" (or appropriate language code)");
        }
      }

      if (issues.length === 0) {
        return {
          content: [{ type: "text", text: "✅ No common accessibility issues detected.\n\nManual review still recommended:\n- Tab through component with keyboard\n- Test with screen reader (VoiceOver/NVDA)\n- Verify color contrast with axe DevTools" }],
          details: { issuesFound: 0 },
        };
      }

      return {
        content: [
          {
            type: "text",
            text: `## Accessibility Audit Results\n\nFound ${issues.length} issue(s):\n\n${issues.join("\n")}\n\n---\nReference: .agents/skills/ui-design/references/accessibility.md`,
          },
        ],
        details: { issuesFound: issues.length, issues },
      };
    },
  });

  // 4. Design Token Generator
  pi.registerTool({
    name: "ui_generate_tokens",
    label: "Generate Design Tokens",
    description:
      "Generate a complete design token set (colors, spacing, typography, shadows) as CSS custom properties, Tailwind config extension, or TypeScript constants. Use when starting a new project or standardizing an existing UI.",
    promptSnippet: "Generate design tokens for a new or existing UI project",
    parameters: Type.Object({
      style: Type.Optional(
        Type.String({
          description: "Style: 'professional' (blue/slate), 'warm' (amber/stone), 'vibrant' (violet/emerald), 'minimal' (monochrome), or 'brand' (describe brand colors)",
        })
      ),
      format: Type.String({
        description: "Output format: 'css-vars', 'tailwind-config', 'typescript', or 'all'",
      }),
      brandColor: Type.Optional(
        Type.String({ description: "Primary brand color hex (e.g., '#2563eb'). Required if style is 'brand'." })
      ),
    }),
    async execute(_toolCallId, params) {
      const style = params.style || "professional";
      const format = params.format || "css-vars";
      const brandColor = params.brandColor || "#2563eb";

      // Color palettes by style
      const palettes: Record<string, { primary: string; secondary: string; accent: string; bg: string; surface: string; text: string }> = {
        professional: { primary: "#2563eb", secondary: "#475569", accent: "#8b5cf6", bg: "#f8fafc", surface: "#ffffff", text: "#0f172a" },
        warm: { primary: "#d97706", secondary: "#78716c", accent: "#f59e0b", bg: "#fafaf9", surface: "#ffffff", text: "#292524" },
        vibrant: { primary: "#7c3aed", secondary: "#059669", accent: "#db2777", bg: "#faf5ff", surface: "#ffffff", text: "#1e1b4b" },
        minimal: { primary: "#18181b", secondary: "#52525b", accent: "#18181b", bg: "#ffffff", surface: "#fafafa", text: "#09090b" },
      };

      const p = palettes[style] || palettes.professional;

      let output = `## Design Tokens — ${style} style\n\n`;

      if (format === "css-vars" || format === "all") {
        output += `### CSS Custom Properties\n\n`;
        output += `\`\`\`css\n:root {\n`;
        output += `  /* Colors */\n`;
        output += `  --color-primary: ${brandColor};\n`;
        output += `  --color-primary-hover: color-mix(in srgb, ${brandColor} 90%, black);\n`;
        output += `  --color-secondary: ${p.secondary};\n`;
        output += `  --color-accent: ${p.accent};\n`;
        output += `  --color-background: ${p.bg};\n`;
        output += `  --color-surface: ${p.surface};\n`;
        output += `  --color-text: ${p.text};\n`;
        output += `  --color-text-muted: #64748b;\n`;
        output += `  --color-border: #e2e8f0;\n`;
        output += `  --color-success: #16a34a;\n`;
        output += `  --color-warning: #f59e0b;\n`;
        output += `  --color-error: #dc2626;\n`;
        output += `\n  /* Spacing */\n`;
        output += `  --space-xs: 4px;\n  --space-sm: 8px;\n  --space-md: 16px;\n  --space-lg: 24px;\n  --space-xl: 32px;\n  --space-2xl: 48px;\n`;
        output += `\n  /* Radius */\n`;
        output += `  --radius-sm: 4px;\n  --radius-md: 6px;\n  --radius-lg: 8px;\n  --radius-xl: 12px;\n`;
        output += `\n  /* Typography */\n`;
        output += `  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;\n`;
        output += `  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;\n`;
        output += `  --text-xs: 0.75rem;\n  --text-sm: 0.875rem;\n  --text-base: 1rem;\n  --text-lg: 1.125rem;\n  --text-xl: 1.25rem;\n  --text-2xl: 1.5rem;\n  --text-3xl: 1.875rem;\n`;
        output += `\n  /* Shadows */\n`;
        output += `  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);\n  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);\n  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);\n`;
        output += `\n  /* Transitions */\n`;
        output += `  --transition-fast: 100ms ease-in-out;\n  --transition-normal: 150ms ease-in-out;\n  --transition-slow: 300ms ease-in-out;\n`;
        output += `}\n\`\`\`\n\n`;
      }

      if (format === "tailwind-config" || format === "all") {
        output += `### Tailwind Config Extension\n\n`;
        output += `\`\`\`js\n// tailwind.config.js\nmodule.exports = {\n  theme: {\n    extend: {\n      colors: {\n        brand: {\n          DEFAULT: '${brandColor}',\n          hover: 'color-mix(in srgb, ${brandColor} 90%, black)',\n          light: 'color-mix(in srgb, ${brandColor} 10%, white)',\n        },\n      },\n      borderRadius: {\n        'xs': '2px',\n      },\n    },\n  },\n};\n\`\`\`\n\n`;
      }

      if (format === "typescript" || format === "all") {
        output += `### TypeScript Constants\n\n`;
        output += `\`\`\`typescript\nexport const tokens = {\n  colors: {\n    primary: '${brandColor}',\n    secondary: '${p.secondary}',\n    accent: '${p.accent}',\n    background: '${p.bg}',\n    surface: '${p.surface}',\n    text: '${p.text}',\n    muted: '#64748b',\n    border: '#e2e8f0',\n    success: '#16a34a',\n    warning: '#f59e0b',\n    error: '#dc2626',\n  },\n  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 },\n  radius: { sm: 4, md: 6, lg: 8, xl: 12 },\n} as const;\n\`\`\`\n`;
      }

      return {
        content: [{ type: "text", text: output }],
        details: { style, format, brandColor },
      };
    },
  });

  // 5. Project Setup: Install a design system
  pi.registerTool({
    name: "ui_setup_design_system",
    label: "Setup Design System",
    description:
      "Initialize a design system in the project. Sets up shadcn/ui, Tailwind, or CSS custom properties with design tokens. Use when starting a new project or adding a design system to an existing one.",
    promptSnippet: "Initialize a design system (shadcn/ui, Tailwind, or CSS tokens)",
    promptGuidelines: [
      "Use ui_setup_design_system when starting a new frontend project or when asked to add a component library. This handles the boilerplate setup.",
    ],
    parameters: Type.Object({
      system: Type.String({
        description: "Design system: 'shadcn' (React), 'tailwind-only', 'css-tokens', or 'streamlit-css'",
      }),
      projectType: Type.Optional(
        Type.String({
          description: "Project type: 'nextjs', 'vite-react', 'remix', 'streamlit', or 'existing' (default: auto-detect)",
        })
      ),
    }),
    async execute(_toolCallId, params) {
      const { system } = params;
      const result: string[] = [];

      switch (system) {
        case "shadcn":
          result.push("## Setting up shadcn/ui\n");
          result.push("```bash");
          result.push("# 1. Initialize shadcn/ui (run in project root)");
          result.push("npx shadcn@latest init");
          result.push("");
          result.push("# 2. Choose during setup:");
          result.push("#    - Style: Default");
          result.push("#    - Base color: Slate");
          result.push("#    - CSS variables: Yes (recommended)");
          result.push("");
          result.push("# 3. Add common components");
          result.push("npx shadcn@latest add button card dialog dropdown-menu form input label");
          result.push("npx shadcn@latest add select separator sheet skeleton table tabs");
          result.push("npx shadcn@latest add toast toggle tooltip");
          result.push("```\n");
          result.push("See: https://ui.shadcn.com/docs/installation");
          break;

        case "tailwind-only":
          result.push("## Setting up Tailwind CSS\n");
          result.push("```bash");
          result.push("# For Vite + React:");
          result.push("npm install -D tailwindcss @tailwindcss/vite");
          result.push("");
          result.push("# For Next.js:");
          result.push("npm install -D tailwindcss @tailwindcss/postcss");
          result.push("```\n");
          result.push("Configure your `tailwind.config.*` with design tokens from the `ui_generate_tokens` tool.");
          break;

        case "css-tokens":
          result.push("## Setting up CSS Design Tokens\n");
          result.push("1. Create `src/styles/tokens.css` with CSS custom properties");
          result.push("2. Import in your root layout/component");
          result.push("3. Use `var(--color-primary)` throughout your CSS");
          result.push("\nSee: .agents/skills/ui-design/references/design-tokens.md");
          break;

        case "streamlit-css":
          result.push("## Setting up Streamlit Custom Theme\n");
          result.push("Create `.streamlit/config.toml`:\n");
          result.push("```toml\n[theme]\nprimaryColor = '#2563eb'\nbackgroundColor = '#f8fafc'\nsecondaryBackgroundColor = '#ffffff'\ntextColor = '#0f172a'\nfont = 'sans serif'\n```\n");
          result.push("For custom CSS: use `st.markdown()` with `<style>` tags.");
          break;

        default:
          result.push(`Unknown design system: ${system}. Use: shadcn, tailwind-only, css-tokens, or streamlit-css.`);
      }

      return {
        content: [{ type: "text", text: result.join("\n") }],
        details: { system },
      };
    },
  });
}
