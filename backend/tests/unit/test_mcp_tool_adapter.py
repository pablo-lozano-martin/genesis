# ABOUTME: Unit tests for MCPToolAdapter tool conversion and execution
# ABOUTME: Tests tool wrapping, name/doc properties, and error handling

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.langgraph.tools.mcp_adapter import MCPToolAdapter, MCPToolDefinition


def test_adapter_name_without_namespace():
    """Test tool name without namespace."""
    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock(), namespace="")

    assert adapter.__name__ == "search"


def test_adapter_name_with_namespace():
    """Test tool name with namespace prefix."""
    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock(), namespace="kb")

    assert adapter.__name__ == "kb:search"


def test_adapter_doc():
    """Test tool description extraction."""
    definition = MCPToolDefinition(
        name="search",
        description="Search the knowledge base",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock())

    assert adapter.__doc__ == "Search the knowledge base"


@pytest.mark.asyncio
async def test_adapter_call_success():
    """Test successful tool execution."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "search results"
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(query="test")

    assert result == "search results"
    mock_session.call_tool.assert_called_once_with("search", {"query": "test"})


@pytest.mark.asyncio
async def test_adapter_call_with_empty_content():
    """Test tool execution with no content in result."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.content = []
    mock_session.call_tool.return_value = mock_result

    definition = MCPToolDefinition(
        name="action",
        description="Action tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(param="value")

    assert result == "Tool executed successfully (no output)"


@pytest.mark.asyncio
async def test_adapter_call_error_handling():
    """Test error handling during tool execution."""
    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = Exception("Connection error")

    definition = MCPToolDefinition(
        name="search",
        description="Search tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(query="test")

    assert "Error executing tool" in result
    assert "Connection error" in result


@pytest.mark.asyncio
async def test_adapter_call_with_multiple_args():
    """Test tool execution with multiple arguments."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "result"
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    definition = MCPToolDefinition(
        name="calculate",
        description="Calculate tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(a=5, b=3, operation="add")

    assert result == "result"
    mock_session.call_tool.assert_called_once_with(
        "calculate",
        {"a": 5, "b": 3, "operation": "add"}
    )


@pytest.mark.asyncio
async def test_adapter_call_with_non_text_content():
    """Test tool execution with non-text content."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_content = MagicMock(spec=[])  # Empty spec means no attributes
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    definition = MCPToolDefinition(
        name="tool",
        description="Test tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, mock_session)

    result = await adapter(param="value")

    # Should convert to string
    assert isinstance(result, str)


def test_adapter_definition_with_output_schema():
    """Test tool definition with optional output schema."""
    definition = MCPToolDefinition(
        name="tool",
        description="Test tool",
        input_schema={"type": "object"},
        output_schema={"type": "string"}
    )
    adapter = MCPToolAdapter(definition, AsyncMock())

    assert adapter.definition.output_schema == {"type": "string"}


def test_adapter_namespace_in_tool_name():
    """Test that namespace is properly prefixed to tool name."""
    definition = MCPToolDefinition(
        name="fetch",
        description="Fetch tool",
        input_schema={}
    )
    adapter = MCPToolAdapter(definition, AsyncMock(), namespace="http")

    assert adapter.__name__ == "http:fetch"
    assert adapter.namespace == "http"
    assert adapter.definition.name == "fetch"  # Original name unchanged
