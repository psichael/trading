from pathlib import Path
import yaml
import shutil

import pytest
from mvs_harness.sdf.models import SdfTopicNode, TopicManifest, Doc
from mvs_harness.sdf.io import write_sdf_to_fs, read_sdf_from_fs

@pytest.fixture
def sample_sdf_tree() -> SdfTopicNode:
    """Provides a sample in-memory SDF structure for testing."""
    return SdfTopicNode(
        manifest=TopicManifest(
            id="root-doc",
            title="Root Document",
            status="finalized",
            abstract="This is the main abstract.",
        ),
        docs=[
            Doc(id="intro-para", content="This is the intro paragraph.")
        ],
        sub_topics=[
            SdfTopicNode(
                manifest=TopicManifest(
                    id="section-1",
                    title="Section 1",
                    status="finalized",
                    abstract="Content for the first section.",
                ),
                docs=[
                    Doc(id="s1-para1", content="Details for 1.1"),
                    Doc(id="s1-para2", content="More details for 1.1"),
                ]
            ),
            SdfTopicNode(
                manifest=TopicManifest(
                    id="section-2",
                    title="Section 2",
                    status="draft",
                    abstract="Content for the second section.",
                )
            ),
        ],
    )

def test_write_sdf_to_fs(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that the SDF structure is written to the filesystem correctly."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    # Check root topic
    root_manifest = tmp_path / "_topic.manifest.yaml"
    assert root_manifest.is_file()
    with root_manifest.open() as f:
        meta = yaml.safe_load(f)
        assert meta["id"] == "root-doc"
        assert meta["title"] == "Root Document"

    root_doc = tmp_path / "0000_intro-para.doc.yaml"
    assert root_doc.is_file()
    with root_doc.open() as f:
        doc_meta = yaml.safe_load(f)
        assert doc_meta["id"] == "intro-para"

    # Check section 1
    section1_dir = tmp_path / "0000_section-1"
    assert section1_dir.is_dir()
    with (section1_dir / "_topic.manifest.yaml").open() as f:
        sec1_meta = yaml.safe_load(f)
        assert sec1_meta["id"] == "section-1"
    assert (section1_dir / "0000_s1-para1.doc.yaml").is_file()
    assert (section1_dir / "0001_s1-para2.doc.yaml").is_file()

    # Check section 2
    section2_dir = tmp_path / "0001_section-2"
    assert section2_dir.is_dir()

def test_round_trip_preserves_data(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """An explicit round-trip test (write then read) to ensure no data loss."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)
    read_tree = read_sdf_from_fs(tmp_path)
    assert read_tree == sample_sdf_tree
    assert sample_sdf_tree.model_dump() == read_tree.model_dump()

def test_read_fails_on_missing_manifest(tmp_path: Path):
    """Tests that reading fails if a _topic.manifest.yaml is missing."""
    with pytest.raises(FileNotFoundError):
        read_sdf_from_fs(tmp_path)

def test_read_fails_on_invalid_doc_yaml(tmp_path: Path):
    """Tests that reading fails if a .doc.yaml has invalid data."""
    # Create a valid manifest
    with (tmp_path / "_topic.manifest.yaml").open("w") as f:
        yaml.dump({"id": "test", "title": "Test", "status": "draft"}, f)

    # Missing 'id' which is a required field
    invalid_doc = {"content": "some content"}
    with (tmp_path / "0000_bad-doc.doc.yaml").open("w") as f:
        yaml.dump(invalid_doc, f)

    with pytest.raises(ValueError, match="Schema validation failed"):
        read_sdf_from_fs(tmp_path)

# --- NEW TESTS FOR UPDATE LOGIC ---

def test_update_doc_content(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that modifying a doc's content is persisted."""
    # 1. Initial write
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    # 2. Read, modify, and write back
    tree_to_modify = read_sdf_from_fs(tmp_path)
    tree_to_modify.sub_topics[0].docs[0].content = "UPDATED CONTENT"
    write_sdf_to_fs(tree_to_modify, tmp_path)

    # 3. Read again and verify
    final_tree = read_sdf_from_fs(tmp_path)
    assert final_tree.sub_topics[0].docs[0].content == "UPDATED CONTENT"
    # Ensure other parts are unchanged
    assert final_tree.sub_topics[0].docs[1].content == "More details for 1.1"

def test_reorder_docs(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that reordering docs in the list updates file prefixes."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    # Read, reorder docs, and write back
    tree_to_modify = read_sdf_from_fs(tmp_path)
    doc0 = tree_to_modify.sub_topics[0].docs[0] # s1-para1
    doc1 = tree_to_modify.sub_topics[0].docs[1] # s1-para2
    tree_to_modify.sub_topics[0].docs = [doc1, doc0] # Swap them
    write_sdf_to_fs(tree_to_modify, tmp_path)

    # Verify file system state
    section1_dir = tmp_path / "0000_section-1"
    assert (section1_dir / "0000_s1-para2.doc.yaml").exists() # was 0001
    assert (section1_dir / "0001_s1-para1.doc.yaml").exists() # was 0000
    assert not (section1_dir / "0000_s1-para1.doc.yaml").exists()

    # Verify model state after reading back
    final_tree = read_sdf_from_fs(tmp_path)
    assert final_tree.sub_topics[0].docs[0].id == "s1-para2"
    assert final_tree.sub_topics[0].docs[1].id == "s1-para1"

def test_rename_topic_updates_directory(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that changing a topic title renames its directory on write."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)
    
    # Read, modify title, and write back
    tree_to_modify = read_sdf_from_fs(tmp_path)
    tree_to_modify.sub_topics[0].manifest.title = "A New Title"
    write_sdf_to_fs(tree_to_modify, tmp_path)
    
    # Verify file system state
    assert not (tmp_path / "0000_section-1").exists()
    new_dir = tmp_path / "0000_a-new-title"
    assert new_dir.is_dir()
    assert (new_dir / "_topic.manifest.yaml").exists()
    
    # Verify model state
    final_tree = read_sdf_from_fs(tmp_path)
    assert final_tree.sub_topics[0].manifest.title == "A New Title"

def test_delete_doc_removes_file(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that removing a doc from the list deletes its file."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    # Read, remove doc, write back
    tree_to_modify = read_sdf_from_fs(tmp_path)
    # Remove "s1-para1"
    tree_to_modify.sub_topics[0].docs.pop(0)
    write_sdf_to_fs(tree_to_modify, tmp_path)

    # Verify file system state
    section1_dir = tmp_path / "0000_section-1"
    # The removed file should be gone
    assert not (section1_dir / "0000_s1-para1.doc.yaml").exists()
    assert not (section1_dir / "0001_s1-para1.doc.yaml").exists() # just in case
    # The remaining file should be re-numbered
    assert (section1_dir / "0000_s1-para2.doc.yaml").exists()

    # Verify model state
    final_tree = read_sdf_from_fs(tmp_path)
    assert len(final_tree.sub_topics[0].docs) == 1
    assert final_tree.sub_topics[0].docs[0].id == "s1-para2"


def test_add_new_doc_creates_file(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that adding a new doc to the list creates a new file."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    tree_to_modify = read_sdf_from_fs(tmp_path)
    new_doc = Doc(id="s1-para3", content="This is a new paragraph.")
    tree_to_modify.sub_topics[0].docs.append(new_doc)
    write_sdf_to_fs(tree_to_modify, tmp_path)

    section1_dir = tmp_path / "0000_section-1"
    assert (section1_dir / "0002_s1-para3.doc.yaml").exists()

    final_tree = read_sdf_from_fs(tmp_path)
    assert len(final_tree.sub_topics[0].docs) == 3
    assert final_tree.sub_topics[0].docs[2].id == "s1-para3"

def test_update_manifest_content(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that modifying manifest content (not title) is persisted."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    tree_to_modify = read_sdf_from_fs(tmp_path)
    tree_to_modify.manifest.status = "deprecated"
    tree_to_modify.manifest.abstract = "This is a new abstract."
    write_sdf_to_fs(tree_to_modify, tmp_path)

    with (tmp_path / "_topic.manifest.yaml").open("r") as f:
        manifest_data = yaml.safe_load(f)
        assert manifest_data["status"] == "deprecated"
        assert manifest_data["abstract"] == "This is a new abstract."

    final_tree = read_sdf_from_fs(tmp_path)
    assert final_tree.manifest.status == "deprecated"

def test_add_sub_topic_creates_directory(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that adding a sub-topic creates a new directory."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    tree_to_modify = read_sdf_from_fs(tmp_path)
    new_topic = SdfTopicNode(
        manifest=TopicManifest(id="section-3", title="Section 3")
    )
    tree_to_modify.sub_topics.append(new_topic)
    write_sdf_to_fs(tree_to_modify, tmp_path)

    assert (tmp_path / "0002_section-3").is_dir()
    assert (tmp_path / "0002_section-3" / "_topic.manifest.yaml").exists()

    final_tree = read_sdf_from_fs(tmp_path)
    assert len(final_tree.sub_topics) == 3
    assert final_tree.sub_topics[2].manifest.id == "section-3"

def test_delete_sub_topic_removes_directory(sample_sdf_tree: SdfTopicNode, tmp_path: Path):
    """Tests that removing a sub-topic deletes its directory and re-numbers siblings."""
    write_sdf_to_fs(sample_sdf_tree, tmp_path)

    tree_to_modify = read_sdf_from_fs(tmp_path)
    tree_to_modify.sub_topics.pop(0) # Remove section-1
    write_sdf_to_fs(tree_to_modify, tmp_path)

    assert not (tmp_path / "0000_section-1").exists()
    assert not (tmp_path / "0001_section-1").exists()
    # Check that section-2 was re-numbered from 0001 to 0000
    assert (tmp_path / "0000_section-2").is_dir()

    final_tree = read_sdf_from_fs(tmp_path)
    assert len(final_tree.sub_topics) == 1
    assert final_tree.sub_topics[0].manifest.id == "section-2"
