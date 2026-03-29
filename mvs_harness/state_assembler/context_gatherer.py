from pathlib import Path
from typing import List

from mvs_harness.schemas.models import ContextFile

def gather_context_files(paths: List[str], project_root: Path) -> List[ContextFile]:
    """Gathers and reads all specified context files, expanding directories."""
    context_files: List[ContextFile] = []
    gathered_paths = set()

    for path_str in paths:
        full_path = project_root / path_str
        if not full_path.exists():
            print(f"[WARNING] Context path does not exist, skipping: {path_str}")
            continue

        if full_path.is_file():
            if path_str not in gathered_paths:
                try:
                    content = full_path.read_text(encoding='utf-8')
                    context_files.append(ContextFile(path=path_str, content=content))
                    gathered_paths.add(path_str)
                except (IOError, UnicodeDecodeError) as e:
                    print(f"[WARNING] Could not read file {path_str}: {e}")

        elif full_path.is_dir():
            for sub_path in sorted(full_path.rglob("*")):
                if "__pycache__" in sub_path.parts or sub_path.name.endswith('.pyc'):
                    continue
                if sub_path.is_file():
                    rel_path_str = str(sub_path.relative_to(project_root)).replace("\\", "/")
                    if rel_path_str not in gathered_paths:
                        try:
                            content = sub_path.read_text(encoding='utf-8')
                            context_files.append(ContextFile(path=rel_path_str, content=content))
                            gathered_paths.add(rel_path_str)
                        except (IOError, UnicodeDecodeError) as e:
                            print(f"[WARNING] Could not read file {rel_path_str}: {e}")
    return context_files
