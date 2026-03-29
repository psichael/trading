from mvs_harness.sdf.models import SdfTopicNode, Doc
from typing import List

def _assemble_node(node: SdfTopicNode, level: int = 1) -> List[str]:
    """Recursively assembles an SdfTopicNode into a list of Markdown strings."""
    parts = []
    
    # Add manifest title as a heading with traceability comment
    parts.append(f"<!-- sdf-id: {node.manifest.id} -->")
    parts.append(f"{'#' * level} {node.manifest.title}")
    parts.append("") # Add a blank line for spacing

    # Add manifest abstract if it exists
    if node.manifest.abstract and node.manifest.abstract.strip():
        parts.append(node.manifest.abstract.strip())
        parts.append("")

    # Process docs within this topic
    for doc in node.docs:
        parts.append(f"<!-- sdf-id: {doc.id} -->")
        if doc.content and doc.content.strip():
            parts.append(doc.content.strip())
            parts.append("")

    # Recursively process sub-topics
    if node.sub_topics:
        for child_node in node.sub_topics:
            parts.extend(_assemble_node(child_node, level + 1))
            
    return parts

def assemble_sdf_to_markdown(root_node: SdfTopicNode) -> str:
    """
    Converts an SdfTopicNode tree into a single, well-formatted Markdown document.
    """
    markdown_parts = _assemble_node(root_node, level=1)
    return "\n".join(markdown_parts).strip() + "\n"
