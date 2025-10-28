# ABOUTME: Tool metadata registry for tracking tool sources and schemas
# ABOUTME: Enables distinction between local and MCP tools for frontend consumption

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ToolSource(str, Enum):
    """Enumeration of tool sources."""
    LOCAL = "local"
    MCP = "mcp"


class ToolMetadata(BaseModel):
    """Metadata about a tool."""
    name: str = Field(..., description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    source: ToolSource = Field(..., description="Tool source (local or mcp)")

    class Config:
        use_enum_values = True


class ToolRegistry:
    """Registry of available tools with metadata."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}

    def register_tool(self, tool: ToolMetadata) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool

    def get_tool_source(self, name: str) -> Optional[ToolSource]:
        """Get the source of a specific tool."""
        tool = self._tools.get(name)
        return tool.source if tool else None

    def get_all_tools(self) -> Dict[str, ToolMetadata]:
        """Get all registered tools."""
        return self._tools.copy()


# Global registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _tool_registry
