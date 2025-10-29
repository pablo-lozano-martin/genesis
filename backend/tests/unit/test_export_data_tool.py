import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import AIMessage
from app.langgraph.state import ConversationState
from app.langgraph.tools.export_data import export_data


@pytest.mark.asyncio
async def test_export_data_all_fields_success(tmp_path):
    """Test exporting complete state with all required fields."""
    # Mock the export directory to use tmp_path
    with patch('app.langgraph.tools.export_data.Path') as mock_path:
        mock_export_dir = tmp_path / "onboarding_data"
        mock_export_dir.mkdir()
        mock_path.return_value = mock_export_dir

        # Mock LLM provider
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = AIMessage(
            content="- Employee John Doe onboarded\n- Selected mouse starter kit\n- No dietary restrictions"
        )

        with patch('app.langgraph.tools.export_data.get_llm_provider', return_value=mock_provider):
            state = ConversationState(
                conversation_id="conv-123",
                user_id="user-456",
                employee_name="John Doe",
                employee_id="EMP-789",
                starter_kit="mouse",
                dietary_restrictions="Vegetarian",
                meeting_scheduled=True,
                messages=[]
            )

            result = await export_data(state)

            assert result["status"] == "success"
            assert "exported successfully" in result["message"]
            assert "file_path" in result
            assert "summary" in result
            assert state["conversation_summary"] is not None


@pytest.mark.asyncio
async def test_export_data_missing_required_fields():
    """Test export fails when required fields are missing."""
    state = ConversationState(
        conversation_id="conv-123",
        user_id="user-456",
        employee_name="John Doe",
        messages=[]
    )

    result = await export_data(state)

    assert result["status"] == "error"
    assert "missing required fields" in result["message"]
    assert "missing_fields" in result
    assert "employee_id" in result["missing_fields"]
    assert "starter_kit" in result["missing_fields"]


@pytest.mark.asyncio
async def test_export_data_file_creation(tmp_path):
    """Test JSON file is created with correct structure."""
    with patch('app.langgraph.tools.export_data.Path') as mock_path_class:
        # Configure mock to use tmp_path
        mock_export_dir = tmp_path / "onboarding_data"
        mock_export_dir.mkdir()

        def path_side_effect(arg):
            if arg == "/app/onboarding_data":
                return mock_export_dir
            return Path(arg)

        mock_path_class.side_effect = path_side_effect

        # Mock LLM provider
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = AIMessage(
            content="Test summary"
        )

        with patch('app.langgraph.tools.export_data.get_llm_provider', return_value=mock_provider):
            state = ConversationState(
                conversation_id="conv-456",
                user_id="user-789",
                employee_name="Jane Smith",
                employee_id="EMP-111",
                starter_kit="keyboard",
                dietary_restrictions=None,
                meeting_scheduled=False,
                messages=[]
            )

            result = await export_data(state)

            assert result["status"] == "success"

            # Verify file was created
            json_file = mock_export_dir / "conv-456.json"
            assert json_file.exists()

            # Verify JSON structure
            with open(json_file, "r") as f:
                data = json.load(f)

            assert data["conversation_id"] == "conv-456"
            assert data["user_id"] == "user-789"
            assert data["employee_name"] == "Jane Smith"
            assert data["employee_id"] == "EMP-111"
            assert data["starter_kit"] == "keyboard"
            assert data["dietary_restrictions"] is None
            assert data["meeting_scheduled"] is False
            assert "conversation_summary" in data
            assert "exported_at" in data


@pytest.mark.asyncio
async def test_export_data_summary_generation():
    """Test LLM summary is generated and included."""
    with patch('app.langgraph.tools.export_data.Path') as mock_path_class:
        mock_export_dir = MagicMock()
        mock_export_dir.mkdir = MagicMock()
        mock_export_dir.__truediv__ = lambda self, other: MagicMock(
            __enter__=MagicMock(return_value=MagicMock(write=MagicMock())),
            __exit__=MagicMock()
        )
        mock_path_class.return_value = mock_export_dir

        # Mock file operations
        mock_file = MagicMock()
        with patch('builtins.open', return_value=mock_file):
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock()

            # Mock LLM provider with specific summary
            mock_provider = AsyncMock()
            expected_summary = "- Employee onboarded successfully\n- Requested backpack starter kit"
            mock_provider.generate.return_value = AIMessage(content=expected_summary)

            with patch('app.langgraph.tools.export_data.get_llm_provider', return_value=mock_provider):
                state = ConversationState(
                    conversation_id="conv-789",
                    user_id="user-111",
                    employee_name="Bob Wilson",
                    employee_id="EMP-222",
                    starter_kit="backpack",
                    messages=[]
                )

                result = await export_data(state)

                assert result["status"] == "success"
                assert result["summary"] == expected_summary
                assert state["conversation_summary"] == expected_summary


@pytest.mark.asyncio
async def test_export_data_summary_generation_failure(tmp_path):
    """Test graceful fallback when LLM summary generation fails."""
    with patch('app.langgraph.tools.export_data.Path') as mock_path_class:
        mock_export_dir = tmp_path / "onboarding_data"
        mock_export_dir.mkdir()

        def path_side_effect(arg):
            if arg == "/app/onboarding_data":
                return mock_export_dir
            return Path(arg)

        mock_path_class.side_effect = path_side_effect

        # Mock LLM provider to raise exception
        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("LLM API error")

        with patch('app.langgraph.tools.export_data.get_llm_provider', return_value=mock_provider):
            state = ConversationState(
                conversation_id="conv-error",
                user_id="user-error",
                employee_name="Error Test",
                employee_id="EMP-ERR",
                starter_kit="mouse",
                messages=[]
            )

            result = await export_data(state)

            # Should still succeed with fallback summary
            assert result["status"] == "success"
            assert result["summary"] == "Summary generation unavailable"
            assert state["conversation_summary"] == "Summary generation unavailable"


@pytest.mark.asyncio
async def test_export_data_empty_optional_fields(tmp_path):
    """Test export works with only required fields."""
    with patch('app.langgraph.tools.export_data.Path') as mock_path_class:
        mock_export_dir = tmp_path / "onboarding_data"
        mock_export_dir.mkdir()

        def path_side_effect(arg):
            if arg == "/app/onboarding_data":
                return mock_export_dir
            return Path(arg)

        mock_path_class.side_effect = path_side_effect

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = AIMessage(content="Minimal onboarding")

        with patch('app.langgraph.tools.export_data.get_llm_provider', return_value=mock_provider):
            state = ConversationState(
                conversation_id="conv-minimal",
                user_id="user-minimal",
                employee_name="Minimal User",
                employee_id="EMP-MIN",
                starter_kit="keyboard",
                messages=[]
            )

            result = await export_data(state)

            assert result["status"] == "success"

            # Verify JSON has None for optional fields
            json_file = mock_export_dir / "conv-minimal.json"
            with open(json_file, "r") as f:
                data = json.load(f)

            assert data["dietary_restrictions"] is None
            assert data["meeting_scheduled"] is None
