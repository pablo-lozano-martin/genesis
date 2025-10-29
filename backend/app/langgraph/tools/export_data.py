# ABOUTME: Tool for exporting collected onboarding data to JSON with LLM-generated summary.
# ABOUTME: Validates completeness, generates summary, saves to Docker volume, and updates state.

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from langchain_core.messages import HumanMessage
from app.langgraph.state import ConversationState
from app.adapters.outbound.llm_providers.provider_factory import get_llm_provider
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


async def export_data(
    state: ConversationState,
    confirmation_message: Optional[str] = None
) -> dict:
    """
    Export collected onboarding data and generate summary.

    This tool performs the final export of onboarding data after all required
    fields have been collected. It generates an LLM-powered summary, saves it
    to the state, and exports all data to a JSON file in the Docker volume.

    Steps:
    1. Collect all onboarding fields from state
    2. Validate that required fields are present
    3. Call LLM to generate markdown summary with bullet points
    4. Save summary to state.conversation_summary (auto-persists to MongoDB)
    5. Save JSON file to /app/onboarding_data/<conversation_id>.json
    6. Return success message to agent

    Args:
        state: Current ConversationState with collected onboarding fields
        confirmation_message: Optional message from agent confirming export intent

    Returns:
        Dictionary with status, message, file_path, and summary.
        Success case returns status='success' with exported file path.
        Error case returns status='error' with missing fields list.
    """

    # Step 1: Collect required fields
    conversation_id = state.get("conversation_id")
    user_id = state.get("user_id")

    required_fields = {
        "employee_name": state.get("employee_name"),
        "employee_id": state.get("employee_id"),
        "starter_kit": state.get("starter_kit")
    }

    optional_fields = {
        "dietary_restrictions": state.get("dietary_restrictions"),
        "meeting_scheduled": state.get("meeting_scheduled")
    }

    # Check completeness of required fields
    missing_required = [k for k, v in required_fields.items() if v is None]
    if missing_required:
        logger.warning(
            f"Export attempted with missing required fields: {missing_required}"
        )
        return {
            "status": "error",
            "message": f"Cannot export: missing required fields",
            "missing_fields": missing_required,
            "required_fields": list(required_fields.keys())
        }

    # Step 2: Generate LLM-powered summary
    llm_provider = get_llm_provider()

    summary_prompt = f"""Summarize this onboarding conversation in 2-3 concise bullet points.

Employee Information:
- Name: {required_fields['employee_name']}
- ID: {required_fields['employee_id']}
- Starter Kit: {required_fields['starter_kit']}
- Dietary: {optional_fields['dietary_restrictions'] or 'Not specified'}
- Meeting: {optional_fields['meeting_scheduled'] or 'Not scheduled'}

Focus on key highlights and any notable requests or concerns."""

    summary_messages = [HumanMessage(content=summary_prompt)]

    try:
        summary_response = await llm_provider.generate(summary_messages)
        summary_text = summary_response.content
        logger.info("Successfully generated onboarding summary")
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        summary_text = "Summary generation unavailable"

    # Step 3: Update state with summary (auto-persists via checkpointer)
    state["conversation_summary"] = summary_text

    # Step 4: Export to JSON file (Docker volume)
    export_dir = Path("/app/onboarding_data")
    export_dir.mkdir(exist_ok=True)

    filename = f"{conversation_id}.json"
    filepath = export_dir / filename

    export_data_dict = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "employee_name": required_fields["employee_name"],
        "employee_id": required_fields["employee_id"],
        "starter_kit": required_fields["starter_kit"],
        "dietary_restrictions": optional_fields["dietary_restrictions"],
        "meeting_scheduled": optional_fields["meeting_scheduled"],
        "conversation_summary": summary_text,
        "exported_at": datetime.utcnow().isoformat()
    }

    try:
        with open(filepath, "w") as f:
            json.dump(export_data_dict, f, indent=2)
        logger.info(f"Exported onboarding data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to write export file: {e}")
        return {
            "status": "error",
            "message": f"Failed to write export file: {str(e)}",
            "file_path": str(filepath)
        }

    return {
        "status": "success",
        "message": "Onboarding data exported successfully",
        "file_path": str(filepath),
        "summary": summary_text
    }
