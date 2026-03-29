# mvs_harness/prompt_builder/loaders/recent_events_loader.py
import json
from pathlib import Path
from typing import List

from mvs_harness.schemas.models import LogEntry

def load_recent_events(project_root: Path, limit: int = 20) -> List[LogEntry]:
    """
    Reads and parses the last N events from the project's event log.

    Args:
        project_root: The root directory of the project.
        limit: The maximum number of recent events to return.

    Returns:
        A list of LogEntry objects.
    """
    log_file = project_root / ".ddio/events.log"
    if not log_file.is_file():
        return []

    events: List[LogEntry] = []
    try:
        lines = log_file.read_text(encoding='utf-8', errors='replace').strip().splitlines()
        recent_lines = lines[-limit:]
        for line in recent_lines:
            try:
                event_data = json.loads(line)
                events.append(LogEntry.model_validate(event_data))
            except (json.JSONDecodeError, ValueError):
                # Skip malformed lines
                continue
    except IOError:
        # If there's an error reading the file, return what we have (which is nothing).
        return []
    
    return events
