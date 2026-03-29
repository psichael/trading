import re
import yaml
from pathlib import Path
from typing import List
from .models import SdfTopicNode, TopicManifest, Doc
from pydantic import ValidationError
import shutil

# This mapping helps associate a doc's ID with its filename
DOC_FILENAME_PATTERN = re.compile(r"^(\d{4})_([a-zA-Z0-9-]+)\.doc\.yaml$")
TOPIC_DIR_PATTERN = re.compile(r"^(\d{4})_(.+)$")

def _sanitize_for_filename(text: str) -> str:
    """Sanitizes a string to be used as a valid directory or file name stem."""
    s = text.lower().replace(' ', '-')
    s = re.sub(r'[^a-z0-9-]', '', s)
    return s[:50]

def _get_id_from_path(path: Path) -> str:
    """Extracts the ID part from a prefixed filename or directory name."""
    match = DOC_FILENAME_PATTERN.match(path.name)
    if match:
        return match.group(2)
    
    dir_match = TOPIC_DIR_PATTERN.match(path.name)
    if dir_match:
        # For directories, the title is used, not an id.
        # This is a simplification. The spec is more complex.
        # Let's assume for now the sanitized title acts as an id for pathing.
        return dir_match.group(2)
    return ""

def write_sdf_to_fs(node: SdfTopicNode, root_path: Path):
    """
    Recursively writes an SdfTopicNode structure to the filesystem.
    This is a destructive operation; it will clear the directory first.
    """
    if root_path.exists():
        shutil.rmtree(root_path)
    root_path.mkdir(exist_ok=True, parents=True)

    # Write the manifest for the current topic node.
    manifest_file = root_path / "_topic.manifest.yaml"
    with manifest_file.open("w") as f:
        yaml.dump(node.manifest.model_dump(), f, indent=2, default_flow_style=False)

    # Write the documents (.doc.yaml files).
    for i, doc in enumerate(node.docs):
        # Using doc.id for the filename is more stable than a title.
        doc_filename = f"{i:04d}_{doc.id}.doc.yaml"
        doc_path = root_path / doc_filename
        with doc_path.open("w") as f:
            yaml.dump(doc.model_dump(), f, indent=2, default_flow_style=False)

    # Recursively write sub-topics.
    for i, sub_topic in enumerate(node.sub_topics):
        sanitized_title = _sanitize_for_filename(sub_topic.title)
        child_dir_name = f"{i:04d}_{sanitized_title}"
        child_path = root_path / child_dir_name
        write_sdf_to_fs(sub_topic, child_path)


def read_sdf_from_fs(root_path: Path) -> SdfTopicNode:
    """
    Recursively reads an SDF structure from the filesystem into SdfTopicNode models.
    """
    manifest_file = root_path / "_topic.manifest.yaml"
    if not manifest_file.is_file():
        raise FileNotFoundError(f"_topic.manifest.yaml not found in {root_path}")

    with manifest_file.open("r", encoding='utf-8') as f:
        manifest_data = yaml.safe_load(f)
        manifest = TopicManifest(**manifest_data)

    docs: List[Doc] = []
    sub_topics: List[SdfTopicNode] = []

    # Discover and sort children to maintain order.
    # We sort them by their full name, which includes the numeric prefix.
    children = sorted(list(root_path.iterdir()))

    for child_path in children:
        if child_path.is_dir():
            try:
                sub_topics.append(read_sdf_from_fs(child_path))
            except FileNotFoundError:
                # Ignore directories that are not valid SDF topics (e.g., .git)
                continue
        elif child_path.name.endswith('.doc.yaml'):
            with child_path.open("r", encoding='utf-8') as f:
                doc_data = yaml.safe_load(f)
                try:
                    docs.append(Doc(**doc_data))
                except ValidationError as e:
                    raise ValueError(f"Schema validation failed for {child_path}: {e}") from e
    
    return SdfTopicNode(
        manifest=manifest,
        docs=docs,
        sub_topics=sub_topics
    )
