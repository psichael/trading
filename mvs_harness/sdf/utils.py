import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel

# Pattern to match the '[index]_[uuid]_[slug]' format.
# It now allows for an optional decimal part in the index (e.g., '0001.001').
SDF_PATH_PATTERN = re.compile(
    r"^(?P<index>\d+(\.\d+)?)_"
    r"(?P<uuid>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})_"
    r"(?P<slug>[a-zA-Z0-9_-]+)$"
)

# Lenient pattern for old SPF paths like 't001_some-slug' or 'e001_some-epic'
SPF_LEGACY_PATH_PATTERN = re.compile(r"^(?P<prefix>[a-zA-Z])(?P<index>\d+)_.*$")

class SdfPathInfo(BaseModel):
    """Structured representation of a parsed SDF path component."""
    index: float  # Use float to handle decimal indices for sorting
    uuid: str
    slug: str


def generate_uuid() -> str:
    """Generates a new, random UUID string."""
    return str(uuid.uuid4())


def slugify(text: str) -> str:
    """
    Converts a string into a filesystem-safe, URL-friendly slug.
    """
    s = text.lower().strip()
    s = re.sub(r'[\s.]+', '-', s)
    s = re.sub(r'[^a-z0-9_-]', '', s)
    return s


def parse_sdf_path(path: Path) -> Optional[SdfPathInfo]:
    """
    Parses an SDF file or directory name to extract its components.
    The name (without extension) must conform to the '[index]_[uuid]_[slug]' format.

    Args:
        path: A Path object representing the file or directory.

    Returns:
        An SdfPathInfo object if the name is valid, otherwise None.
    """
    name = path.name
    if name.endswith('.doc.yaml'):
        stem = name[:-len('.doc.yaml')]
    else:
        stem = name

    # First, try to match the strict SDF v3 pattern
    match = SDF_PATH_PATTERN.match(stem)
    if match:
        data = match.groupdict()
        return SdfPathInfo(
            index=float(data["index"]),
            uuid=data["uuid"],
            slug=data["slug"]
        )

    # If it fails, check for the legacy SPF plan pattern to avoid renumbering it
    legacy_match = SPF_LEGACY_PATH_PATTERN.match(stem)
    if legacy_match:
        return None # It's a known, non-SDFv3 format, so we ignore it.

    # If it's neither, it's not a parsable SDF path for renumbering purposes.
    return None


def renumber_sdf_paths(paths: List[Path]) -> List[Tuple[Path, Path]]:
    """
    Analyzes a list of SDF paths and generates a sequence of rename operations
    to resolve decimal indices into a clean, sequential integer series.

    For example, `[0001_..., 0001.001_..., 0002_...]` becomes
    `[0001_..., 0002_..., 0003_...]`.

    Args:
        paths: A list of Path objects to analyze.

    Returns:
        A list of tuples, where each tuple is `(old_path, new_path)`.
        Paths that do not require renumbering are not included.
    """
    parsable_items = []
    for path in paths:
        info = parse_sdf_path(path)
        if info:
            parsable_items.append((path, info))

    # Sort items based on their index (including decimals)
    parsable_items.sort(key=lambda item: item[1].index)

    rename_operations = []
    padding = 4  # Use a fixed padding for consistency with the spec.

    for i, (original_path, info) in enumerate(parsable_items):
        new_index_str = str(i).zfill(padding)

        # Reconstruct the base name (stem)
        new_stem = f"{new_index_str}_{info.uuid}_{info.slug}"

        suffix = ''
        if original_path.name.endswith('.doc.yaml'):
            suffix = '.doc.yaml'
        
        new_name = f"{new_stem}{suffix}"

        if original_path.name != new_name:
            new_path = original_path.with_name(new_name)
            rename_operations.append((original_path, new_path))

    return rename_operations
