"""Headless TUI tests for AI Workspace v3 Cyberdeck layout."""
import asyncio

from ai_workspace.tui.app import AIWorkspaceApp


async def test_widget_tree():
    """Verify all core widgets are composed correctly."""
    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause(1.0)

        print("=== Widget Tree ===")
        def show_tree(w, depth=0):
            indent = "  " * depth
            name = type(w).__name__
            wid = getattr(w, "id", "") or ""
            info = f"#{wid}" if wid else ""
            extra = ""
            if hasattr(w, "collapsed"):
                extra = f" [collapsed={w.collapsed}]"
            print(f"{indent}{name} {info}{extra}")
            for child in w.children:
                show_tree(child, depth + 1)
        show_tree(app.screen)

        print()
        print("=== Key Widget Checks ===")
        checks = [
            ("header-bar", "HeaderBar"),
            ("cyberdeck", "CyberdeckLayout"),
            ("cyberdeck-center", "VerticalScroll"),
            ("left-stack", "SidePanelStack"),
            ("right-stack", "SidePanelStack"),
            ("bottom-panel", "BottomPanel"),
            ("bottom-bar", "BottomBar"),
        ]
        all_ok = True
        for wid, expected in checks:
            try:
                w = app.query_one(f"#{wid}")
                actual = type(w).__name__
                ok = actual == expected
                print(f"  {'✓' if ok else '✗'} #{wid} ({actual})")
                if not ok:
                    all_ok = False
            except Exception as e:
                print(f"  ✗ #{wid} MISSING: {e}")
                all_ok = False

        if all_ok:
            print("\nALL WIDGETS PRESENT ✓")
        else:
            print("\nSOME WIDGETS MISSING ✗")

        # Check side panels are collapsed by default
        try:
            left = app.query_one("#left-stack")
            panels = [c for c in left.children]
            print(f"\nLeft stack panels: {len(panels)}")
            for p in panels:
                c = getattr(p, 'collapsed', '?')
                print(f"  {type(p).__name__} collapsed={c}")
        except Exception as e:
            print(f"Left stack check failed: {e}")


async def test_panel_toggles():
    """Test panel toggle keybindings."""
    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause(1.0)

        print("\n=== Panel Toggle Tests ===")

        # Test Ctrl+1: toggle left panel
        try:
            left_panel = app.query_one("#sp-agents")
            print(f"Left panel initial: collapsed={left_panel.collapsed}")
            await pilot.press("ctrl+1")
            await pilot.pause(0.3)
            print(f"Left panel after ^1: collapsed={left_panel.collapsed}")
            await pilot.press("ctrl+1")
            await pilot.pause(0.3)
            print(f"Left panel after ^1 again: collapsed={left_panel.collapsed}")
        except Exception as e:
            print(f"Left panel test failed: {e}")

        # Test Ctrl+2: toggle right panel
        try:
            right_panel = app.query_one("#sp-context")
            print(f"Right panel initial: collapsed={right_panel.collapsed}")
            await pilot.press("ctrl+2")
            await pilot.pause(0.3)
            print(f"Right panel after ^2: collapsed={right_panel.collapsed}")
            await pilot.press("ctrl+2")
            await pilot.pause(0.3)
            print(f"Right panel after ^2 again: collapsed={right_panel.collapsed}")
        except Exception as e:
            print(f"Right panel test failed: {e}")

        # Test Ctrl+3: toggle bottom panel
        try:
            bp = app.query_one("#bottom-panel")
            print(f"Bottom panel initial: collapsed={bp.collapsed}")
            await pilot.press("ctrl+3")
            await pilot.pause(0.3)
            print(f"Bottom panel after ^3: collapsed={bp.collapsed}")
        except Exception as e:
            print(f"Bottom panel test failed: {e}")

        # Test Ctrl+\: zen mode
        try:
            await pilot.press("ctrl+backslash")
            await pilot.pause(0.3)
            left = app.query_one("#sp-agents")
            right = app.query_one("#sp-context")
            bp = app.query_one("#bottom-panel")
            print(f"Zen mode: left={left.collapsed}, right={right.collapsed}, bottom={bp.collapsed}")
        except Exception as e:
            print(f"Zen mode test failed: {e}")


async def test_quick_input():
    """Test the bottom input bar."""
    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause(1.0)

        print("\n=== Quick Input Tests ===")
        try:
            inp = app.query_one("#bb-input")
            print(f"Input found: placeholder='{inp.placeholder}'")
            await pilot.click(inp)
            await pilot.pause(0.2)
            has_focus = inp.has_focus
            print(f"Input focused: {has_focus}")
        except Exception as e:
            print(f"Input test failed: {e}")


async def test_agent_inventory_populated():
    """Verify agent inventory panel is populated into left stack."""
    app = AIWorkspaceApp()
    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause(1.5)  # Wait for set_timer(0.1) to populate

        print("\n=== Agent Inventory Test ===")
        try:
            inventory = app.query_one("#agent-inventory")
            print(f"✓ AgentInventoryPanel found: {type(inventory).__name__}")

            # Check for spawn button
            spawn_btn = app.query_one("#inv-spawn")
            print(f"✓ Spawn button found: {spawn_btn.label}")

            # Check empty state
            cards = [c for c in inventory.query("#inv-cards").first().children
                     if hasattr(c, 'id')]
            print(f"  Cards: {len(cards)}")
        except Exception as e:
            print(f"✗ Agent inventory test failed: {e}")


async def main():
    await test_widget_tree()
    await test_panel_toggles()
    await test_quick_input()
    await test_agent_inventory_populated()
    print("\n=== All tests complete ===")


if __name__ == "__main__":
    asyncio.run(main())
