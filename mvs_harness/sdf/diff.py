from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union, Dict, Optional, Tuple

from mvs_harness.sdf.models import SdfTopicNode, Doc

@dataclass
class Added:
    item_type: str
    id: str
    title: str
    path: str

@dataclass
class Removed:
    item_type: str
    id: str
    title: str
    path: str

@dataclass
class Modified:
    item_type: str
    id: str
    title: str
    path: str
    changes: List[str]

@dataclass
class Reordered:
    item_type: str
    id: str
    title: str
    path: str
    from_index: int
    to_index: int

SdfDiff = Union[Added, Removed, Modified, Reordered]

def _get_item_title(item: Union[SdfTopicNode, Doc]) -> str:
    if isinstance(item, SdfTopicNode):
        return item.manifest.title
    return item.id # Docs don't have titles, so ID is the best identifier

def _compare_docs(
    before_docs: List[Doc],
    after_docs: List[Doc],
    path_prefix: str
) -> List[SdfDiff]:
    diffs: List[SdfDiff] = []
    before_map: Dict[str, Tuple[int, Doc]] = {doc.id: (i, doc) for i, doc in enumerate(before_docs)}
    after_map: Dict[str, Tuple[int, Doc]] = {doc.id: (i, doc) for i, doc in enumerate(after_docs)}

    all_ids = set(before_map.keys()) | set(after_map.keys())

    for doc_id in sorted(list(all_ids)):
        before_item = before_map.get(doc_id)
        after_item = after_map.get(doc_id)
        
        path_str = f"{path_prefix}/{doc_id}"

        if before_item and not after_item:
            diffs.append(Removed("Doc", doc_id, _get_item_title(before_item[1]), path_str))
        elif not before_item and after_item:
            diffs.append(Added("Doc", doc_id, _get_item_title(after_item[1]), path_str))
        elif before_item and after_item:
            # Check for reordering
            if before_item[0] != after_item[0]:
                diffs.append(Reordered("Doc", doc_id, _get_item_title(before_item[1]), path_str, before_item[0], after_item[0]))
            
            # Check for modification
            if before_item[1].content != after_item[1].content:
                diffs.append(Modified("Doc", doc_id, _get_item_title(before_item[1]), path_str, ["content changed"]))

    return diffs

def _compare_topics(
    before_topics: List[SdfTopicNode],
    after_topics: List[SdfTopicNode],
    path_prefix: str
) -> List[SdfDiff]:
    diffs: List[SdfDiff] = []
    before_map: Dict[str, Tuple[int, SdfTopicNode]] = {t.manifest.id: (i, t) for i, t in enumerate(before_topics)}
    after_map: Dict[str, Tuple[int, SdfTopicNode]] = {t.manifest.id: (i, t) for i, t in enumerate(after_topics)}

    all_ids = set(before_map.keys()) | set(after_map.keys())

    for topic_id in sorted(list(all_ids)):
        before_item = before_map.get(topic_id)
        after_item = after_map.get(topic_id)
        
        title = before_item[1].manifest.title if before_item else after_item[1].manifest.title
        path_str = f"{path_prefix}/{title}"

        if before_item and not after_item:
            diffs.append(Removed("Topic", topic_id, title, path_str))
        elif not before_item and after_item:
            diffs.append(Added("Topic", topic_id, title, path_str))
        elif before_item and after_item:
            # Check for reordering
            if before_item[0] != after_item[0]:
                diffs.append(Reordered("Topic", topic_id, title, path_str, before_item[0], after_item[0]))

            # Recursively find diffs in children
            diffs.extend(compare_sdf_trees(before_item[1], after_item[1], path_str))
    
    return diffs


def compare_sdf_trees(before: SdfTopicNode, after: SdfTopicNode, path_prefix: str = ".") -> List[SdfDiff]:
    """Compares two SdfTopicNode trees and returns a list of differences."""
    diffs: List[SdfDiff] = []

    # 1. Compare manifests of the current node
    if before.manifest.model_dump() != after.manifest.model_dump():
        # A more granular diff could be implemented here, but for now, any change is a modification.
        changes = []
        if before.manifest.title != after.manifest.title:
            changes.append(f"title changed from '{before.manifest.title}' to '{after.manifest.title}'")
        if before.manifest.abstract != after.manifest.abstract:
            changes.append("abstract changed")

        if changes:
             diffs.append(Modified(
                "Topic Manifest",
                before.manifest.id,
                before.manifest.title,
                path_prefix,
                changes
            ))

    # 2. Compare docs within the current node
    doc_diffs = _compare_docs(before.docs, after.docs, path_prefix)
    diffs.extend(doc_diffs)

    # 3. Compare sub-topics
    topic_diffs = _compare_topics(before.sub_topics, after.sub_topics, path_prefix)
    diffs.extend(topic_diffs)
    
    return diffs

def format_diffs(diffs: List[SdfDiff]) -> str:
    """Formats a list of SdfDiff objects into a human-readable string."""
    if not diffs:
        return "No semantic differences found."

    lines = ["Semantic Differences:"]
    for d in diffs:
        if isinstance(d, Added):
            lines.append(f"  [+] ADDED {d.item_type}: '{d.title}' at path '{d.path}'")
        elif isinstance(d, Removed):
            lines.append(f"  [-] REMOVED {d.item_type}: '{d.title}' from path '{d.path}'")
        elif isinstance(d, Modified):
            lines.append(f"  [~] MODIFIED {d.item_type}: '{d.title}' at path '{d.path}'")
            for change in d.changes:
                lines.append(f"    - {change}")
        elif isinstance(d, Reordered):
            lines.append(f"  [~] REORDERED {d.item_type}: '{d.title}' at path '{d.path}' (from index {d.from_index} to {d.to_index})")
    return "\n".join(lines)
