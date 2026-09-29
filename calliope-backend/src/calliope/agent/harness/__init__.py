from calliope.agent.harness.plugins import render, script, story
from calliope.agent.harness.registry import ToolRegistry


def build_harness() -> ToolRegistry:
    registry = ToolRegistry()
    for plugin in (story, script, render):
        plugin.register(registry)
    return registry
