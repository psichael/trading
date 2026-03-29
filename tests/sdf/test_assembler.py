import pytest
from mvs_harness.sdf.models import SdfTopicNode, TopicManifest, Doc
from mvs_harness.sdf.assembler import assemble_sdf_to_markdown

@pytest.fixture
def sample_sdf_tree_for_assembly() -> SdfTopicNode:
    """Provides a sample in-memory SDF structure for assembly testing."""
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
                    abstract="", # Test empty abstract
                )
            ),
        ],
    )

def test_assemble_sdf_to_markdown(sample_sdf_tree_for_assembly: SdfTopicNode):
    """Tests the core logic of the SDF assembler."""
    markdown = assemble_sdf_to_markdown(sample_sdf_tree_for_assembly)

    # Check for traceability comments
    assert "<!-- sdf-id: root-doc -->" in markdown
    assert "<!-- sdf-id: intro-para -->" in markdown
    assert "<!-- sdf-id: section-1 -->" in markdown
    assert "<!-- sdf-id: s1-para1 -->" in markdown
    assert "<!-- sdf-id: s1-para2 -->" in markdown
    assert "<!-- sdf-id: section-2 -->" in markdown

    # Check for content and structure
    assert "# Root Document" in markdown
    assert "This is the main abstract." in markdown
    assert "This is the intro paragraph." in markdown
    assert "## Section 1" in markdown
    assert "Content for the first section." in markdown
    assert "Details for 1.1" in markdown
    assert "More details for 1.1" in markdown
    assert "## Section 2" in markdown

    # Check order and formatting using a more robust method
    expected_structure = [
        "<!-- sdf-id: root-doc -->",
        "# Root Document",
        "This is the main abstract.",
        "<!-- sdf-id: intro-para -->",
        "This is the intro paragraph.",
        "<!-- sdf-id: section-1 -->",
        "## Section 1",
        "Content for the first section.",
        "<!-- sdf-id: s1-para1 -->",
        "Details for 1.1",
        "<!-- sdf-id: s1-para2 -->",
        "More details for 1.1",
        "<!-- sdf-id: section-2 -->",
        "## Section 2",
    ]

    # Create a clean, order-sensitive list of content lines from the output
    actual_lines = [line for line in markdown.strip().split('\n') if line.strip()]

    assert actual_lines == expected_structure
