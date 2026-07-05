"""Smoke tests for the Plugin System.

Covers register/unregister lifecycle, hook firing, discovery isolation,
and the Plugin base class contract.
"""

from __future__ import annotations

import pytest

from ai_workspace.plugin_system import (
    _HOOKS,
    Plugin,
    discover,
    fire,
    register,
    unregister,
)


@pytest.fixture(autouse=True)
def _clean_hooks():
    """Snapshot/restore the global hook registry so tests don't leak handlers."""
    saved = {k: list(v) for k, v in _HOOKS.items()}
    yield
    for k, v in saved.items():
        _HOOKS[k] = v


class _CallOrderPlugin(Plugin):
    """Plugin that records hook invocations into a list."""

    name = "order-test"

    def __init__(self, sink: list[str]):
        self.sink = sink

    def on_start(self, task: str) -> None:
        self.sink.append(f"start:{task}")

    def on_step(self, event, state) -> None:
        self.sink.append("step")

    def on_finish(self, task: str, result: str, duration_s: float) -> None:
        self.sink.append(f"finish:{task}")


class _NoErrorPlugin(Plugin):
    """Plugin that overrides nothing — default no-op behavior."""

    name = "noop"


class TestRegistration:
    def test_register_wires_overridden_hooks(self):
        sink: list[str] = []
        p = _CallOrderPlugin(sink)
        register(p)
        # on_start, on_step, on_finish should be wired
        assert len(_HOOKS["on_start"]) == 1
        assert len(_HOOKS["on_step"]) == 1
        assert len(_HOOKS["on_finish"]) == 1

    def test_register_skips_unchanged_hooks(self):
        """Default Plugin base no-op methods are NOT registered."""
        p = _NoErrorPlugin()
        register(p)
        # All hooks remain empty because nothing was overridden
        assert _HOOKS["on_start"] == []
        assert _HOOKS["on_step"] == []
        assert _HOOKS["on_finish"] == []

    def test_unregister_removes_all_hooks(self):
        sink: list[str] = []
        p = _CallOrderPlugin(sink)
        register(p)
        unregister(p)
        assert _HOOKS["on_start"] == []
        assert _HOOKS["on_step"] == []
        assert _HOOKS["on_finish"] == []


class TestFire:
    def test_fire_invokes_registered_hook(self):
        sink: list[str] = []
        p = _CallOrderPlugin(sink)
        register(p)
        fire("on_start", task="hello")
        assert sink == ["start:hello"]

    def test_fire_unknown_hook_is_noop(self):
        # Unknown hook name should not raise
        fire("nonexistent_hook")

    def test_fire_isolates_failing_hooks(self):
        """A hook raising should not stop other hooks from running."""
        bad_calls: list[str] = []

        class BadPlugin(Plugin):
            name = "bad"

            def on_start(self, task: str) -> None:
                raise RuntimeError("boom")

        class GoodPlugin(Plugin):
            name = "good"
            def on_start(self, task: str) -> None:
                bad_calls.append(task)

        register(BadPlugin())
        register(GoodPlugin())
        fire("on_start", task="x")
        assert bad_calls == ["x"]

    def test_fire_multiple_hooks_order_preserved(self):
        order: list[str] = []

        class P(Plugin):
            name = "p1"
            def on_finish(self, task, result, duration_s):
                order.append("p1")

        class Q(Plugin):
            name = "p2"
            def on_finish(self, task, result, duration_s):
                order.append("p2")

        register(P())
        register(Q())
        fire("on_finish", task="t", result="r", duration_s=0.0)
        assert order == ["p1", "p2"]


class TestDiscover:
    def test_discover_empty_dir_returns_empty(self, tmp_path):
        result = discover([tmp_path])
        assert result == []

    def test_discover_loads_plugin_file(self, tmp_path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            "from ai_workspace.plugin_system import Plugin\n"
            "class HelloPlugin(Plugin):\n"
            "    name = 'hello'\n"
            "    def on_start(self, task):\n"
            "        pass\n"
        )
        plugins = discover([tmp_path])
        assert len(plugins) == 1
        assert plugins[0].name == "hello"
        # And it should have been auto-registered
        assert len(_HOOKS["on_start"]) >= 1

    def test_discover_skips_broken_plugin_file(self, tmp_path):
        bad = tmp_path / "broken.py"
        bad.write_text("raise RuntimeError('nope')")
        good = tmp_path / "good.py"
        good.write_text(
            "from ai_workspace.plugin_system import Plugin\n"
            "class GoodPlugin(Plugin):\n"
            "    name = 'good'\n"
        )
        # Should not raise; should load only good
        plugins = discover([tmp_path])
        names = [p.name for p in plugins]
        assert "good" in names
        assert "broken" not in names

    def test_discover_ignores_nonexistent_dir(self, tmp_path):
        # Passing a dir that doesn't exist should be safe
        result = discover([tmp_path / "no-such-dir"])
        assert result == []


class TestPluginBase:
    def test_plugin_base_hooks_are_noops(self):
        """Default Plugin methods do nothing and don't raise."""
        p = Plugin()
        p.on_start("t")
        p.on_step(None, None)
        p.on_tool_call("name", {})
        p.on_tool_result("name", None)
        p.on_error(RuntimeError("x"))
        p.on_finish("t", "r", 0.0)
        # No exception means success
