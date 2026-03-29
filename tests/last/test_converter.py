import pytest
import ast
from mvs_harness.last.converter import py_to_last, last_to_py
from mvs_harness.last.models import ModuleNode, FunctionDefNode, PassNode

@pytest.fixture
def sample_python_code() -> str:
    return """\
def my_function(arg1, arg2):
    pass
"""

@pytest.fixture
def corresponding_last_tree() -> ModuleNode:
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

def test_py_to_last(sample_python_code, corresponding_last_tree):
    """Tests converting Python source code to a LAST tree."""
    generated_last = py_to_last(sample_python_code)
    assert generated_last == corresponding_last_tree

def test_last_to_py(corresponding_last_tree, sample_python_code):
    """Tests converting a LAST tree back to Python source code."""
    generated_code = last_to_py(corresponding_last_tree)
    # Use ast.dump for a canonical comparison, ignoring formatting differences
    expected_ast = ast.dump(ast.parse(sample_python_code))
    generated_ast = ast.dump(ast.parse(generated_code))
    assert generated_ast == expected_ast

def test_round_trip_safety(sample_python_code):
    """Ensures that code converted to LAST and back is semantically identical."""
    # 1. Convert from Python source to LAST
    last_representation = py_to_last(sample_python_code)

    # 2. Convert from LAST back to Python source
    reconstructed_code = last_to_py(last_representation)
    
    # 3. Compare the ASTs of the original and reconstructed code
    original_ast = ast.dump(ast.parse(sample_python_code))
    reconstructed_ast = ast.dump(ast.parse(reconstructed_code))
    
    assert original_ast == reconstructed_ast

def test_unimplemented_node_py_to_last():
    """Checks that an unsupported AST node raises NotImplementedError."""
    unsupported_code = "class MyClass:\n    pass"
    with pytest.raises(NotImplementedError, match="ClassDef"):
        py_to_last(unsupported_code)
