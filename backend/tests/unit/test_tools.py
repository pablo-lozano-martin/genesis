"""Unit tests for tool functions."""
import pytest
from app.langgraph.tools.add import add
from app.langgraph.tools.multiply import multiply


class TestAddTool:
    """Tests for add tool."""

    def test_add_positive_numbers(self):
        """Test adding two positive integers."""
        result = add(5, 3)
        assert result == 8

    def test_add_negative_numbers(self):
        """Test adding two negative integers."""
        result = add(-5, -3)
        assert result == -8

    def test_add_mixed_signs(self):
        """Test adding positive and negative."""
        result = add(10, -3)
        assert result == 7

    def test_add_with_zero(self):
        """Test adding with zero."""
        result = add(0, 5)
        assert result == 5


class TestMultiplyTool:
    """Tests for multiply tool."""

    def test_multiply_positive_numbers(self):
        """Test multiplying two positive integers."""
        result = multiply(6, 7)
        assert result == 42

    def test_multiply_with_zero(self):
        """Test multiplying with zero."""
        result = multiply(5, 0)
        assert result == 0

    def test_multiply_negative_numbers(self):
        """Test multiplying two negative integers."""
        result = multiply(-3, -4)
        assert result == 12

    def test_multiply_mixed_signs(self):
        """Test multiplying positive and negative."""
        result = multiply(-5, 3)
        assert result == -15
