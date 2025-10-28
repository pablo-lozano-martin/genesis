# ABOUTME: MCP tool adapter converting MCP tool definitions to Python callables
# ABOUTME: Enables LangChain bind_tools() to work with MCP tools transparently

import json
import asyncio
from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class MCPToolDefinition(BaseModel):
    """Data transfer object for MCP tool schema."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None


class MCPToolAdapter:
    """
    Wraps MCP tool definition as Python callable for LangChain binding.

    This adapter makes MCP tools appear as native Python functions with:
    - __name__ property (tool name)
    - __doc__ property (tool description)
    - Type hints extracted from MCP schema
    - Async __call__ method for execution
    """

    def __init__(
        self,
        definition: MCPToolDefinition,
        session: Any,
        namespace: str = ""
    ):
        self.definition = definition
        self.session = session
        self.namespace = namespace
        self._build_signature()

    async def __call__(self, **kwargs) -> str:
        """
        Execute MCP tool via the MCP session.

        Args:
            **kwargs: Tool parameters from LLM

        Returns:
            String representation of tool result
        """
        try:
            logger.info(f"Executing MCP tool: {self.definition.name} with args: {kwargs}")

            # Call MCP server via session
            result = await self.session.call_tool(self.definition.name, kwargs)

            # Extract result content
            if result.content:
                # Return first content item as string
                content = result.content[0]
                if hasattr(content, 'text'):
                    return content.text
                else:
                    return str(content)

            return "Tool executed successfully (no output)"

        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return f"Error executing tool: {str(e)}"

    @property
    def __name__(self) -> str:
        """Tool name with optional namespace."""
        if self.namespace:
            return f"{self.namespace}:{self.definition.name}"
        return self.definition.name

    @property
    def __doc__(self) -> str:
        """Tool description from MCP schema."""
        return self.definition.description

    def _build_signature(self):
        """
        Extract Python function signature from MCP input_schema.

        This method would generate type hints for LangChain introspection.
        For MVP, we'll rely on the schema being passed to bind_tools directly.
        """
        pass
