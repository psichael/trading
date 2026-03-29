import json
from pathlib import Path
from .models import LASTNode, ModuleNode, FunctionDefNode, PassNode
from pydantic import ValidationError

# A map to resolve node types to their Pydantic models during reading.
NODE_TYPE_MAP = {
    "module": ModuleNode,
    "function_def": FunctionDefNode,
    "pass": PassNode,
}

def write_last_to_fs(node: LASTNode, root_path: Path):
    """
    Recursively writes a LAST node structure to the filesystem.

    Each node becomes a directory containing a meta.json for its properties
    and numbered subdirectories for its children to preserve order.
    """
    root_path.mkdir(exist_ok=True)

    # Separate metadata from children (body).
    node_dict = node.model_dump()
    children_data = node_dict.pop("body", [])

    # Write the node's own metadata.
    meta_file = root_path / "meta.json"
    with meta_file.open("w") as f:
        json.dump(node_dict, f, indent=2)

    # Recursively write children if they exist.
    if children_data:
        for i, child_data in enumerate(children_data):
            # Re-create the Pydantic model for the child to pass to the recursive call.
            child_node = NODE_TYPE_MAP[child_data['node_type']](**child_data)

            # Create a descriptive, sorted directory name.
            child_name = child_data.get("name", child_data["node_type"])
            child_dir_name = f"{i:03d}_{child_name}"
            child_path = root_path / child_dir_name
            write_last_to_fs(child_node, child_path)

def read_last_from_fs(root_path: Path) -> LASTNode:
    """
    Recursively reads a LAST structure from the filesystem into Pydantic models.
    """
    meta_file = root_path / "meta.json"
    if not meta_file.is_file():
        raise FileNotFoundError(f"meta.json not found in {root_path}")

    with meta_file.open("r") as f:
        metadata = json.load(f)

    node_type = metadata.get("node_type")
    if not node_type or node_type not in NODE_TYPE_MAP:
        raise ValueError(f"Invalid or missing node_type in {meta_file}")

    # Find and sort child directories to maintain order.
    child_dirs = sorted([d for d in root_path.iterdir() if d.is_dir()])

    children = []
    for child_dir in child_dirs:
        children.append(read_last_from_fs(child_dir))

    if children:
        metadata["body"] = children

    # Validate and create the Pydantic model.
    try:
        NodeModel = NODE_TYPE_MAP[node_type]
        return NodeModel(**metadata)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed for {meta_file}: {e}") from e
