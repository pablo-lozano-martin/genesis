# ABOUTME: Math tools for LLM tool calling, including multiplication
# ABOUTME: Uses LangChain's @tool decorator for function-to-tool conversion

from langchain_core.tools import tool


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together.

    Use this when you need to calculate the product of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The product of a and b
    """
    return a * b
