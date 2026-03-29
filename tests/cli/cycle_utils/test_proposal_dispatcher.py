from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
import typer

from mvs_harness.cli.cycle_utils import proposal_dispatcher
from mvs_harness.schemas.models import Proposal, SpfProposal, Command

@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher._create_schema_validator')
def test_prepare_standard_proposal(mock_create_validator: MagicMock):
    """Verify that a standard proposal with commands is passed through correctly."""
    # Arrange
    mock_create_validator.return_value = MagicMock()
    standard_proposal_data = {
        "plan_analysis": "Standard analysis",
        "summary": "Standard summary",
        "event_type": "fix",
        "commands": [
            {"command": "create_file", "path": "/test.txt"}
        ]
    }
    project_root = Path("/fake/project")

    # Act
    result_proposal = proposal_dispatcher.prepare_proposal_for_execution(
        standard_proposal_data, project_root
    )

    # Assert
    assert isinstance(result_proposal, Proposal)
    assert result_proposal.summary == "Standard summary"
    assert len(result_proposal.commands) == 1
    assert result_proposal.commands[0].command == "create_file"
    assert result_proposal.commands[0].path == "/test.txt"
    mock_create_validator.assert_called_once_with(project_root)
    mock_create_validator.return_value.validate.assert_called_once_with(standard_proposal_data)


@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher.SpfCompiler')
@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher._create_schema_validator')
def test_prepare_logical_proposal_invokes_compiler(mock_create_validator: MagicMock, MockSpfCompiler: MagicMock):
    """Verify that a logical proposal correctly invokes the SpfCompiler."""
    # Arrange
    mock_create_validator.return_value = MagicMock()
    mock_compiler_instance = MockSpfCompiler.return_value
    mock_commands = [Command(command="create_file", path="plan/new_epic/_topic.manifest.yaml")]
    mock_compiler_instance.compile_and_validate.return_value = mock_commands

    # A minimal but valid logical proposal using the new schema structure
    logical_proposal_data = {
        "plan_analysis": "Logical analysis",
        "summary": "Logical summary",
        "event_type": "feat",
        "spf_plan_update": {
            "create": {
                "epics": [{
                    "temp_id": "e1",
                    "title": "New Epic",
                    "insert_after_epic_id": "start",
                    "component_ids": ["c1"],
                    "abstract": "An abstract."
                }]
            }
        }
    }
    project_root = Path("/fake/project")

    # Act
    result_proposal = proposal_dispatcher.prepare_proposal_for_execution(
        logical_proposal_data, project_root
    )

    # Assert
    # 0. Validator was called
    mock_create_validator.assert_called_once_with(project_root)
    mock_create_validator.return_value.validate.assert_called_once_with(logical_proposal_data)

    # 1. Compiler was initialized correctly
    MockSpfCompiler.assert_called_once_with(project_root / 'plan')

    # 2. Compilation method was called with the correct data
    mock_compiler_instance.compile_and_validate.assert_called_once()
    arg_passed = mock_compiler_instance.compile_and_validate.call_args[0][0]
    assert isinstance(arg_passed, SpfProposal)
    assert arg_passed.create.epics[0].title == "New Epic"

    # 3. The result is a standard Proposal with the commands from the compiler
    assert isinstance(result_proposal, Proposal)
    assert result_proposal.summary == "Logical summary"
    assert result_proposal.commands == mock_commands
    assert result_proposal.spf_plan_update is None

@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher.pyperclip')
@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher._create_schema_validator')
def test_prepare_proposal_with_context_request_success(mock_create_validator: MagicMock, mock_pyperclip: MagicMock, tmp_path: Path):
    """Verify a proposal with a context_request copies file contents to the clipboard and exits."""
    # Arrange
    mock_create_validator.return_value = MagicMock()
    project_root = tmp_path
    (project_root / "file1.txt").write_text("Content of file 1")
    (project_root / "src").mkdir()
    (project_root / "src/main.py").write_text("print('hello')")

    proposal_data = {
        "plan_analysis": "Requesting context",
        "summary": "Requesting context",
        "event_type": "chore",
        "context_request": {
            "response_type": "context_request",
            "requested_files": ["file1.txt", "src/main.py"]
        }
    }

    # Act & Assert
    with pytest.raises(typer.Exit) as e:
        proposal_dispatcher.prepare_proposal_for_execution(proposal_data, project_root)
    
    # Assert Exit was called correctly
    assert e.value.exit_code == 0

    # Assert pyperclip.copy was called once
    mock_pyperclip.copy.assert_called_once()
    copied_content = mock_pyperclip.copy.call_args[0][0]

    # Assert content is correct
    assert "File: file1.txt" in copied_content
    assert "Content of file 1" in copied_content
    assert "File: src/main.py" in copied_content
    assert "print('hello')" in copied_content

@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher.pyperclip')
@patch('mvs_harness.cli.cycle_utils.proposal_dispatcher._create_schema_validator')
def test_prepare_proposal_with_context_request_mixed_files(mock_create_validator: MagicMock, mock_pyperclip: MagicMock, tmp_path: Path):
    """Verify a context_request handles both existing and missing files gracefully."""
    # Arrange
    mock_create_validator.return_value = MagicMock()
    project_root = tmp_path
    (project_root / "existing.txt").write_text("I exist.")

    proposal_data = {
        "plan_analysis": "Requesting context",
        "summary": "Requesting context",
        "event_type": "chore",
        "context_request": {
            "response_type": "context_request",
            "requested_files": ["existing.txt", "missing.txt"]
        }
    }

    # Act & Assert
    with pytest.raises(typer.Exit) as e:
        proposal_dispatcher.prepare_proposal_for_execution(proposal_data, project_root)
    
    # Assert Exit was called correctly
    assert e.value.exit_code == 0

    # Assert pyperclip.copy was called once
    mock_pyperclip.copy.assert_called_once()
    copied_content = mock_pyperclip.copy.call_args[0][0]

    # Assert content is correct
    assert "File: existing.txt" in copied_content
    assert "I exist." in copied_content
    assert "File: missing.txt" in copied_content
    assert "### ERROR: File not found at 'missing.txt' ###" in copied_content
