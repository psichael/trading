from pydantic import BaseModel
from typing import Optional

# Represents a single log entry from the events.log file.
class LogEntry(BaseModel):
    timestamp: str
    event_type: str
    summary: str
    task_file: Optional[str] = None

# Represents a single file's content provided as context to the agent.
class ContextFile(BaseModel):
    path: str
    content: str
