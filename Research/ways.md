# ways — Research

**Date:** 2026-06-10
**Type:** spike
**Time-box:** 

## Goal
How can AI agents (like pi) perform end-to-end testing of Shade — a Hyprland-based GJS/GTK4 desktop shell — with automated visual feedback (screenshots and recordings), and how can the current infrastructure be improved?

## Approach
- Audit existing agent-driven e2e infrastructure (VM configs, VNC automation, MCP server, smoke test scripts)
- Identify concrete pain points and gaps
- Propose specific, actionable improvements ranked by impact
- Evaluate trade-offs for each improvement

## Findings

### 1. Current Infrastructure

The project already has a solid foundation:

| Component | Path | Status |
|-----------|------|--------|
| **VNC-enabled VM** | `nix/vm-vnc.nix` | ✅ Exposes QEMU display on localhost:5901 |
| **VNC automation CLI** | `vncdo` (v1.2.0) | ✅ Capture, key, type, mousemove, click |
| **MCP server (VNC tools)** | `scripts/vnc-mcp-server.py` | ✅ screenshot, send_key, type_text, mouse_click, mouse_move, save_screenshot |
| **Agent smoke test** | `scripts/agent-smoke-test.py` | ✅ 5-phase test with sequential screenshots |
| **Agent full test** | `scripts/agent-full-test.py` | ✅ 7-phase test with terminal + journalctl |
| **Test orchestrator** | `scripts/run-vm-test.sh` | ✅ Boot → test → cleanup |
| **In-VM recording** | `wf-recorder` (in flake) | ✅ Available but no shared dir to extract files |
| **In-VM screenshot** | `grim` (in flake) | ✅ Available |
| **Devshell** | `nix/devshell.nix` | ✅ vncdo + mcp Python packages included |

### 2. Pain Points & Improvement Opportunities

#### 🔴 P1: No Readiness Probe — Tests Hardcode Waits

```python
wait(20)   # Phase 1: hope Shade is ready
wait(45)   # Phase 1 in full test: hope even harder
```

**Problem:** Hardcoded sleeps are brittle. If boot takes 25s, first screenshot catches a half-initialized desktop. If it takes 15s, we waste 5s.

**Solution:** Poll for readiness via multiple signals:
- VNC screen content changes (`vncdo expect` — checks pixels at a coordinate)
- SSH into VM + `systemctl --user is-active shade-shell`
- D-Bus query from host: `gdbus call ...` against Shade's bus name
- Hyprland socket check: `hyprctl monitors` (can be run via SSH into VM)

```python
def wait_for_shade(timeout: int = 60) -> bool:
    """Poll until the bar or wallpaper is visible."""
    for _ in range(timeout):
        try:
            # Option 1: Check a pixel region we know should be non-background
            vncdo("expect", "-region", "0,0,50,50", "-tolerance", "10")
            return True
        except CalledProcessError:
            pass
        # Option 2: SSH check
        # result = ssh("systemctl --user is-active shade-shell")
        time.sleep(1)
    return False
```

---

#### 🔴 P2: No Shared Filesystem Between Host and VM

**Problem:** `wf-recorder` output stays inside the VM. Journal logs require opening a terminal and typing commands via VNC (as `agent-full-test.py` does — extremely fragile).

**Solution:** Add virtiofs to `nix/vm-vnc.nix`:

```nix
# In nix/vm-vnc.nix
virtualisation.vmVariant.virtualisation.qemu.options = [
  "-vnc" "localhost:1"
  # Shared directory for test artifacts
  "-virtfs" "local,path=/tmp/shade-test-output,security_model=passthrough,mount_tag=test-output"
];
```

Then mount inside VM:
```nix
# In vm.nix
fileSystems."/mnt/test-output" = {
  device = "test-output";
  fsType = "9p";
  options = ["trans=virtio", "version=9p2000.L"];
};
```

Now:
- `wf-recorder` writes to `/mnt/test-output/recording.mp4` → accessible at `/tmp/shade-test-output/` on host
- `journalctl > /mnt/test-output/journal.log` for log extraction
- Golden images can be stored there for comparison

---

#### 🔴 P3: No Shared Test Library — Duplicated Boilerplate

`agent-smoke-test.py` and `agent-full-test.py` duplicate:
- `vncdo()` helper
- `screenshot()` helper
- `wait()` helper
- `wait_for_vnc()` helper
- Error handling patterns

**Solution:** Extract `shadetest/` library:

```
scripts/
  shadetest/
    __init__.py        # export VNCConfig, ShadeTestHarness
    _vnc.py            # VNC connection, vncdo wrapper
    _screenshot.py     # screenshot capture + comparison
    _assert.py         # visual assertions (region check, golden image diff)
    _vm.py             # VM lifecycle (boot, wait, shutdown)
  agent-smoke-test.py  # imports from shadetest
  agent-full-test.py   # imports from shadetest
```

```python
# scripts/shadetest/__init__.py
class ShadeTestHarness:
    def __init__(self, vnc_host="localhost", vnc_port=5901):
        self.vnc = VNCClient(vnc_host, vnc_port)

    def screenshot(self, name: str) -> Path: ...
    def send_key(self, key: str) -> None: ...
    def type_text(self, text: str) -> None: ...
    def click(self, x: int, y: int) -> None: ...

    def wait_until_shade_ready(self, timeout=60) -> bool: ...
    def wait_until_widget_open(self, widget: str, timeout=10) -> bool: ...

    def assert_screenshot_matches(self, name: str, golden: Path, threshold=0.05) -> bool: ...
    def assert_screenshot_differs(self, name: str, baseline: Path, threshold=0.05) -> bool: ...
```

---

#### 🔴 P4: No Vision-Based Assertions

**Problem:** Screenshots are captured but never asserted against. The agent must manually inspect every image. No regression detection.

**Solution A: Pixel-level (fast, dumb)**
```python
from PIL import Image, ImageChops

def assert_region_not_blank(img: Path, x1, y1, x2, y2) -> bool:
    """Fail if a screen region is all one color (widget didn't render)."""
    region = Image.open(img).crop((x1, y1, x2, y2))
    extrema = region.getextrema()
    return not all(lo == hi for lo, hi in extrema)  # not blank

def assert_screenshot_differs_from(baseline: Path, current: Path) -> bool:
    """Fail if screenshots are identical (interaction had no effect)."""
    return ImageChops.difference(
        Image.open(baseline), Image.open(current)
    ).getbbox() is not None
```

**Solution B: AI-assisted (slower, semantic)**
Use the agent's own vision capability to assess screenshots programmatically:
```python
def describe_screenshot(img_path: Path) -> str:
    """Use a VLM (vision language model) to caption what's on screen."""
    # ... call pi's vision or an API like GPT-4o
    return "Desktop with bar visible, app launcher open with search results"
```

---

#### 🟠 P5: MCP Server Lives Independently of VM

**Problem:** `vnc-mcp-server.py` must be started as a separate process. If the VM isn't running, the MCP server starts but all tools fail with cryptic errors.

**Solution:** Integrate MCP server lifecycle into the orchestrator:

```bash
# run-vm-test.sh — enhanced
$VM_CMD &
VM_PID=$!

# Wait for VNC port
wait_for_vnc

# Start MCP server alongside VM
python3 scripts/vnc-mcp-server.py &
MCP_PID=$!

# Run test(s)
python3 scripts/agent-smoke-test.py

# Cleanup both
kill $MCP_PID $VM_PID
```

Or better: embed the MCP server as a subprocess of the test harness:
```python
# In ShadeTestHarness
class ShadeTestHarness:
    def start_vm(self):
        self._vm_process = subprocess.Popen(["nix", "run", VM_REF])
        self._wait_for_vnc()

    def start_mcp(self, port=5901):
        self._mcp_process = subprocess.Popen(["python3", MCP_SERVER_PATH])
        return f"http://localhost:{port}"  # MCP endpoint
```

---

#### 🟠 P6: No CI Integration

**Problem:** Tests only run manually. No regression safety net.

**Solution:** Add a GitHub Actions workflow:

```yaml
# .github/workflows/vm-test.yml
on:
  pull_request:
    paths:
      - 'src/**'
      - 'nix/**'
      - 'flake.nix'

jobs:
  vm-test:
    runs-on: [self-hosted, linux, x64]
    steps:
      - uses: actions/checkout@v4
      - name: Run VM smoke test
        run: |
          nix develop -c ./scripts/run-vm-test.sh
      - name: Upload screenshots
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-screenshots
          path: test-output/
```

**Constraint:** Needs a self-hosted runner with KVM access (NixOS builder). Not practical for GitHub-hosted runners (no KVM). Alternative: use `nix build` on the VM and run via `qemu-system` without acceleration (slow but works anywhere).

---

#### 🟠 P7: No Recording Capability

**Problem:** MCP server only offers single-frame screenshots. No way to capture a video of a test run.

**Solution A: Frame series stitching (low effort)**
```python
@mcp.tool()
def record_sequence(keys: list[str], interval_ms: int = 500) -> str:
    """Send a sequence of keys, capture screenshot after each, return frames as base64 list."""
    frames = []
    for key in keys:
        _vncdo("key", key)
        time.sleep(interval_ms / 1000)
        frames.append(screenshot())
    return frames  # or stitch into animated GIF
```

**Solution B: In-VM wf-recorder + virtiofs (best quality)**
```
# Host-side agent script
ssh vm "wf-recorder -f /mnt/test-output/test-recording.mp4 &"
# ... perform test interactions ...
ssh vm "pkill wf-recorder"
cp /tmp/shade-test-output/test-recording.mp4 ./artifacts/
```

**Solution C: VNC-to-video via ffmpeg**
```bash
# Capture VNC as video directly (no VM-side software needed)
ffmpeg -f vnc -r 10 -i localhost:5901 -c:v libx264 output.mp4
```
> ⚠️ `ffmpeg` VNC input requires `--enable-libvncserver` compile flag. Not in most nixpkgs ffmpeg builds.

---

#### 🟠 P8: Hardcoded Screen Coordinates

`agent-full-test.py` has:
```python
vncdo("mousemove", "200", "120", "click", "1")  # Magic numbers!
```

**Problem:** Coordinates change with resolution, widget config, or theme changes.

**Solution A: Named regions via template**
```python
# config/coords.yaml
applauncher:
  search_result_first: {x: 200, y: 120}
quicksettings:
  power_button: {x: 300, y: 500}
```

**Solution B: D-Bus commands instead of clicks**
Use Shade's existing D-Bus interface instead of mouse clicks for deterministic actions:
```bash
gdbus call --session --dest org.shade.Shell --object-path /org/shade/Shell --method org.shade.Shell.Toggle "applauncher"
```
This is more reliable and resolution-independent.

---

#### 🟡 P9: No Structured State Queries

**Problem:** The only way to know if a widget is open is to look at a screenshot. No programmatic assertions.

**Solution:** Expose widget state via D-Bus properties and query them from the test harness:

```python
def is_applauncher_open() -> bool:
    result = subprocess.run([
        "gdbus", "call", "--session",
        "--dest", "org.shade.Shell",
        "--object-path", "/org/shade/Shell",
        "--method", "org.freedesktop.DBus.Properties.Get",
        "org.shade.Shell", "LauncherOpen"
    ], capture_output=True, text=True)
    return "true" in result.stdout.lower()
```

This pairs with visual assertions: query state as a fast pre-check, then screenshot for visual confirmation.

---

#### 🟡 P10: Single-Use VM — No Reuse Between Tests

**Problem:** Every test run boots a fresh VM (30-60s overhead). Can't iterate quickly.

**Solution A: Keep VM alive between test runs**
```bash
# Keep VM running across multiple test invocations
./scripts/run-vm-test.sh --no-shutdown
python3 scripts/agent-smoke-test.py
python3 scripts/agent-full-test.py
./scripts/run-vm-test.sh --shutdown
```

**Solution B: VM snapshot**
```bash
# After boot + Shade ready, take a QEMU snapshot
# "savevm" in QEMU monitor, then "loadvm" for each test
(echo "savevm shade-ready"; sleep 1) | socat - UNIX-CONNECT:/tmp/qemu-monitor
# ... run test ...
(echo "loadvm shade-ready"; sleep 1) | socat - UNIX-CONNECT:/tmp/qemu-monitor
```

---

### 3. Prioritized Improvement Roadmap

| Priority | Improvement | Effort | Impact | Dependencies |
|----------|-------------|--------|--------|-------------|
| **P1** | Readiness probe (replace hardcoded waits) | 2h | High | None — can use `vncdo expect` or SSH |
| **P1** | D-Bus state queries instead of click coords | 3h | High | Shade's D-Bus interface (already exists) |
| **P2** | Shared test library (`shadetest/`) | 4h | High | None |
| **P3** | virtiofs shared directory | 2h | High | VM rebuild |
| **P4** | Vision-based assertions (pixel-level) | 3h | Medium | `Pillow` (already in devshell?) |
| **P5** | MCP server lifecycle integration | 1h | Medium | None |
| **P6** | Frame-series recording via MCP tool | 2h | Medium | None |
| **P7** | vm-vnc.nix + devshell CI integration | 4h | Medium | Self-hosted runner with KVM |
| **P8** | VM snapshot/reuse between tests | 3h | Medium | QEMU monitor socket |
| **P9** | wf-recorder + virtiofs video capture | 2h | Low | virtiofs (P3) first |
| **P10** | AI-assisted screenshot analysis | 4h | Low | Requires vision model API |

## Conclusion

The current infrastructure is a solid foundation: VNC + vncdo + MCP server + smoke test scripts all work. But several common e2e testing patterns are missing:

1. **No readiness probing** — hardcoded waits make tests brittle and slow
2. **No shared filesystem** — can't extract artifacts from inside the VM
3. **No shared test library** — duplicated boilerplate across scripts
4. **No visual assertions** — screenshots are captured but never validated programmatically
5. **No CI integration** — regression detection is entirely manual
6. **No structured state queries** — only visual inspection, no D-Bus property assertions

The most impactful changes are replacing hardcoded waits with readiness probes (P1) and extracting a shared test library (P2). These alone would make the test suite reliable and maintainable. Adding virtiofs (P3) unlocks recording and log extraction.

## Recommendation

### Sprint 1: Reliability (P1-P3)
1. Extract `scripts/shadetest/` library with `ShadeTestHarness` class
2. Add `wait_until_shade_ready()` using `vncdo expect` (pixel check) + SSH fallback
3. Add `wait_until_widget_open(widget_name)` using D-Bus property queries
4. Add virtiofs shared directory to `nix/vm-vnc.nix`

### Sprint 2: Assertions & Automation (P4-P6)
5. Add `assert_region_not_blank()` and `assert_screenshot_differs_from()` helpers
6. Add `record_sequence()` MCP tool for frame-series capture
7. Wire MCP server startup into `run-vm-test.sh`
8. Add `.github/workflows/vm-test.yml`

### Sprint 3: Polish (P7-P10)
9. VM snapshot/reuse for fast iteration
10. wf-recorder video capture via shared directory
11. AI-assisted screenshot analysis callback

## References
- MCP server: `scripts/vnc-mcp-server.py`
- Smoke test: `scripts/agent-smoke-test.py`
- Full test: `scripts/agent-full-test.py`
- Orchestrator: `scripts/run-vm-test.sh`
- VM VNC config: `nix/vm-vnc.nix`
- VM base config: `nix/vm.nix`
- Devshell: `nix/devshell.nix`
- Flake: `flake.nix`
- Screenshot module: `src/lib/screenshot.ts`
- vncdo docs: https://github.com/sibson/vncdotool
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
