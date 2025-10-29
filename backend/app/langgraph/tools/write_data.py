# ABOUTME: Tool for writing validated data to conversation state fields
# ABOUTME: Provides Pydantic-based type validation for onboarding data

from typing import Optional, Any
from pydantic import BaseModel, Field, ValidationError, field_validator
from app.langgraph.state import ConversationState
from app.infrastructure.config.logging_config import get_logger

logger = get_logger(__name__)


class OnboardingDataSchema(BaseModel):
    """Schema for validating onboarding field values."""

    employee_name: Optional[str] = Field(None, min_length=1, max_length=255)
    employee_id: Optional[str] = Field(None, min_length=1, max_length=50)
    starter_kit: Optional[str] = None
    dietary_restrictions: Optional[str] = Field(None, max_length=500)
    meeting_scheduled: Optional[bool] = None
    conversation_summary: Optional[str] = None

    @field_validator("starter_kit")
    @classmethod
    def validate_starter_kit(cls, v):
        """Validate starter_kit is one of allowed options."""
        if v is not None:
            valid_options = ["mouse", "keyboard", "backpack"]
            if v.lower() not in valid_options:
                raise ValueError(
                    f"Invalid starter_kit value '{v}'. "
                    f"Must be one of: {', '.join(valid_options)}"
                )
            return v.lower()
        return v

    @field_validator("meeting_scheduled")
    @classmethod
    def validate_meeting_scheduled(cls, v):
        """Validate meeting_scheduled is boolean."""
        if v is not None and not isinstance(v, bool):
            raise ValueError(
                f"Invalid meeting_scheduled value '{v}'. "
                f"Must be true or false."
            )
        return v


async def write_data(
    state: ConversationState,
    field_name: str,
    value: Any,
    comments: Optional[str] = None
) -> dict:
    """
    Write validated data to a conversation state field.

    This tool allows the agent to record collected onboarding information
    to the conversation state. All data is validated before writing.

    Validation Rules:
    - employee_name: String, 1-255 characters
    - employee_id: String, 1-50 characters
    - starter_kit: One of ["mouse", "keyboard", "backpack"] (case-insensitive)
    - dietary_restrictions: String, up to 500 characters
    - meeting_scheduled: Boolean (true/false)
    - conversation_summary: String (no length limit)

    Args:
        state: Current ConversationState (passed by LangGraph)
        field_name: Name of the field to write (e.g., "employee_name")
        value: Value to write (will be validated)
        comments: Optional agent-provided comments about the data

    Returns:
        Dictionary with write result. Success case returns field_name, value,
        status='success', and message='Data recorded'. Validation errors return
        status='error' with message and valid_values for constrained fields.
        Invalid field names return status='error' with valid_fields list.
    """
    # Validate field_name exists in ConversationState
    valid_fields = [
        "employee_name",
        "employee_id",
        "starter_kit",
        "dietary_restrictions",
        "meeting_scheduled",
        "conversation_summary"
    ]

    if field_name not in valid_fields:
        logger.warning(f"Attempted to write to invalid field: {field_name}")
        return {
            "field_name": field_name,
            "status": "error",
            "message": f"Unknown field '{field_name}'",
            "valid_fields": valid_fields
        }

    # Validate value using Pydantic schema
    try:
        validation_data = {field_name: value}
        validated = OnboardingDataSchema(**validation_data)
        validated_value = getattr(validated, field_name)

    except ValidationError as e:
        logger.warning(f"Validation failed for {field_name}: {e}")

        error_details = {
            "field_name": field_name,
            "value": value,
            "status": "error",
            "message": str(e.errors()[0]["msg"])
        }

        # Include valid options for constrained fields
        if field_name == "starter_kit":
            error_details["valid_values"] = ["mouse", "keyboard", "backpack"]
        elif field_name == "meeting_scheduled":
            error_details["valid_values"] = [True, False]

        return error_details

    # Write validated value to state
    state[field_name] = validated_value

    logger.info(
        f"Data written to {field_name}: {validated_value}"
        f"{f' (comments: {comments})' if comments else ''}"
    )

    return {
        "field_name": field_name,
        "value": validated_value,
        "status": "success",
        "message": "Data recorded"
    }
