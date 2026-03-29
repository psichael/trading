from pathlib import Path
import json

import pytest
from mvs_harness.last.models import ModuleNode, FunctionDefNode, PassNode
from mvs_harness.last.io import write_last_to_fs, read_last_from_fs

@pytest.fixture
def sample_last_tree() -> ModuleNode:
    """Provides a sample in-memory LAST structure for testing."""
    return ModuleNode(
        body=[
            FunctionDefNode(
                name="my_function",
                args=["arg1", "arg2"],
                body=[
                    PassNode()
                ]
            )
        ]
    )

def test_write_last_to_fs(sample_last_tree: ModuleNode, tmp_path: Path):
    """Tests that the LAST structure is written to the filesystem correctly."""
    write_last_to_fs(sample_last_tree, tmp_path)

    # Check root module
    assert (tmp_path / "meta.json").is_file()
    with (tmp_path / "meta.json").open() as f:
        meta = json.load(f)
        assert meta == {"node_type": "module"} # Body is not in meta

    # Check function definition directory
    func_dir = tmp_path / "000_my_function"
    assert func_dir.is_dir()

    # Check function meta
    with (func_dir / "meta.json").open() as f:
        func_meta = json.load(f)
        assert func_meta == {
            "node_type": "function_def",
            "name": "my_function",
            "args": ["arg1", "arg2"],
        }

    # Check pass node directory
    pass_dir = func_dir / "000_pass"
    assert pass_dir.is_dir()

    # Check pass meta
    with (pass_dir / "meta.json").open() as f:
        pass_meta = json.load(f)
        assert pass_meta == {"node_type": "pass"}

def test_round_trip_preserves_data(sample_last_tree: ModuleNode, tmp_path: Path):
    """An explicit round-trip test (write then read) to ensure no data loss."""
    # 1. Write to disk
    write_last_to_fs(sample_last_tree, tmp_path)

    # 2. Read from disk
    read_tree = read_last_from_fs(tmp_path)

    # 3. Assert equality
    assert read_tree == sample_last_tree
    assert sample_last_tree.model_dump() == read_tree.model_dump()

def test_read_fails_on_missing_meta(tmp_path: Path):
    """Tests that reading fails if a meta.json is missing."""
    # A directory without meta.json should cause an error
    with pytest.raises(FileNotFoundError):
        read_last_from_fs(tmp_path)

def test_read_fails_on_invalid_meta(tmp_path: Path):
    """Tests that reading fails if meta.json has an unknown node_type."""
    invalid_meta = {"node_type": "unknown_node", "name": "test"}
    with (tmp_path / "meta.json").open("w") as f:
        json.dump(invalid_meta, f)

    with pytest.raises(ValueError, match="Invalid or missing node_type"):
        read_last_from_fs(tmp_path)
