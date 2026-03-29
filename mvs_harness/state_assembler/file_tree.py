import re
from pathlib import Path

SDF_NAMING_PATTERN = re.compile(r'^([a-zA-Z0-9\\-]+)_([a-zA-Z0-9\\-]+)_.+$')

def generate_file_tree(root_dir: Path = Path('.')) -> str:
    # This function is now modified to exclude common cache/system directories 
    # to optimize the context payload.
    tree_lines = []
    ignore_patterns = {
        '.git', 
        '__pycache__', 
        '.vscode', 
        '.idea', 
        '.ddio', 
        'poetry.lock', 
        '.pytest_cache',
        '.venv',  # Exclude virtual environment
        '.ruff_cache', # Exclude ruff cache
        'build' # Exclude build artifacts
    }
    
    def walk(current_path: Path, prefix: str = ''):
        try:
            items_in_dir = [p for p in current_path.iterdir() if p.name not in ignore_patterns and not p.name.endswith('.pyc')]
        except FileNotFoundError:
            return

        sdf_items = {}
        non_sdf_items = []
        for item in items_in_dir:
            match = SDF_NAMING_PATTERN.match(item.name)
            if match:
                predecessor, my_id = match.groups()
                sdf_items[my_id] = {'path': item, 'predecessor': predecessor}
            else:
                non_sdf_items.append(item)

        ordered_sdf_items = []
        if sdf_items:
            pred_to_children = {}
            for my_id, data in sdf_items.items():
                pred = data['predecessor']
                if pred not in pred_to_children:
                    pred_to_children[pred] = []
                pred_to_children[pred].append(sdf_items[my_id]['path'])
            
            for pred in pred_to_children:
                pred_to_children[pred].sort(key=lambda p: p.name)

            processing_queue = pred_to_children.get('0000', [])
            visited_paths = set()
            while processing_queue:
                item = processing_queue.pop(0)
                if item in visited_paths:
                    continue
                
                visited_paths.add(item)
                ordered_sdf_items.append(item)
                
                item_match = SDF_NAMING_PATTERN.match(item.name)
                if item_match:
                    item_id = item_match.groups()[1]
                    children = pred_to_children.get(item_id, [])
                    processing_queue[0:0] = children

        sorted_non_sdf = sorted(non_sdf_items, key=lambda p: (p.is_file(), p.name.lower()))
        items = ordered_sdf_items + sorted_non_sdf
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            # Use ASCII tree characters for better efficiency and readability in text context
            connector = '`-- ' if is_last else '|-- '
            tree_lines.append(f"{prefix}{connector}{item.name}")

            if item.is_dir():
                # Update prefix character
                new_prefix = prefix + ('    ' if is_last else '|   ')
                walk(item, new_prefix)

    tree_lines.append(f"./")
    walk(root_dir)
    # Remove the redundant/complex Unicode string replacement logic
    return "\n".join(tree_lines)
