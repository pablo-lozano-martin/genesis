# ABOUTME: Unit tests for math tools used in LLM tool calling
# ABOUTME: Tests multiply tool functionality and LangChain tool integration

import pytest
from app.langgraph.tools.math_tools import multiply


def test_multiply_positive_numbers():
    """Test multiplication of positive numbers."""
    result = multiply.invoke({"a": 5, "b": 3})
    assert result == 15


def test_multiply_with_zero():
    """Test multiplication with zero."""
    result = multiply.invoke({"a": 0, "b": 100})
    assert result == 0


def test_multiply_negative_numbers():
    """Test multiplication with negative numbers."""
    result = multiply.invoke({"a": -2, "b": 5})
    assert result == -10


def test_multiply_floats():
    """Test multiplication of float numbers."""
    result = multiply.invoke({"a": 2.5, "b": 4.0})
    assert result == 10.0


def test_multiply_tool_has_name():
    """Test that the tool has a proper name."""
    assert multiply.name == "multiply"


def test_multiply_tool_has_description():
    """Test that the tool has a description."""
    assert multiply.description is not None
    assert "multiply" in multiply.description.lower()
