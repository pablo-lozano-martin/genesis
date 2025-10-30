# ABOUTME: Tool for writing validated data to conversation state fields
# ABOUTME: Provides Pydantic-based type validation for onboarding data

from typing import Optional, Any, Annotated, Dict
from pydantic import BaseModel, Field, ValidationError, field_validator
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
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


@tool
def write_data(
    field_name: str,
    value: Any,
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    comments: Optional[str] = None
) -> Command:
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
        field_name: Name of the field to write (e.g., "employee_name")
        value: Value to write (will be validated)
        state: Current ConversationState (injected by LangGraph)
        comments: Optional agent-provided comments about the data

    Returns:
        Command object that updates the state with the validated value.
        Returns error message for validation failures.
    """
    try:
        logger.info(f"=== WRITE_DATA CALLED === field_name={field_name}, value={value}, tool_call_id={tool_call_id}")
        logger.info(f"State type: {type(state)}, State keys: {state.keys() if hasattr(state, 'keys') else 'N/A'}")

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
            error_msg = f"Error: Unknown field '{field_name}'. Valid fields: {', '.join(valid_fields)}"
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )

        # Validate value using Pydantic schema
        try:
            validation_data = {field_name: value}
            validated = OnboardingDataSchema(**validation_data)
            validated_value = getattr(validated, field_name)

        except ValidationError as e:
            logger.warning(f"Validation failed for {field_name}: {e}")

            error_msg = f"Validation error for {field_name}: {e.errors()[0]['msg']}"

            # Include valid options for constrained fields
            if field_name == "starter_kit":
                error_msg += ". Valid values: mouse, keyboard, backpack"
            elif field_name == "meeting_scheduled":
                error_msg += ". Valid values: true, false"

            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )

        # Update state with validated value
        logger.info(
            f"Data written to {field_name}: {validated_value}"
            f"{f' (comments: {comments})' if comments else ''}"
        )

        success_msg = f"Successfully recorded {field_name}: {validated_value}"
        logger.info(f"=== WRITE_DATA RETURNING Command with update: {field_name}={validated_value} ===")

        return Command(
            update={
                field_name: validated_value,
                "messages": [
                    ToolMessage(
                        content=success_msg,
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
    except Exception as e:
        logger.error(f"=== WRITE_DATA EXCEPTION === {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error in write_data: {str(e)}",
                        tool_call_id=tool_call_id
                    )
                ]
            }
        )
