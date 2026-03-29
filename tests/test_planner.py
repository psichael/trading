import pytest
from pathlib import Path
from mvs_harness.planner import generate_file_tree

@pytest.fixture
def file_tree_test_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()

    # Regular structure
    (root / "src").mkdir()
    (root / "src" / "main.py").touch()
    (root / "src" / "utils.py").touch()
    
    (root / "README.md").touch()

    # SDF plan structure
    plan = root / "plan"
    plan.mkdir()
    (plan / "_topic.manifest.yaml").touch()
    epic1 = plan / "0000_e1_first"
    epic1.mkdir()
    (epic1 / "0000_t1_task1.doc.yaml").touch()
    
    epic3 = plan / "e2_e3_third" # out of order, should be last
    epic3.mkdir()

    epic2 = plan / "e1_e2_second" # should come after e1
    epic2.mkdir()
    
    (plan / "notes.txt").touch()

    # SDF spec structure
    spec = root / "spec"
    spec.mkdir()
    sdf_spec = spec / "sdf"
    sdf_spec.mkdir()
    (sdf_spec / "0000_p1_intro.doc.yaml").touch()
    last_spec = spec / "last"
    last_spec.mkdir()

    return root

def test_generate_file_tree_orders_and_abstracts_sdf(file_tree_test_dir: Path):
    tree_output = generate_file_tree(file_tree_test_dir)
    
    # Expected output reflects SDF ordering and a full recursive listing.
    expected_lines = [
        "./",
        "\u251c\u2500\u2500 plan",
        "\u2502   \u251c\u2500\u2500 0000_e1_first",
        "\u2502   \u2502   \u2514\u2500\u2500 0000_t1_task1.doc.yaml",
        "\u2502   \u251c\u2500\u2500 e1_e2_second",
        "\u2502   \u251c\u2500\u2500 e2_e3_third",
        "\u2502   \u251c\u2500\u2500 _topic.manifest.yaml",
        "\u2502   \u2514\u2500\u2500 notes.txt",
        "\u251c\u2500\u2500 spec",
        "\u2502   \u251c\u2500\u2500 last",
        "\u2502   \u2514\u2500\u2500 sdf",
        "\u2502       \u2514\u2500\u2500 0000_p1_intro.doc.yaml",
        "\u251c\u2500\u2500 src",
        "\u2502   \u251c\u2500\u2500 main.py",
        "\u2502   \u2514\u2500\u2500 utils.py",
        "\u2514\u2500\u2500 README.md",
    ]
    expected_output = "\n".join(expected_lines)
    
    # Normalize line endings and compare
    actual_normalized = tree_output.strip().replace('\r\n', '\n')
    expected_normalized = expected_output.strip().replace('\r\n', '\n')
    
    assert actual_normalized == expected_normalized
