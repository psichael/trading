import uuid
from pathlib import Path

import pytest
from mvs_harness.sdf.utils import (
    SdfPathInfo,
    generate_uuid,
    parse_sdf_path,
    renumber_sdf_paths,
    slugify,
)


def test_generate_uuid():
    """Tests that generate_uuid returns a valid UUID string."""
    new_uuid = generate_uuid()
    assert isinstance(new_uuid, str)
    # Check if it's a valid UUID
    try:
        uuid.UUID(new_uuid)
    except ValueError:
        pytest.fail(f"'{new_uuid}' is not a valid UUID.")

@pytest.mark.parametrize(
    "input_text, expected_slug",
    [
        ("Hello World", "hello-world"),
        ("  Leading/Trailing Spaces  ", "leadingtrailing-spaces"),
        ("Special Chars!@#$%^&*()", "special-chars"),
        ("under_scores and-dashes", "under_scores-and-dashes"),
        ("File.with.dots", "file-with-dots"),
        ("A title with 123 numbers", "a-title-with-123-numbers"),
    ],
)
def test_slugify(input_text, expected_slug):
    """Tests the slugify function with various inputs."""
    assert slugify(input_text) == expected_slug

@pytest.mark.parametrize(
    "path_name, is_valid, expected",
    [
        (
            "0001_a1b2c3d4-e5f6-7890-1234-567890abcdef_my-slug.doc.yaml",
            True,
            SdfPathInfo(index=1.0, uuid="a1b2c3d4-e5f6-7890-1234-567890abcdef", slug="my-slug"),
        ),
        (
            "0000_ffffffff-ffff-ffff-ffff-ffffffffffff_another-slug",  # Directory
            True,
            SdfPathInfo(index=0.0, uuid="ffffffff-ffff-ffff-ffff-ffffffffffff", slug="another-slug"),
        ),
        (
            "0001.001_b2c3d4e5-f6a7-8901-2345-67890abcdef1_inserted-slug.doc.yaml",  # Decimal index
            True,
            SdfPathInfo(index=1.001, uuid="b2c3d4e5-f6a7-8901-2345-67890abcdef1", slug="inserted-slug"),
        ),
        (
            "12345_123_no-uuid-slug",  # Invalid UUID format
            False,
            None,
        ),
        (
            "no-index_a1b2c3d4-e5f6-7890-1234-567890abcdef_slug",
            False,
            None,
        ),
        (
            "_a1b2c3d4-e5f6-7890-1234-567890abcdef_slug",  # Missing index
            False,
            None,
        ),
        (
            "0001__slug",  # Missing UUID
            False,
            None,
        ),
        (
            "0001_a1b2c3d4-e5f6-7890-1234-567890abcdef_",  # Missing slug
            False,
            None,
        ),
        (
            "_topic.manifest.yaml",  # Special file, should fail
            False,
            None,
        ),
    ],
)
def test_parse_sdf_path(path_name, is_valid, expected):
    """Tests the SDF path parser with valid and invalid inputs."""
    path = Path(path_name)
    result = parse_sdf_path(path)
    if is_valid:
        assert result is not None
        # Use pytest.approx for float comparison
        assert result.index == pytest.approx(expected.index)
        assert result.uuid == expected.uuid
        assert result.slug == expected.slug
    else:
        assert result is None


def test_renumber_sdf_paths_simple_insertion():
    """Tests renumbering with a single decimal insertion that causes a cascade."""
    paths = [
        Path("0000_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa_first.doc.yaml"),
        Path("0001_cccccccc-cccc-cccc-cccc-cccccccccccc_third.doc.yaml"),
        Path("0000.5_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_inserted.doc.yaml"),
    ]

    result = renumber_sdf_paths(paths)
    result.sort(key=lambda x: str(x[0]))  # sort for deterministic check

    expected_renames = [
        (
            Path("0000.5_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_inserted.doc.yaml"),
            Path("0001_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_inserted.doc.yaml"),
        ),
        (
            Path("0001_cccccccc-cccc-cccc-cccc-cccccccccccc_third.doc.yaml"),
            Path("0002_cccccccc-cccc-cccc-cccc-cccccccccccc_third.doc.yaml"),
        ),
    ]

    assert result == expected_renames


def test_renumber_sdf_paths_multiple_insertions_and_types():
    """Tests renumbering with multiple insertions, directories, and files."""
    paths = [
        Path("0001_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_second-dir"),
        Path("0000_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa_first.doc.yaml"),
        Path("0000.1_cccccccc-cccc-cccc-cccc-cccccccccccc_inserted-file.doc.yaml"),
        Path("0000.2_dddddddd-dddd-dddd-dddd-dddddddddddd_inserted-dir"),
        Path("_topic.manifest.yaml"),  # Should be ignored
    ]

    result = renumber_sdf_paths(paths)

    # Sort results by the old path name for deterministic comparison
    result.sort(key=lambda x: str(x[0]))

    expected_renames = [
        (
            Path("0000.1_cccccccc-cccc-cccc-cccc-cccccccccccc_inserted-file.doc.yaml"),
            Path("0001_cccccccc-cccc-cccc-cccc-cccccccccccc_inserted-file.doc.yaml"),
        ),
        (
            Path("0000.2_dddddddd-dddd-dddd-dddd-dddddddddddd_inserted-dir"),
            Path("0002_dddddddd-dddd-dddd-dddd-dddddddddddd_inserted-dir"),
        ),
        (
            Path("0001_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_second-dir"),
            Path("0003_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_second-dir"),
        ),
    ]

    assert result == expected_renames


def test_renumber_sdf_paths_no_changes_needed():
    """Tests a list of paths that are already in correct order."""
    paths = [
        Path("0000_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa_first.doc.yaml"),
        Path("0001_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb_second.doc.yaml"),
    ]
    result = renumber_sdf_paths(paths)
    assert result == []


def test_renumber_sdf_paths_empty_list():
    """Tests that an empty list of paths produces an empty list of operations."""
    result = renumber_sdf_paths([])
    assert result == []
