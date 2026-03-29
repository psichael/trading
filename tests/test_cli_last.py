import pytest
import ast
from typer.testing import CliRunner
from pathlib import Path

from mvs_harness.cli import app

runner = CliRunner()

@pytest.fixture
def sample_py_file(tmp_path: Path) -> Path:
    """Creates a sample python file for testing."""
    py_file = tmp_path / "sample.py"
    py_file.write_text("""
def my_func():
    pass
""")
    return py_file

def test_cli_last_disassemble(sample_py_file: Path, tmp_path: Path):
    """Tests the 'last disassemble' command."""
    output_dir = tmp_path / "last_output"
    result = runner.invoke(app, ["last", "disassemble", str(sample_py_file), str(output_dir)])

    assert result.exit_code == 0
    assert "Successfully disassembled" in result.stdout
    assert output_dir.is_dir()
    assert (output_dir / "meta.json").is_file()
    assert (output_dir / "000_my_func").is_dir()
    assert (output_dir / "000_my_func" / "meta.json").is_file()

def test_cli_last_assemble(tmp_path: Path):
    """Tests the 'last assemble' command writing to a file."""
    # First, create a dummy LAST structure
    last_dir = tmp_path / "last_input"
    func_dir = last_dir / "000_hello"
    pass_dir = func_dir / "000_pass"
    pass_dir.mkdir(parents=True)
    
    (last_dir / "meta.json").write_text('{"node_type": "module"}')
    (func_dir / "meta.json").write_text('{"node_type": "function_def", "name": "hello", "args": []}')
    (pass_dir / "meta.json").write_text('{"node_type": "pass"}')

    output_file = tmp_path / "output.py"
    result = runner.invoke(app, ["last", "assemble", str(last_dir), "--output", str(output_file)])

    assert result.exit_code == 0
    assert "Successfully assembled" in result.stdout
    assert output_file.is_file()
    
    content = output_file.read_text()
    assert "def hello():" in content
    assert "    pass" in content

def test_cli_round_trip(sample_py_file: Path, tmp_path: Path):
    """Tests a full disassemble then assemble cycle via the CLI."""
    last_dir = tmp_path / "round_trip_last"
    final_py_file = tmp_path / "round_trip.py"

    # 1. Disassemble
    disassemble_result = runner.invoke(app, ["last", "disassemble", str(sample_py_file), str(last_dir)])
    assert disassemble_result.exit_code == 0
    assert last_dir.is_dir()

    # 2. Assemble
    assemble_result = runner.invoke(app, ["last", "assemble", str(last_dir), "--output", str(final_py_file)])
    assert assemble_result.exit_code == 0
    assert final_py_file.is_file()

    # 3. Compare content
    original_ast = ast.dump(ast.parse(sample_py_file.read_text()))
    final_ast = ast.dump(ast.parse(final_py_file.read_text()))
    assert original_ast == final_ast
