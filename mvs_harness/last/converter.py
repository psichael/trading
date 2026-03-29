import ast
from .models import LASTNode, ModuleNode, FunctionDefNode, PassNode

# --- Python AST to LAST Conversion ---

def _convert_node(py_node: ast.AST) -> LASTNode:
    """Recursively converts a Python AST node to a LAST node."""
    if isinstance(py_node, ast.Module):
        return ModuleNode(
            body=[_convert_node(n) for n in py_node.body]
        )
    elif isinstance(py_node, ast.FunctionDef):
        return FunctionDefNode(
            name=py_node.name,
            args=[arg.arg for arg in py_node.args.args],
            body=[_convert_node(n) for n in py_node.body]
        )
    elif isinstance(py_node, ast.Pass):
        return PassNode()
    
    raise NotImplementedError(f"Conversion for Python AST node type '{type(py_node).__name__}' is not implemented.")

def py_to_last(source_code: str) -> ModuleNode:
    """
    Parses Python source code and converts it into a LAST tree.
    """
    py_ast = ast.parse(source_code)
    last_node = _convert_node(py_ast)
    if not isinstance(last_node, ModuleNode):
        raise TypeError("The root of a LAST tree must be a ModuleNode.")
    return last_node

# --- LAST to Python Source Conversion ---

def _generate_source(last_node: LASTNode, indent_level: int = 0) -> str:
    """Recursively generates Python source code from a LAST node."""
    indent = "    " * indent_level
    
    if isinstance(last_node, ModuleNode):
        return "\n".join(_generate_source(n, indent_level) for n in last_node.body)
    
    elif isinstance(last_node, FunctionDefNode):
        args_str = ", ".join(last_node.args)
        # Handle empty body with a 'pass' statement
        if not last_node.body:
            body_str = f"{indent}    pass"
        else:
            body_str = "\n".join(
                _generate_source(n, indent_level + 1) for n in last_node.body
            )
        return f"{indent}def {last_node.name}({args_str}):\n{body_str}"
        
    elif isinstance(last_node, PassNode):
        return f"{indent}pass"
        
    raise NotImplementedError(f"Source generation for LAST node type '{last_node.node_type}' is not implemented.")


def last_to_py(last_node: ModuleNode) -> str:
    """
    Converts a LAST tree back into a Python source code string.
    """
    return _generate_source(last_node) + "\n" # Ensure trailing newline for PEP8
