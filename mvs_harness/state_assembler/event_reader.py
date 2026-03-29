import json
from pathlib import Path
from typing import List, Dict

def get_recent_events(project_root: Path, limit: int = 20) -> List[Dict]:
    event_log_path = project_root / ".ddio/events.log"
    if not event_log_path.exists():
        return []
    
    lines = event_log_path.read_text().strip().splitlines()
    recent_lines = lines[-limit:]
    events = []
    for line in recent_lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
