# ABOUTME: Tool for querying collected onboarding data from conversation state
# ABOUTME: Allows agent to check what fields have been collected during conversation

from typing import Optional, List, Dict, Any
from app.langgraph.state import ConversationState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def read_data(
    state: ConversationState,
    field_names: Optional[List[str]] = None
) -> Dict[str, Any]:
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
        state: Current ConversationState (passed by LangGraph)
        field_names: Optional list of specific field names to query.
                    If None, returns all onboarding fields.
                    E.g., ["employee_name", "employee_id"]

    Returns:
        Dictionary with field names and current values:
        {
            "employee_name": "John Doe" or None,
            "employee_id": "EMP-123" or None,
            "starter_kit": "mouse" or None,
            "dietary_restrictions": "vegetarian" or None,
            "meeting_scheduled": true or None,
            "conversation_summary": "..." or None,
            "status": "success"
        }
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
        return {
            "status": "error",
            "message": f"Invalid field names: {invalid_fields}",
            "valid_fields": all_onboarding_fields
        }

    # Extract field values from state
    result = {}
    for field in fields_to_query:
        result[field] = state.get(field)

    result["status"] = "success"
    logger.info(f"Read {len(fields_to_query)} fields from state")

    return result
