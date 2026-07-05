"""Plugin System — extensible hooks for the agent loop.

Plugins can hook into lifecycle events:
- ``on_start`` — agent loop begins
- ``on_step`` — after each agent step (event, state)
- ``on_tool_call`` — tool is about to be called
- ``on_tool_result`` — tool result received
- ``on_error`` — error occurred
- ``on_finish`` — agent loop ends
"""

from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.plugins")

# ── Hook registry ───────────────────────────────────────────

_HOOKS: dict[str, list[Callable[..., Any]]] = {
    "on_start": [],
    "on_step": [],
    "on_tool_call": [],
    "on_tool_result": [],
    "on_error": [],
    "on_finish": [],
}


# ── Base plugin class ───────────────────────────────────────


class Plugin:
    """Base class for all plugins.

    Subclass and override the hooks you need::

        class MyPlugin(Plugin):
            name = "my_plugin"

            def on_start(self, task: str) -> None:
                logger.info("Task starting: %s", task)

            def on_finish(self, task: str, result: str, duration_s: float) -> None:
                logger.info("Task finished in %.2fs", duration_s)
    """

    name: str = ""

    def on_start(self, task: str) -> None:
        pass

    def on_step(self, event: Any, state: Any) -> None:
        pass

    def on_tool_call(self, tool_name: str, args: dict) -> None:
        pass

    def on_tool_result(self, tool_name: str, result: Any) -> None:
        pass

    def on_error(self, error: Exception) -> None:
        pass

    def on_finish(self, task: str, result: str, duration_s: float) -> None:
        pass


# ── Registration ────────────────────────────────────────────


def register(plugin: Plugin) -> None:
    """Register a plugin instance, wiring its hook methods.

    Only hooks overridden on ``type(plugin)`` (not the Plugin base) are wired —
    default no-op methods from Plugin are skipped.
    """
    for hook_name in _HOOKS:
        method = getattr(plugin, hook_name, None)
        if method is None:
            continue
        # Compare underlying functions so the bound-vs-unbound distinction
        # does not falsely mark base no-ops as overridden.
        base_func = getattr(Plugin, hook_name, None)
        plugin_func = getattr(method, "__func__", method)
        if plugin_func is base_func:
            continue  # inherited base no-op — skip
        # Sanity: confirm the subclass actually declares/overrides this hook.
        if hook_name not in getattr(type(plugin), "__dict__", {}):
            # Walk MRO to detect overrides in intermediate subclasses.
            mro = type(plugin).__mro__[:-1]  # exclude `object`
            if not any(hook_name in parent.__dict__ for parent in mro if parent is not Plugin):
                continue
        _HOOKS[hook_name].append(method)
        logger.debug("Plugin %s registered hook: %s", plugin.name, hook_name)


def unregister(plugin: Plugin) -> None:
    """Remove all hooks for a plugin instance."""
    for hook_name in _HOOKS:
        _HOOKS[hook_name] = [
            fn for fn in _HOOKS[hook_name]
            if fn.__self__ is not plugin
        ]
    logger.debug("Plugin %s unregistered", plugin.name)


# ── Hook execution ──────────────────────────────────────────


def fire(hook_name: str, *args: Any, **kwargs: Any) -> None:
    """Execute all registered hook functions."""
    for fn in _HOOKS.get(hook_name, []):
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.warning("Plugin hook %s failed: %s", hook_name, exc)


# ── Discovery ────────────────────────────────────────────────

_PLUGIN_DIRS = [
    Path.home() / ".config" / "aiw" / "plugins",
    Path(os.getenv("AIW_PLUGIN_DIR", "")),
]


def discover(plugin_dirs: list[Path] | None = None) -> list[Plugin]:
    """Discover and load plugins from plugin directories.

    Each plugin is a Python file (.py) in the plugin directory
    that defines a subclass of ``Plugin``.

    Returns the list of loaded plugin instances.
    """
    dirs = plugin_dirs or [d for d in _PLUGIN_DIRS if d and d.is_dir()]
    plugins: list[Plugin] = []

    for plugin_dir in dirs:
        if not plugin_dir.is_dir():
            continue

        for py_file in sorted(plugin_dir.glob("*.py")):
            try:
                mod_name = f"aiw_plugin_{py_file.stem}"
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if spec is None or spec.loader is None:
                    continue

                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)

                # Find Plugin subclasses
                for _name, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, Plugin) and obj is not Plugin:
                        instance = obj()
                        register(instance)
                        plugins.append(instance)
                        logger.info("Loaded plugin: %s", instance.name)

            except Exception as exc:
                logger.warning("Failed to load plugin %s: %s", py_file, exc)

    return plugins
