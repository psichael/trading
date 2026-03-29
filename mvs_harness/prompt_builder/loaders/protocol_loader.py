from pathlib import Path

class ProtocolNotFoundError(FileNotFoundError):
    """Raised when the compiled protocol file cannot be found."""
    pass

def load_operational_protocol(project_root: Path, protocol_name: str) -> str:
    """
    Loads a compiled agent protocol content from the build directory by name.

    Args:
        project_root: The root directory of the project.
        protocol_name: The name of the protocol (e.g., 'agent_protocol', 'planner_protocol').

    Returns:
        The content of the agent protocol file as a string.

    Raises:
        ProtocolNotFoundError: If the protocol file does not exist.
        IOError: If there is an error reading the file.
    """
    protocol_path = project_root / "build" / "spec" / f"{protocol_name}.md"
    
    if not protocol_path.is_file():
        error_message = (
            f"FATAL: Compiled protocol '{protocol_name}' not found at '{protocol_path}'. "
            f"Hint: Ensure the 'spec/{protocol_name}' topic exists and has been compiled."
        )
        raise ProtocolNotFoundError(error_message)
        
    try:
        return protocol_path.read_text(encoding='utf-8', errors='replace')
    except IOError as e:
        # Re-raise with more context
        raise IOError(f"Error reading protocol file {protocol_path}: {e}") from e
