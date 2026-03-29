import pytest
from unittest.mock import MagicMock
from mvs_harness.sdf.md_converter import convert_markdown_to_sdf, slugify

# --- Test Data ---

SAMPLE_MARKDOWN_NO_FRONTMATTER = """# Main Title

This is the abstract.

## Section 1

This is a paragraph.

```
print("hello")
```"""

SAMPLE_MARKDOWN_WITH_FRONTMATTER = """---
id: custom-root-id
title: Custom Title from Frontmatter
abstract: This is a custom abstract from the frontmatter.
---
# This H1 is ignored

This paragraph should be a normal doc file, not an abstract.

## Section 1

This is the section abstract.
"""

# --- Fixtures ---

@pytest.fixture
def mock_uuid(monkeypatch):
    mock = MagicMock()
    # Make the mock return sequential, predictable UUIDs for stable testing
    mock.side_effect = [
        f"00000000-0000-0000-0000-{i:012d}" for i in range(1, 20)
    ]
    monkeypatch.setattr('mvs_harness.sdf.md_converter.uuid.uuid4', mock)
    return mock

# --- Test Cases ---

def test_markdown_to_sdf_no_frontmatter(mock_uuid):
    """Tests the original behavior when no frontmatter is present."""
    result = convert_markdown_to_sdf(SAMPLE_MARKDOWN_NO_FRONTMATTER, "Fallback Title")

    # Check for root manifest and its abstract
    assert "_topic.manifest.yaml" in result
    # It should use the fallback title and generate a new UUID
    assert "id: 00000000-0000-0000-0000-000000000001" in result["_topic.manifest.yaml"]
    assert "title: Fallback Title" in result["_topic.manifest.yaml"]
    assert "abstract: This is the abstract." in result["_topic.manifest.yaml"]

    # Check for the Section 1 manifest and its abstract (the first paragraph)
    expected_topic_path = "0000_00000000-0000-0000-0000-000000000002_section-1/_topic.manifest.yaml"
    assert expected_topic_path in result
    assert "abstract: This is a paragraph." in result[expected_topic_path]

    # The code block should still create a doc file
    expected_code_path = "0000_00000000-0000-0000-0000-000000000002_section-1/0000_00000000-0000-0000-0000-000000000003_code.doc.yaml"
    assert expected_code_path in result
    assert 'print("hello")' in result[expected_code_path]


def test_markdown_to_sdf_with_frontmatter(mock_uuid):
    """Tests that frontmatter correctly overrides default behavior."""
    result = convert_markdown_to_sdf(SAMPLE_MARKDOWN_WITH_FRONTMATTER, "This Title is Ignored")
    
    # Check that the root manifest uses frontmatter values
    assert "_topic.manifest.yaml" in result
    assert "id: custom-root-id" in result["_topic.manifest.yaml"]
    assert "title: Custom Title from Frontmatter" in result["_topic.manifest.yaml"]
    assert "abstract: This is a custom abstract from the frontmatter." in result["_topic.manifest.yaml"]

    # Check that the first paragraph is NOT captured as an abstract
    # It should be a regular doc file instead.
    expected_doc_path = "0000_00000000-0000-0000-0000-000000000001_p.doc.yaml"
    assert expected_doc_path in result
    assert "content: This paragraph should be a normal doc file, not an abstract." in result[expected_doc_path]

    # Check that Section 1 is still created correctly
    expected_topic_path = "0000_00000000-0000-0000-0000-000000000002_section-1/_topic.manifest.yaml"
    assert expected_topic_path in result
    assert "abstract: This is the section abstract." in result[expected_topic_path]


def test_converter_creates_correct_ids_in_files(mock_uuid):
    result = convert_markdown_to_sdf("## Section 1\n\nPara 1", "Test IDs")

    # Account for root manifest UUID consumption.
    topic_path = "0000_00000000-0000-0000-0000-000000000002_section-1/_topic.manifest.yaml"

    # Assert that the manifest exists and contains the correct ID
    assert f"id: 00000000-0000-0000-0000-000000000002" in result[topic_path]
    # Assert that the paragraph was correctly captured as the abstract
    assert "abstract: Para 1" in result[topic_path]


def test_converter_handles_nested_headings(mock_uuid):
    nested_md = "## Level 1\n\nAbstract 1\n\n### Level 2\n\nAbstract 2"
    result = convert_markdown_to_sdf(nested_md, "Nested Test")

    # Account for root manifest UUID consumption.
    level1_topic_path = "0000_00000000-0000-0000-0000-000000000002_level-1/_topic.manifest.yaml"
    level2_topic_path = "0000_00000000-0000-0000-0000-000000000002_level-1/0000_00000000-0000-0000-0000-000000000003_level-2/_topic.manifest.yaml"
    
    assert level1_topic_path in result
    assert "abstract: Abstract 1" in result[level1_topic_path]
    assert level2_topic_path in result
    assert "abstract: Abstract 2" in result[level2_topic_path]


def test_converter_preserves_inline_code(mock_uuid):
    md_with_code = "## Section with `inline_code`\n\nSome text with `_cosa.boundary.json`."
    result = convert_markdown_to_sdf(md_with_code, "Inline Code Test")

    # Account for root manifest UUID consumption.
    topic_path = "0000_00000000-0000-0000-0000-000000000002_section-with-inline-code/_topic.manifest.yaml"
    
    assert topic_path in result
    # Assert that the paragraph containing the inline code was correctly captured as the abstract
    assert "abstract: Some text with `_cosa.boundary.json`." in result[topic_path]


def test_slugify_handles_various_inputs():
    # slugify is a standalone function, not a method.
    assert slugify("Simple Title") == "simple-title"
    # This test is updated to reflect the fixed slugify logic that correctly handles underscores.
    assert slugify("Title with_special-chars!@#$") == "title-with-special-chars"
    assert slugify("  leading/trailing spaces  ") == "leading-trailing-spaces"
