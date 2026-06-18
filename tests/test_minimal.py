"""Test minimal TUI v3."""
import asyncio
from ai_workspace.tui.app import AIWorkspaceApp


async def test():
    app = AIWorkspaceApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(1.5)  # Let on_mount + push_screen complete

        print(f"Screen stack: {len(app.screen_stack)}")
        print(f"Top screen: {type(app.screen).__name__}")
        print(f"_main: {app._main}")

        if app._main is None:
            print("ERROR: MainScreen not pushed")
            return

        main = app._main

        print("=== Widget tree ===")

        def tree(w, d=0):
            name = type(w).__name__
            wid = f" #{w.id}" if w.id else ""
            print(f"  {'  ' * d}{name}{wid}")
            for c in w.children:
                tree(c, d + 1)

        tree(main)

        def count(w):
            return 1 + sum(count(c) for c in w.children)

        total = count(main)
        print(f"\nTotal widgets: {total}")
        print(f"CSS_PATH: {app.CSS_PATH}")
        print(f"CSS exists: {app.CSS_PATH.exists()}")
        print("\n[OK] Minimal TUI works")


asyncio.run(test())
