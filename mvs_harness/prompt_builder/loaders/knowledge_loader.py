# mvs_harness/prompt_builder/loaders/knowledge_loader.py
from pathlib import Path

class CoreKnowledgeNotFoundError(Exception):
    """Custom exception for when the core knowledge spec is not found."""
    pass

def load_core_knowledge(project_root: Path) -> str:
    """
    Loads the agent's core knowledge from the pre-compiled Markdown artifact.

    This function looks for the build artifact at 'build/spec/agent_knowledge.md'.

    Args:
        project_root: The root directory of the project.

    Returns:
        A Markdown string containing the core knowledge, or an empty string if not found.
    """
    knowledge_artifact_path = project_root / "build" / "spec" / "agent_knowledge.md"

    if not knowledge_artifact_path.is_file():
        # It's not an error for this not to exist yet (e.g., before first build).
        # Return an empty string so the prompt builder can proceed.
        return ""

    try:
        # The compiled artifact already contains the necessary headers and formatting.
        return knowledge_artifact_path.read_text()
    except Exception as e:
        # In case of a file read error, return a formatted error message.
        error_message = (
            f"# ERROR: Could not load Core Knowledge Base\n---\n"
            f"Failed to read artifact at '{knowledge_artifact_path.relative_to(project_root)}'.\n"
            f"Error: {e}\n"
        )
        return error_message
