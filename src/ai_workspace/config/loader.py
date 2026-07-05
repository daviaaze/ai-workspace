"""
YAML config loader for crewAI agents and tasks.

Usage:
    from ai_workspace.config.loader import load_agent, load_task

    agent = load_agent("researcher", llm=my_llm)
    task = load_task("research_plan", topic="Nix flakes", agent=agent)

Supports {variable} interpolation and LLM assignment from SwarmConfig.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the config directory."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        logger.warning("Config file not found: %s", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_agent(
    name: str,
    llm: Any = None,
    tools: list[Any] | None = None,
    **overrides,
):
    """Load an agent definition from agents.yaml.

    Args:
        name: Agent key in agents.yaml (e.g. "researcher", "coder")
        llm: crewAI LLM instance (from SwarmConfig)
        tools: List of crewAI tools for this agent
        **overrides: Any additional Agent keyword args to override YAML

    Returns:
        A crewAI Agent configured from YAML + overrides.

    Example:
        agent = load_agent("researcher", llm=cfg.deep_llm)
        agent = load_agent("coder", llm=cfg.coder_llm, tools=git_tools, verbose=False)
    """
    from crewai import Agent

    agents = _load_yaml("agents.yaml")
    config = agents.get(name, {})

    if not config:
        logger.warning("Agent '%s' not found in agents.yaml, using defaults", name)
        config = {"role": name, "goal": "Complete the task", "backstory": ""}

    # Clean up multi-line YAML strings (strip extra whitespace)
    for key in ("role", "goal", "backstory"):
        if key in config and isinstance(config[key], str):
            config[key] = " ".join(config[key].split())

    # Apply overrides
    config.update(overrides)

    # Inject LLM
    if llm is not None:
        config["llm"] = llm

    # Inject tools
    if tools is not None:
        config["tools"] = tools

    return Agent(**config)


def load_task(
    name: str,
    agent=None,
    context=None,
    output_pydantic: type | None = None,
    **variables,
):
    """Load a task template from tasks.yaml with variable interpolation.

    Args:
        name: Task key in tasks.yaml (e.g. "research_plan")
        agent: crewAI Agent to assign to this task
        context: List of upstream tasks for dependency
        output_pydantic: Optional Pydantic model for structured output
        **variables: Values to interpolate into {placeholders} in description

    Returns:
        A crewAI Task with interpolated description.

    Example:
        task = load_task("research_plan", topic="What is Nix?", agent=researcher)
    """
    from crewai import Task

    tasks = _load_yaml("tasks.yaml")
    config = tasks.get(name, {})

    if not config:
        logger.warning("Task '%s' not found in tasks.yaml", name)
        config = {
            "description": str(variables.get("task", name)),
            "expected_output": "Complete the task",
        }

    # Clean up multi-line strings
    for key in ("description", "expected_output"):
        if key in config and isinstance(config[key], str):
            config[key] = " ".join(config[key].split())

    # Interpolate variables
    description = config.get("description", "")
    expected_output = config.get("expected_output", "")
    try:
        description = description.format(**variables)
        expected_output = expected_output.format(**variables)
    except KeyError as e:
        logger.warning(
            "Missing variable %s for task '%s' — leaving placeholder", e, name
        )

    task_kwargs: dict[str, Any] = {
        "description": description,
        "expected_output": expected_output,
    }

    if agent is not None:
        task_kwargs["agent"] = agent
    if context is not None:
        task_kwargs["context"] = context
    if output_pydantic is not None:
        task_kwargs["output_pydantic"] = output_pydantic

    return Task(**task_kwargs)


def list_agents() -> list[str]:
    """List all defined agent names."""
    agents = _load_yaml("agents.yaml")
    return sorted(agents.keys())


def list_tasks() -> list[str]:
    """List all defined task template names."""
    tasks = _load_yaml("tasks.yaml")
    return sorted(tasks.keys())
