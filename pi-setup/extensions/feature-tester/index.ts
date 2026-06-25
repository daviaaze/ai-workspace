/**
 * Feature Tester Extension — v3
 *
 * Registers three Playwright-powered tools callable directly by pi-agent:
 *   take_screenshot        — Navigate to a staging URL and capture a screenshot
 *   record_walkthrough     — Record a video of a multi-step browser interaction
 *   run_e2e_test           — Run a Playwright test file against staging
 *
 * Screenshots and videos save to ~/Projects/Lux/ai-workspace/Media-Inbox/
 *
 * Architecture: Each tool generates an inline .mjs script written into the
 * project's .pi-temp/ directory, then runs it with node. This ensures
 * @playwright/test resolves from the project's node_modules.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { resolve, join } from "node:path";
import { existsSync, mkdirSync, writeFileSync, unlinkSync, readFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const WORKSPACE_MEDIA =
  process.env.FEATURE_TESTER_OUTPUT_DIR ||
  resolve(process.env.HOME || "/home", "Projects/Lux/ai-workspace/Media-Inbox");

const STAGING: Record<string, string> = {
  admin: "https://test-admin.luxuryescapes.com",
  extranet: "https://test-extranet.luxuryescapes.com",
  vendor: "https://vendor.luxuryescapes.com",
};

// ---------------------------------------------------------------------------
// NixOS Playwright browser resolution
// ---------------------------------------------------------------------------

let cachedBrowsersPath: string | null = null;
let nixResolved = false;

/** Try to resolve playwright-driver.browsers from nixpkgs. Cached after first call. */
async function resolvePlaywrightBrowsersPath(): Promise<string | null> {
  if (nixResolved) return cachedBrowsersPath;
  nixResolved = true;

  // 1. Check if already set in environment
  if (process.env.PLAYWRIGHT_BROWSERS_PATH) {
    cachedBrowsersPath = process.env.PLAYWRIGHT_BROWSERS_PATH;
    return cachedBrowsersPath;
  }

  // 2. Try nix eval to get the store path
  try {
    const { stdout } = await execFileAsync("nix", [
      "eval", "nixpkgs#playwright-driver.browsers", "--raw",
    ], { timeout: 30_000, windowsHide: true });
    const path = stdout.trim();
    if (path && existsSync(path)) {
      cachedBrowsersPath = path;
      return cachedBrowsersPath;
    }
  } catch {
    // nix eval failed — probably not on NixOS, or nix not in PATH
  }

  return null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ensureDir(dir: string): string {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

function resolveUrl(raw: string): string {
  for (const [key, base] of Object.entries(STAGING)) {
    if (raw === key || raw.startsWith(key + "/")) {
      return base + (raw.startsWith(key + "/") ? raw.slice(key.length) : "");
    }
  }
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  return STAGING.admin + (raw.startsWith("/") ? raw : "/" + raw);
}

function writeTempScript(projectDir: string, code: string): string {
  ensureDir(join(projectDir, ".pi-temp"));
  const path = join(projectDir, ".pi-temp", `pw-${randomUUID()}.mjs`);
  writeFileSync(path, code, "utf-8");
  return path;
}

function cleanup(path: string): void {
  try { unlinkSync(path); } catch {}
}

// ===========================================================================
// Script generators (inline .mjs files that import @playwright/test)
// ===========================================================================

/** Read admin credentials from the project's playwright fixtures, if present. */
function readAuthConfig(projectDir: string): { login: string; password: string; authHost: string } | null {
  const fixturesPath = join(projectDir, "playwright", "fixtures", "adminUsers.json");
  if (!existsSync(fixturesPath)) return null;
  try {
    const raw = JSON.parse(readFileSync(fixturesPath, "utf-8"));
    const admin = raw?.admin || raw?.default_admin;
    if (!admin?.login || !admin?.password) return null;
    return {
      login: admin.login,
      password: admin.password,
      authHost: (process.env.REACT_APP_AUTH_HOST ||
                 process.env.AUTH_HOST ||
                 process.env.API_HOST ||
                 "https://cdn.test.luxuryescapes.com").replace(/\/$/, ""),
    };
  } catch {
    return null;
  }
}

function authBlock(auth: { login: string; password: string; authHost: string }): string {
  return `
// Authenticate before navigating
const loginRes = await ctx.request.post(${JSON.stringify(auth.authHost)} + "/login", {
  data: { login: ${JSON.stringify(auth.login)}, password: ${JSON.stringify(auth.password)} },
  headers: { Accept: "application/json", "Content-Type": "application/json" },
});
if (!loginRes.ok()) throw new Error("Login failed: " + loginRes.status());
const body = await loginRes.json();
const token = body.access_token || body.result?.access_token;
if (!token) throw new Error("No access_token in login response");
await page.addInitScript((t) => { try { window.localStorage.setItem("token", t); } catch {} }, token);
`;
}

function screenshotCode(
  url: string, outputPath: string,
  selector?: string, viewport?: string, waitMs?: number,
  auth?: { login: string; password: string; authHost: string } | null,
): string {
  const [w, h] = (viewport || "1280x720").split("x").map(Number);
  const ms = waitMs ?? 2000;
  const sel = selector
    ? `const el = await page.locator(${JSON.stringify(selector)}).first();\nawait el.screenshot({ path: ${JSON.stringify(outputPath)} });`
    : `await page.screenshot({ path: ${JSON.stringify(outputPath)}, fullPage: true });`;

  return `import { chromium } from "@playwright/test";
import { statSync } from "node:fs";
const browser = await chromium.launch({ headless: true });
try {
  const ctx = await browser.newContext({ viewport: { width: ${w}, height: ${h} } });
  const page = await ctx.newPage();
${auth ? authBlock(auth) : ""}
  await page.goto(${JSON.stringify(url)}, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(${ms});
  ${sel}
  const size = statSync(${JSON.stringify(outputPath)}).size;
  console.log(JSON.stringify({ ok:true, path:${JSON.stringify(outputPath)}, size }));
} catch (e) {
  console.log(JSON.stringify({ ok:false, error:e.message }));
  process.exit(1);
} finally { await browser.close(); }
`;
}

function walkthroughCode(stepsJson: string, outputPath: string, baseUrl?: string, auth?: { login: string; password: string; authHost: string } | null): string {
  return `import { chromium } from "@playwright/test";
import { renameSync, readdirSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
const steps = ${stepsJson};
const out = ${JSON.stringify(outputPath)};
const base = ${JSON.stringify(baseUrl || "")};
const dir = dirname(out);
mkdirSync(dir, { recursive: true });
const browser = await chromium.launch({ headless: true });
let failed = false;

// ---- visible cursor overlay ----
const CURSOR_SVG = \`<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <defs><filter id="cs"><feDropShadow dx="1" dy="1" stdDeviation="0.5" flood-opacity="0.4"/></filter></defs>
  <path filter="url(#cs)" fill="#fff" stroke="#1a1a1a" stroke-width="1.2"
    d="M3 3l6 16h5l3 7 6-19H3z"/>
</svg>\`;
let cursorX = -100, cursorY = -100;  // track last position across moves
async function injectCursor(page) {
  await page.addStyleTag({ content: \`
    #pi-cursor { position:fixed; z-index:2147483647; pointer-events:none;
      left:-100px; top:-100px; width:32px; height:32px; }
  \` });
  await page.evaluate((svg) => {
    const el = document.createElement("div");
    el.id = "pi-cursor";
    el.innerHTML = svg;
    document.body.appendChild(el);
  }, CURSOR_SVG);
  // reset tracked position when re-injecting
  cursorX = -100; cursorY = -100;
}
async function moveCursor(page, x, y) {
  cursorX = x; cursorY = y;
  await page.evaluate(({x,y}) => {
    const el = document.getElementById("pi-cursor");
    if (el) { el.style.left = x + "px"; el.style.top = y + "px"; }
  }, { x, y });
}
// ---- smooth mouse movement (bezier curve) ----
function lerp(a, b, t) { return a + (b - a) * t; }
function bezier(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return { x: u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x,
           y: u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y };
}
function dist(a, b) { return Math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2); }
async function smoothMove(page, toX, toY, durationMs = 400) {
  // Continue from last known position, or pick one near the target
  let fromX = cursorX, fromY = cursorY;
  if (fromX < -50 || fromY < -50) {
    fromX = toX - 80 + Math.random() * 160;
    fromY = toY - 60 + Math.random() * 120;
  }
  const d = dist({x:fromX,y:fromY}, {x:toX,y:toY});
  // Subtle control point offsets — scaled by distance for consistency
  const wobbleX = Math.min(d * 0.15, 120) * (Math.random() > 0.5 ? 1 : -1);
  const wobbleY = Math.min(d * 0.10, 80) * (Math.random() > 0.5 ? 1 : -1);
  const cp1 = { x: lerp(fromX, toX, 0.35) + wobbleX, y: lerp(fromY, toY, 0.2) + wobbleY };
  const cp2 = { x: lerp(fromX, toX, 0.65) - wobbleX * 0.5, y: lerp(fromY, toY, 0.8) - wobbleY * 0.5 };
  // Adapt step count to distance; slower near the end (ease-out)
  const steps = Math.max(8, Math.floor(d / 8));
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Ease-out: accelerate at start, decelerate near target
    const eased = t < 0.5 ? 2*t*t : -1+(4-2*t)*t;
    const pt = bezier({x:fromX,y:fromY}, cp1, cp2, {x:toX,y:toY}, eased);
    await page.mouse.move(pt.x, pt.y);
    await moveCursor(page, pt.x, pt.y);
    if (i < steps) await page.waitForTimeout(durationMs / steps);
  }
}
async function moveToElement(page, sel) {
  const el = page.locator(sel).first();
  await el.waitFor({ state: "visible", timeout: 10000 });
  const box = await el.boundingBox();
  if (box) await smoothMove(page, box.x + box.width/2, box.y + box.height/2);
}
// -------------------------------------------------

try {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir, size: { width: 1280, height: 720 } },
  });
  const page = await ctx.newPage();
${auth ? authBlock(auth) : ""}
  // Inject visible cursor before any movement
  await injectCursor(page);
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    const u = s.url?.startsWith("http") ? s.url : base + (s.url || "");
    try {
      console.error("[pw] Step " + (i+1) + "/" + steps.length + ": " + s.action);
      switch (s.action) {
        case "navigate":
          await page.goto(u, { waitUntil: "domcontentloaded", timeout: 30000 });
          // Give the SPA time to render
          await page.waitForTimeout(2000);
          // Re-inject cursor after page navigation
          await injectCursor(page);
          break;
        case "click":
          await moveToElement(page, s.selector);
          await page.waitForTimeout(200);
          await page.locator(s.selector).first().click();
          break;
        case "type":
          await moveToElement(page, s.selector);
          await page.waitForTimeout(200);
          await page.locator(s.selector).first().click();
          await page.locator(s.selector).first().fill(s.value || "");
          break;
        case "wait":
          if (s.selector) {
            await page.waitForSelector(s.selector, { timeout: s.timeout || 15000 });
          } else {
            await page.waitForTimeout(s.ms || 1500);
          }
          break;
        case "hover":
          await moveToElement(page, s.selector);
          break;
        case "select":
          await moveToElement(page, s.selector);
          await page.waitForTimeout(200);
          await page.locator(s.selector).first().selectOption(s.value || "");
          break;
        case "move_mouse":
          if (s.x !== undefined && s.y !== undefined) {
            await smoothMove(page, s.x, s.y, s.duration || 500);
          } else if (s.selector) {
            await moveToElement(page, s.selector);
          }
          break;
        case "screenshot":
          await page.screenshot({ path: s.path || join(dir, "step-" + (i+1) + ".png"), fullPage: s.fullPage !== false });
          break;
      }
      await page.waitForTimeout(s.waitAfter ?? 800);
    } catch (e) {
      console.error("[pw] Step " + (i+1) + " failed: " + e.message);
      failed = true;
      try { await page.screenshot({ path: join(dir, "step-" + (i+1) + "-error.png") }); } catch {}
      break;
    }
  }
  await page.waitForTimeout(1500);
  await ctx.close();
  const files = readdirSync(dir);
  const webm = files.find(f => f.endsWith(".webm"));
  if (webm) {
    const src = join(dir, webm);
    const dest = out.endsWith(".webm") ? out : out + ".webm";
    if (src !== dest) renameSync(src, dest);
    const sz = statSync(dest).size;
    console.log(JSON.stringify({ ok:true, path:dest, size:sz, steps:steps.length, failed }));
  } else {
    console.log(JSON.stringify({ ok:false, error:"Video file not found in " + dir }));
    process.exit(1);
  }
} catch (e) {
  console.log(JSON.stringify({ ok:false, error:e.message }));
  process.exit(1);
} finally { try { await browser.close(); } catch {} }
`;
}

function walkthroughHeadedCode(
  stepsJson: string, outputPath: string,
  baseUrl?: string,
  auth?: { login: string; password: string; authHost: string } | null,
  windowX = 0, windowY = 0
): string {
  return `import { chromium } from "@playwright/test";
import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
const steps = ${stepsJson};
const out = ${JSON.stringify(outputPath)};
const base = ${JSON.stringify(baseUrl || "")};
const dir = dirname(out);
if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

function lerp(a,b,t){return a+(b-a)*t}
function bezier(p0,p1,p2,p3,t){const u=1-t;return{x:u*u*u*p0.x+3*u*u*t*p1.x+3*u*t*t*p2.x+t*t*t*p3.x,y:u*u*u*p0.y+3*u*u*t*p1.y+3*u*t*t*p2.y+t*t*t*p3.y}}
function dist(a,b){return Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2)}
let lx=-1,ly=-1;
async function smoothMove(page,toX,toY,dur=350){
  const fx=lx>0?lx:toX-60+Math.random()*120, fy=ly>0?ly:toY-40+Math.random()*80;
  const d=dist({x:fx,y:fy},{x:toX,y:toY});
  const w=Math.min(d*0.08,80)*(Math.random()>.5?1:-1);
  const c1={x:lerp(fx,toX,.3)+w,y:lerp(fy,toY,.15)+w*.6};
  const c2={x:lerp(fx,toX,.7)-w*.4,y:lerp(fy,toY,.85)-w*.3};
  const n=Math.max(12,Math.floor(d/10));
  for(let i=0;i<=n;i++){
    const t=i/n,e=t<.5?2*t*t:-1+(4-2*t)*t;
    const pt=bezier({x:fx,y:fy},c1,c2,{x:toX,y:toY},e);
    await page.mouse.move(pt.x,pt.y);
    lx=pt.x;ly=pt.y;
    if(i<n)await page.waitForTimeout(dur/n);
  }
}

console.error("[pw-headed] Launching on display...");
const browser = await chromium.launch({
  headless: false,
  args: [
    "--no-sandbox", "--disable-gpu",
    "--ozone-platform=wayland",
    "--window-position=" + ${windowX} + "," + ${windowY},
    "--window-size=1920,1080",
  ],
});
let failed = false;
try {
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    // no recordVideo — screen recording handles it
  });
  const page = await ctx.newPage();
${auth ? authBlock(auth) : ""}
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    const u = s.url?.startsWith("http") ? s.url : base + (s.url || "");
    try {
      console.error("[pw-headed] Step " + (i+1) + "/" + steps.length + ": " + s.action);
      switch (s.action) {
        case "navigate":
          await page.goto(u, { waitUntil: "domcontentloaded", timeout: 30000 });
          await page.waitForTimeout(2000);
          lx = -1; ly = -1;  // reset tracked cursor after nav
          break;
        case "click": {
          const el = page.locator(s.selector).first();
          await el.waitFor({ state: "visible", timeout: 10000 });
          const box = await el.boundingBox();
          if (box) {
            await smoothMove(page, box.x + box.width/2, box.y + box.height/2);
            await page.waitForTimeout(200);
          }
          await el.click();
          break;
        }
        case "type": {
          const el = page.locator(s.selector).first();
          await el.waitFor({ state: "visible", timeout: 10000 });
          const box = await el.boundingBox();
          if (box) {
            await smoothMove(page, box.x + box.width/2, box.y + box.height/2);
            await page.waitForTimeout(150);
          }
          await el.click();
          await el.fill(s.value || "");
          break;
        }
        case "wait":
          if (s.selector) await page.waitForSelector(s.selector, { timeout: s.timeout || 15000 });
          else await page.waitForTimeout(s.ms || 1500);
          break;
        case "hover": {
          const el = page.locator(s.selector).first();
          await el.waitFor({ state: "visible", timeout: 10000 });
          const box = await el.boundingBox();
          if (box) await smoothMove(page, box.x + box.width/2, box.y + box.height/2);
          break;
        }
        case "select": {
          const el = page.locator(s.selector).first();
          await el.waitFor({ state: "visible", timeout: 10000 });
          const box = await el.boundingBox();
          if (box) {
            await smoothMove(page, box.x + box.width/2, box.y + box.height/2);
            await page.waitForTimeout(150);
          }
          await el.selectOption(s.value || "");
          break;
        }
        case "move_mouse":
          await smoothMove(page, s.x || 400, s.y || 300, s.duration || 500);
          break;
        case "screenshot":
          await page.screenshot({ path: s.path || join(dir, "step-" + (i+1) + ".png"), fullPage: s.fullPage !== false });
          break;
      }
      await page.waitForTimeout(s.waitAfter ?? 800);
    } catch (e) {
      console.error("[pw-headed] Step " + (i+1) + " failed: " + e.message);
      failed = true;
      try { await page.screenshot({ path: join(dir, "step-" + (i+1) + "-error.png") }); } catch {}
      break;
    }
  }
  await page.waitForTimeout(1500);
  console.log(JSON.stringify({ ok: true, path: out, steps: steps.length, failed }));
} catch (e) {
  console.error(e);
  console.log(JSON.stringify({ ok: false, error: e.message }));
  process.exit(1);
} finally { try { await browser.close(); } catch {} }
`;
}

// ===========================================================================
// Extension
// ===========================================================================

export default function (pi: ExtensionAPI) {
  pi.on("session_start", (_event, ctx) => {
    ctx.ui.notify(
      "Feature tester loaded: take_screenshot, record_walkthrough, run_e2e_test",
      "info"
    );
  });

  // =========================================================================
  // take_screenshot
  // =========================================================================

  pi.registerTool({
    name: "take_screenshot",
    label: "Take Screenshot",
    promptSnippet:
      "Take a screenshot of a web page on staging (admin/extranet/vendor) using Playwright",
    promptGuidelines: [
      "Use take_screenshot to visually verify UI changes on staging. Prefer this over 'read' for web pages.",
      "Use take_screenshot when the user asks for a screenshot of a page or UI element.",
      "Shorthand URLs: 'admin' = test-admin, 'extranet' = test-extranet, 'vendor' = vendor portal.",
      "After taking a screenshot, tell the user the file path and size.",
    ],
    description:
      "Navigate to a URL on staging and take a screenshot. " +
      "Can capture full page or a specific CSS element. " +
      "Screenshots are saved to the workspace Media-Inbox directory.",
    parameters: Type.Object({
      url: Type.String({
        description:
          "URL or shorthand: 'admin', 'extranet', 'vendor', 'admin/commercial-ops/extranet', or full URL",
      }),
      selector: Type.Optional(
        Type.String({
          description:
            "CSS selector for a specific element. Omit for full-page screenshot.",
        })
      ),
      viewport: Type.Optional(
        Type.String({
          description: "Viewport WxH (default: 1280x720). Use 1920x1080 for full desktop.",
        })
      ),
      wait_ms: Type.Optional(
        Type.Number({
          description: "Wait ms after page load before screenshot (default: 2000)",
        })
      ),
      output_filename: Type.Optional(
        Type.String({
          description: "Custom .png filename. Auto-generated with timestamp if omitted.",
        })
      ),
    }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      const url = resolveUrl(params.url);
      ensureDir(WORKSPACE_MEDIA);
      const filename =
        params.output_filename ||
        `screenshot-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
      const outputPath = join(WORKSPACE_MEDIA, filename);

      const code = screenshotCode(url, outputPath, params.selector, params.viewport, params.wait_ms, readAuthConfig(ctx.cwd));
      const script = writeTempScript(ctx.cwd, code);

      try {
        const { stdout, stderr, exitCode } = await runNodeScript(ctx.cwd, script, signal);
        const parsed = safeJson(stdout);
        cleanup(script);

        if (exitCode !== 0 || !parsed?.ok) {
          return fail(`Screenshot failed for ${url}`, {
            url,
            error: parsed?.error || stderr || "Unknown error",
          });
        }

        const kb = parsed.size ? ` (${(parsed.size / 1024).toFixed(1)} KB)` : "";
        return {
          content: [{ type: "text", text: `Screenshot taken${kb}: ${outputPath}\nURL: ${url}` }],
          details: { success: true, path: outputPath, url, size: parsed.size },
        };
      } catch (e: any) {
        cleanup(script);
        return fail(`Screenshot crashed: ${e.message}`, { url, error: e.message });
      }
    },
  });

  // =========================================================================
  // record_walkthrough
  // =========================================================================

  pi.registerTool({
    name: "record_walkthrough",
    label: "Record Walkthrough",
    promptSnippet:
      "Record a video walkthrough of multi-step browser interactions on staging",
    promptGuidelines: [
      "Use record_walkthrough to create a video demonstrating a feature for PRs.",
      "Use record_walkthrough when the user asks to record a demo or feature walkthrough.",
      "Keep walkthroughs short (under 2 min). Focus on key flows.",
      "Actions: navigate(url), click(selector), type(selector,value), wait(ms|selector), hover(selector), select(selector,value), screenshot.",
    ],
    description:
      "Record a video of a sequence of browser interactions on staging. " +
      "Moves the mouse smoothly before clicks/hovers for natural-looking video. " +
      "Each step is an action: navigate, click, type, wait, hover, select, screenshot, move_mouse. " +
      "Videos are saved as .webm files in the workspace Media-Inbox. " +
      "Ideal for PR walkthroughs.",
    parameters: Type.Object({
      steps: Type.Array(
        Type.Object({
          action: Type.String({
            description: "Action: navigate, click, type, wait, hover, select, screenshot, move_mouse",
          }),
          url: Type.Optional(Type.String({ description: "URL (for navigate)" })),
          selector: Type.Optional(Type.String({ description: "CSS selector (for click/type/hover/select/wait/move_mouse)" })),
          value: Type.Optional(Type.String({ description: "Value (for type or select)" })),
          waitAfter: Type.Optional(Type.Number({ description: "Extra wait ms after this step (default: 800)" })),
          ms: Type.Optional(Type.Number({ description: "Wait duration ms (for wait action)" })),
          x: Type.Optional(Type.Number({ description: "X coordinate (for move_mouse with absolute coords)" })),
          y: Type.Optional(Type.Number({ description: "Y coordinate (for move_mouse with absolute coords)" })),
          duration: Type.Optional(Type.Number({ description: "Movement duration ms (for move_mouse, default: 500)" })),
          fullPage: Type.Optional(Type.Boolean({ description: "Full page screenshot? (for screenshot action)" })),
          path: Type.Optional(Type.String({ description: "Custom path (for screenshot action)" })),
        }),
        { description: "Sequence of browser interaction steps" }
      ),
      base_url: Type.Optional(
        Type.String({ description: "Base URL shorthand or full URL for relative step URLs" })
      ),
      output_filename: Type.Optional(
        Type.String({ description: "Custom .webm filename. Auto-generated if omitted." })
      ),
      headed: Type.Optional(
        Type.Boolean({ description: "Use headed browser + screen recording for real cursor (Hyprland/Wayland only). Default: false (headless with fake cursor)." })
      ),
    }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      ensureDir(WORKSPACE_MEDIA);
      const filename =
        params.output_filename ||
        `walkthrough-${new Date().toISOString().replace(/[:.]/g, "-")}.webm`;
      const outputPath = join(WORKSPACE_MEDIA, filename);

      const resolved = params.steps.map((s: any) => ({
        ...s,
        url: s.url ? resolveUrl(s.url) : s.url,
      }));
      const baseUrl = params.base_url ? resolveUrl(params.base_url) : undefined;
      const auth = readAuthConfig(ctx.cwd);

      // --- Headed mode: real browser + screen recording ---
      if (params.headed) {
        return await runHeadedWalkthrough(ctx, resolved, outputPath, baseUrl, auth, signal);
      }

      // --- Headless mode: fake cursor + Playwright video recording ---
      const code = walkthroughCode(JSON.stringify(resolved), outputPath, baseUrl, auth);
      const script = writeTempScript(ctx.cwd, code);

      try {
        const { stdout, stderr, exitCode } = await runNodeScript(ctx.cwd, script, signal, 300_000);
        const parsed = safeJson(stdout);
        cleanup(script);

        if (exitCode !== 0 || !parsed?.ok) {
          return fail(
            `Walkthrough failed (${params.steps.length} steps)`,
            { steps: params.steps.length, error: parsed?.error || stderr }
          );
        }

        const warn = parsed.failed ? " (some steps failed — check video for error screenshots)" : "";
        return {
          content: [{
            type: "text",
            text: `Walkthrough recorded: ${parsed.path || outputPath}\n${params.steps.length} steps${warn}`,
          }],
          details: { success: true, videoPath: parsed.path || outputPath, steps: params.steps.length },
        };
      } catch (e: any) {
        cleanup(script);
        return fail(`Walkthrough crashed: ${e.message}`, { steps: params.steps.length, error: e.message });
      }
    },
  });

  // =========================================================================
  // run_e2e_test
  // =========================================================================

  pi.registerTool({
    name: "run_e2e_test",
    label: "Run E2E Test",
    promptSnippet:
      "Run a Playwright E2E test file against staging with video and screenshot capture",
    promptGuidelines: [
      "Use run_e2e_test to run existing Playwright tests and capture results.",
      "Use run_e2e_test when the user wants to verify an E2E test passes on staging.",
      "After running, report pass/fail status. The project's playwright config handles video/screenshot capture.",
    ],
    description:
      "Run a Playwright test file against a target environment. " +
      "Uses the project's existing playwright.config.ts. " +
      "Captures video and screenshots as configured in the project.",
    parameters: Type.Object({
      test_file: Type.String({
        description: "Path to test file relative to project root (e.g., 'playwright/tests/approvals.spec.ts')",
      }),
      base_url: Type.Optional(
        Type.String({ description: "Base URL shorthand or full URL (default: 'admin')" })
      ),
      project: Type.Optional(
        Type.String({ description: "Playwright project name from config (e.g., 'admin-desktop')" })
      ),
      project_root: Type.Optional(
        Type.String({ description: "Project root. Auto-detected if omitted." })
      ),
    }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      const cwd = params.project_root || ctx.cwd;
      const configTs = join(cwd, "playwright.config.ts");
      const configJs = join(cwd, "playwright.config.js");

      if (!existsSync(configTs) && !existsSync(configJs)) {
        return {
          content: [{
            type: "text",
            text: `No playwright.config.ts/js found in ${cwd}. Only www-le-admin has Playwright currently configured. Set project_root or cd to a project with Playwright.`,
          }],
          details: { success: false, cwd, reason: "no-playwright-config" },
        };
      }

      const baseUrl = params.base_url ? resolveUrl(params.base_url) : STAGING.admin;
      const args = ["playwright", "test", params.test_file];
      if (params.project) args.push("--project", params.project);

      try {
        const { stdout, stderr, exitCode } = await runNodeScript(
          cwd, "npx", signal, 300_000,
          args,
          { ...process.env, PW_BASE_URL: baseUrl }
        );

        if (exitCode !== 0) {
          return {
            content: [{
              type: "text",
              text: `E2E test FAILED: ${params.test_file}\nBase: ${baseUrl}\n\n${stdout.slice(-3000)}\n${stderr.slice(-1000)}`,
            }],
            details: { success: false, testFile: params.test_file, baseUrl, exitCode },
          };
        }

        return {
          content: [{
            type: "text",
            text: `E2E test PASSED: ${params.test_file}\nBase URL: ${baseUrl}\n${stdout.slice(-2000)}`,
          }],
          details: { success: true, testFile: params.test_file, baseUrl },
        };
      } catch (e: any) {
        return fail(`E2E test crashed: ${e.message}`, {
          testFile: params.test_file, baseUrl, error: e.message,
        });
      }
    },
  });

  // =========================================================================
  // Command: /feature-test-status
  // =========================================================================

  pi.registerCommand("feature-test-status", {
    description: "Show feature tester status and artifact directory contents",
    handler: async (_args, ctx) => {
      const { readdir } = await import("node:fs/promises");
      const files = existsSync(WORKSPACE_MEDIA) ? await readdir(WORKSPACE_MEDIA) : [];
      const pngs = files.filter((f: string) => f.endsWith(".png")).length;
      const vids = files.filter((f: string) => f.endsWith(".webm") || f.endsWith(".mp4")).length;
      ctx.ui.notify(
        `Feature tester: ${WORKSPACE_MEDIA}\n${pngs} screenshots, ${vids} videos`,
        pngs + vids > 0 ? "success" : "info"
      );
    },
  });
}

// ===========================================================================
// Low-level helpers
// ===========================================================================

async function runNodeScript(
  cwd: string,
  scriptOrCmd: string,
  signal?: AbortSignal,
  timeoutMs = 60_000,
  argsOverride?: string[],
  envOverride?: Record<string, string>,
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  const isPath = scriptOrCmd.includes("/") || scriptOrCmd.endsWith(".mjs");
  const env = await buildPlaywrightEnv(envOverride);

  if (isPath) {
    const result = await execFileAsync("node", [scriptOrCmd], {
      cwd,
      timeout: timeoutMs,
      signal,
      maxBuffer: 10 * 1024 * 1024, // 10MB
      env,
    });
    return { stdout: result.stdout, stderr: result.stderr, exitCode: 0 };
  } else {
    const cmd = scriptOrCmd;
    const args = argsOverride || [];
    try {
      const result = await execFileAsync(cmd, args, {
        cwd,
        timeout: timeoutMs,
        signal,
        maxBuffer: 10 * 1024 * 1024,
        env,
      });
      return { stdout: result.stdout, stderr: result.stderr, exitCode: 0 };
    } catch (e: any) {
      return {
        stdout: e.stdout || "",
        stderr: e.stderr || "",
        exitCode: e.code || 1,
      };
    }
  }
}

/**
 * Build environment vars for Playwright child processes.
 * Resolves nixpkgs playwright-driver.browsers path and sets
 * PLAYWRIGHT_BROWSERS_PATH + PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS.
 */
async function buildPlaywrightEnv(base?: Record<string, string>): Promise<Record<string, string>> {
  const env = { ...(base || process.env) };

  // If already explicitly set, keep it
  if (!env.PLAYWRIGHT_BROWSERS_PATH) {
    const nixPath = await resolvePlaywrightBrowsersPath();
    if (nixPath) {
      env.PLAYWRIGHT_BROWSERS_PATH = nixPath;
    }
  }

  if (!env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS) {
    env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = "true";
  }

  return env;
}

// ===========================================================================
// Headed walkthrough: Hyprland headless output + wf-recorder
// ===========================================================================

async function runHeadedWalkthrough(
  ctx: any,
  steps: any[],
  outputPath: string,
  baseUrl: string | undefined,
  auth: { login: string; password: string; authHost: string } | null,
  signal?: AbortSignal,
) {
  // 1. Check prerequisites
  try {
    await execFileAsync("which", ["hyprctl"], { timeout: 2000 });
    await execFileAsync("which", ["wf-recorder"], { timeout: 2000 });
    await execFileAsync("which", ["nix"], { timeout: 2000 });
  } catch {
    return fail("Headed mode requires Hyprland + wf-recorder + nix. Not available on this system.", {});
  }

  // 2. Create headless output
  try {
    await execFileAsync("hyprctl", ["output", "create", "headless"], { timeout: 5000 });
  } catch {
    return fail("Could not create headless output via hyprctl.", {});
  }

  // 3. Find the headless output name and position
  let outputName = "";
  let outX = -100, outY = 0;
  try {
    const { stdout } = await execFileAsync("nix", ["run", "nixpkgs#wlr-randr", "--"], { timeout: 5000 });
    const lines = stdout.split("\n");
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith("HEADLESS-")) {
        outputName = lines[i].split(' "')[0].trim();
        // Parse position from next lines
        for (let j = i; j < Math.min(i + 10, lines.length); j++) {
          const posMatch = lines[j].match(/Position:\s*(-?\d+),(-?\d+)/);
          if (posMatch) {
            outX = parseInt(posMatch[1], 10);
            outY = parseInt(posMatch[2], 10);
            break;
          }
        }
        break;
      }
    }
    if (!outputName) throw new Error("Could not find HEADLESS output");
  } catch (e: any) {
    // Clean up
    try { await execFileAsync("hyprctl", ["output", "remove", "HEADLESS-"], { timeout: 2000 }); } catch {}
    return fail(`Could not detect headless output: ${e.message}`, {});
  }

  // 4. Start screen recording
  const videoOutput = outputPath.endsWith(".mp4") ? outputPath : outputPath.replace(/\.webm$/, ".mp4");
  const recorder = execFileAsync("wf-recorder", [
    "-o", outputName,
    "-f", videoOutput,
  ], { timeout: 600_000 }); // 10 min max

  // Wait a beat for recorder to start
  await new Promise(r => setTimeout(r, 800));

  // 5. Generate and run the headed script
  const code = walkthroughHeadedCode(JSON.stringify(steps), videoOutput, baseUrl, auth, outX, outY);
  const script = writeTempScript(ctx.cwd, code);

  let walkthroughResult: { stdout: string; stderr: string; exitCode: number };
  try {
    walkthroughResult = await runNodeScript(ctx.cwd, script, signal, 300_000);
  } finally {
    cleanup(script);
  }

  // 6. Give recorder a moment to flush final frames, then stop it
  await new Promise(r => setTimeout(r, 2000));
  try { await execFileAsync("killall", ["wf-recorder"], { timeout: 3000 }); } catch {}

  // 7. Remove headless output
  try { await execFileAsync("hyprctl", ["output", "remove", outputName], { timeout: 3000 }); } catch {}

  const parsed = safeJson(walkthroughResult.stdout);
  if (walkthroughResult.exitCode !== 0 || !parsed?.ok) {
    return fail(`Headed walkthrough failed (${steps.length} steps)`, {
      steps: steps.length,
      error: parsed?.error || walkthroughResult.stderr,
    });
  }

  return {
    content: [{
      type: "text",
      text: `Walkthrough recorded (headed): ${videoOutput}\n${steps.length} steps${parsed.failed ? " (some steps failed)" : ""}`,
    }],
    details: { success: true, videoPath: videoOutput, steps: steps.length },
  };
}

function safeJson(raw: string): Record<string, any> | null {
  try {
    return JSON.parse(raw.trim());
  } catch {
    // Try to find a JSON line
    const lines = raw.split("\n");
    for (const line of lines) {
      try { return JSON.parse(line.trim()); } catch {}
    }
    return null;
  }
}

function fail(summary: string, details: Record<string, any>) {
  return {
    content: [{ type: "text" as const, text: summary }],
    details: { success: false, ...details },
  };
}
