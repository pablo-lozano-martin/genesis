from langchain_community.tools import DuckDuckGoSearchResults


def web_search(query: str) -> str:
    """
    Perform a web search using DuckDuckGo.

    Args:
        query: The search query string.

    Returns:
        The search results as a string.
    """
    search = DuckDuckGoSearchResults(output_format="json")

    return search.rinvokeun(query)