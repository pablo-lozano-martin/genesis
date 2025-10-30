# ABOUTME: Tool for querying collected onboarding data from conversation state
# ABOUTME: Allows agent to check what fields have been collected during conversation

from typing import Optional, List, Dict, Any, Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


@tool
def read_data(
    state: Annotated[Dict[str, Any], InjectedState],
    field_names: Optional[List[str]] = None
) -> str:
    """
    Query collected fields from current conversation state.

    This tool allows the agent to check what onboarding information has been
    collected so far. The agent can query specific fields or all fields.

    Onboarding fields available:
    - employee_name: Employee's full name
    - employee_id: Employee ID number
    - starter_kit: Starter kit choice (mouse/keyboard/backpack)
    - dietary_restrictions: Dietary preferences
    - meeting_scheduled: Whether onboarding meeting is scheduled
    - conversation_summary: Summary of conversation

    Args:
        state: Current ConversationState (injected by LangGraph)
        field_names: Optional list of specific field names to query.
                    If None, returns all onboarding fields.
                    E.g., ["employee_name", "employee_id"]

    Returns:
        Formatted string with field names and current values for the LLM.
    """
    # Define all available onboarding fields
    all_onboarding_fields = [
        "employee_name",
        "employee_id",
        "starter_kit",
        "dietary_restrictions",
        "meeting_scheduled",
        "conversation_summary"
    ]

    # Determine which fields to query
    fields_to_query = field_names if field_names else all_onboarding_fields

    # Validate requested fields exist
    invalid_fields = [f for f in fields_to_query if f not in all_onboarding_fields]
    if invalid_fields:
        logger.warning(f"Attempted to read invalid fields: {invalid_fields}")
        return f"Error: Invalid field names: {invalid_fields}. Valid fields: {', '.join(all_onboarding_fields)}"

    # Extract field values from state and format as string
    result_lines = ["Current onboarding data:"]

    for field in fields_to_query:
        value = state.get(field)
        if value is not None:
            result_lines.append(f"- {field}: {value}")
        else:
            result_lines.append(f"- {field}: (not collected yet)")

    logger.info(f"Read {len(fields_to_query)} fields from state")

    return "\n".join(result_lines)
