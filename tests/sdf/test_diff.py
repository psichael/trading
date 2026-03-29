import pytest
from mvs_harness.sdf.models import SdfTopicNode, TopicManifest, Doc
from mvs_harness.sdf.diff import compare_sdf_trees, format_diffs, Added, Removed, Modified, Reordered

@pytest.fixture
def base_tree() -> SdfTopicNode:
    """Provides a base 'before' SDF tree for diffing."""
    return SdfTopicNode(
        manifest=TopicManifest(id="root", title="Root"),
        docs=[
            Doc(id="doc-a", content="Content A"),
            Doc(id="doc-b", content="Content B"),
        ],
        sub_topics=[
            SdfTopicNode(manifest=TopicManifest(id="topic-1", title="Topic 1")),
            SdfTopicNode(manifest=TopicManifest(id="topic-2", title="Topic 2")),
        ]
    )

def test_no_changes(base_tree: SdfTopicNode):
    """Tests that identical trees produce no diffs."""
    after_tree = base_tree.model_copy(deep=True)
    diffs = compare_sdf_trees(base_tree, after_tree)
    assert not diffs
    assert format_diffs(diffs) == "No semantic differences found."

def test_add_doc(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.docs.append(Doc(id="doc-c", content="Content C"))
    
    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 1
    assert isinstance(diffs[0], Added)
    assert diffs[0].id == "doc-c"

def test_remove_doc(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.docs.pop(0) # remove doc-a

    diffs = compare_sdf_trees(base_tree, after_tree)
    # Removing also causes re-ordering of subsequent items
    assert len(diffs) == 2
    assert any(isinstance(d, Removed) and d.id == "doc-a" for d in diffs)
    assert any(isinstance(d, Reordered) and d.id == "doc-b" for d in diffs)

def test_modify_doc(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.docs[0].content = "New Content A"

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 1
    assert isinstance(diffs[0], Modified)
    assert diffs[0].id == "doc-a"
    assert "content changed" in diffs[0].changes

def test_reorder_docs(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.docs.reverse() # Swap doc-a and doc-b

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 2
    assert any(isinstance(d, Reordered) and d.id == "doc-a" and d.from_index == 0 and d.to_index == 1 for d in diffs)
    assert any(isinstance(d, Reordered) and d.id == "doc-b" and d.from_index == 1 and d.to_index == 0 for d in diffs)

def test_add_topic(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.sub_topics.append(SdfTopicNode(manifest=TopicManifest(id="topic-3", title="Topic 3")))

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 1
    assert isinstance(diffs[0], Added)
    assert diffs[0].id == "topic-3"
    assert diffs[0].title == "Topic 3"

def test_remove_topic(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.sub_topics.pop(0) # remove topic-1

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 2
    assert any(isinstance(d, Removed) and d.id == "topic-1" for d in diffs)
    assert any(isinstance(d, Reordered) and d.id == "topic-2" for d in diffs)

def test_modify_manifest(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.manifest.title = "New Root Title"

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 1
    assert isinstance(diffs[0], Modified)
    assert diffs[0].id == "root"
    assert "title changed" in diffs[0].changes[0]

def test_reorder_topics(base_tree: SdfTopicNode):
    after_tree = base_tree.model_copy(deep=True)
    after_tree.sub_topics.reverse() # Swap topic-1 and topic-2

    diffs = compare_sdf_trees(base_tree, after_tree)
    assert len(diffs) == 2
    assert any(isinstance(d, Reordered) and d.id == "topic-1" and d.from_index == 0 and d.to_index == 1 for d in diffs)
    assert any(isinstance(d, Reordered) and d.id == "topic-2" and d.from_index == 1 and d.to_index == 0 for d in diffs)
