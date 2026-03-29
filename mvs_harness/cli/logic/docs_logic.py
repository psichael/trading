import os
from pathlib import Path
from typing import Optional, List, Tuple, NamedTuple

from mvs_harness.sdf.io import read_sdf_from_fs
from mvs_harness.sdf.assembler import assemble_sdf_to_markdown
from mvs_harness.sdf.diff import compare_sdf_trees, format_diffs, SdfDiff
from mvs_harness.sdf.md_converter import convert_markdown_to_sdf

class ValidationResult(NamedTuple):
    is_valid: bool
    path: Path
    error: Optional[Exception] = None

def convert_markdown_to_sdf_structure(input_file: Path, output_dir: Path) -> int:
    """
    Converts a Markdown file into an SDF v3 directory structure.
    Raises:
        ValueError: If the output directory is not empty.
    Returns:
        The number of files created.
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    elif any(output_dir.iterdir()):
        raise ValueError(f"Output directory '{output_dir}' is not empty.")

    markdown_content = input_file.read_text()
    root_title = input_file.stem.replace('_', ' ').replace('-', ' ').title()
    sdf_files = convert_markdown_to_sdf(markdown_content, root_title)

    file_count = 0
    for file_path_str, file_content in sdf_files.items():
        full_path = output_dir / file_path_str
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(file_content)
        file_count += 1
    
    return file_count

def validate_sdf_directory(source_dir: Path) -> List[ValidationResult]:
    """
    Recursively validates all SDF topics found within the given directory.
    Returns:
        A list of ValidationResult objects.
    """
    results: List[ValidationResult] = []
    
    manifest_paths = sorted(source_dir.rglob("_topic.manifest.yaml"))
    if not manifest_paths:
         # Special case: no topics found. Let CLI handle the message.
        return []

    for manifest_path in manifest_paths:
        topic_dir = manifest_path.parent
        try:
            _ = read_sdf_from_fs(topic_dir)
            results.append(ValidationResult(is_valid=True, path=topic_dir))
        except (FileNotFoundError, ValueError) as e:
            results.append(ValidationResult(is_valid=False, path=topic_dir, error=e))
        except Exception as e:
            # Catch unexpected errors to prevent crash
            results.append(ValidationResult(is_valid=False, path=topic_dir, error=e))
            
    return results

def diff_sdf_directories(before_dir: Path, after_dir: Path) -> str:
    """
    Compares two SDF directories and returns a formatted string of the semantic diff.
    """
    before_tree = read_sdf_from_fs(before_dir)
    after_tree = read_sdf_from_fs(after_dir)
    diffs = compare_sdf_trees(before_tree, after_tree)
    return format_diffs(diffs)

def compile_sdf_directory(source_dir: Path) -> str:
    """
    Compiles an SDF directory into a single Markdown string.
    """
    sdf_tree = read_sdf_from_fs(source_dir)
    return assemble_sdf_to_markdown(sdf_tree)
