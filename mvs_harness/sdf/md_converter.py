import mistune
import yaml
import uuid
import re
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel
from mistune.renderers.markdown import MarkdownRenderer

# --- Pydantic Models (derived from SDF v3 spec) ---
class SdfManifest(BaseModel):
    id: str
    title: str
    status: str = 'draft'
    # Abstract is now optional, as it can be captured or provided by frontmatter
    abstract: Optional[str] = None

class SdfDocument(BaseModel):
    id: str
    type: str
    status: str = 'draft'
    content: str

# --- Frontmatter Parsing ---
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)

def parse_frontmatter(text: str) -> Tuple[Dict, str]:
    """Parses YAML frontmatter from a string."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    
    frontmatter_str = match.group(1)
    content = text[match.end():]
    
    try:
        data = yaml.safe_load(frontmatter_str)
        if isinstance(data, dict):
            return data, content
    except yaml.YAMLError:
        # If parsing fails, treat it as regular content
        return {}, text
    
    return {}, text


# --- Helper Function ---
def slugify(text: str) -> str:
    text = text.lower()
    # FIX: Explicitly replace underscores with hyphens first.
    text = text.replace('_', '-')
    # Then, replace any remaining invalid characters (not word, space, or hyphen) with a space.
    text = re.sub(r'[^\w\s-]', ' ', text)
    # Then, collapse whitespace sequences and multiple hyphens into a single hyphen.
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text[:50]

class SdfRenderer(MarkdownRenderer):
    def __init__(self, root_title: str, root_id: Optional[str] = None, root_abstract: Optional[str] = None):
        super().__init__()
        self.root_title = root_title
        self.output_files: Dict[str, str] = {}
        self.path_parts: List[str] = []
        self.sibling_counters: List[int] = []
        self.content_counter: int = 0
        self.is_processing_list: bool = False

        # New state variables for abstract capturing
        self.last_manifest_path: Optional[str] = None
        self.capture_next_paragraph_as_abstract: bool = False

        self._add_manifest(
            self.root_title,
            manifest_id=root_id,
            abstract=root_abstract,
            is_root=True
        )

    def _add_manifest(self, title: str, manifest_id: Optional[str] = None, abstract: Optional[str] = None, is_root: bool = False):
        if is_root:
            path = "_topic.manifest.yaml"
        else:
            path = "/".join(self.path_parts) + "/_topic.manifest.yaml"
        
        # Use provided abstract or a default one
        final_abstract = abstract if abstract is not None else f"Specification section for '{title}'."

        manifest = SdfManifest(
            id=manifest_id or str(uuid.uuid4()),
            title=title,
            status='draft',
            abstract=final_abstract
        )
        self.output_files[path] = yaml.dump(manifest.model_dump(exclude_none=True), sort_keys=False)
        
        # Store path and set flag to capture the next paragraph if no abstract was provided
        if abstract is None:
            self.last_manifest_path = path
            self.capture_next_paragraph_as_abstract = True
        else:
            # If an abstract was provided, we don't need to capture another one for this manifest
            self.capture_next_paragraph_as_abstract = False

        return manifest.id

    def _add_doc_file(self, content: str, doc_type: str):
        slug = doc_type
        if doc_type == 'paragraph':
            slug = 'p'
        
        doc_id = str(uuid.uuid4())
        doc_name = f"{self.content_counter:04d}_{doc_id}_{slug}.doc.yaml"
        path_prefix = "/".join(self.path_parts)
        full_path = f"{path_prefix}/{doc_name}" if path_prefix else doc_name

        doc = SdfDocument(
            id=doc_id,
            type=doc_type,
            status='draft',
            content=content
        )
        self.output_files[full_path] = yaml.dump(doc.model_dump(exclude_none=True), sort_keys=False)
        self.content_counter += 1

    def heading(self, token, state):
        self.content_counter = 0
        level = token['attrs']['level']
        title = self.render_children(token, state)
        
        # We handle the root title (H1) in the initializer. This parser will still see it, but we ignore it.
        if level == 1:
            # If we just processed the root manifest, the next paragraph is its abstract (if not in frontmatter)
            if self.last_manifest_path == "_topic.manifest.yaml":
                self.capture_next_paragraph_as_abstract = True
            return ""

        path_level = level - 2

        while len(self.sibling_counters) <= path_level:
            self.sibling_counters.append(-1)
        
        self.sibling_counters[path_level] += 1
        
        if path_level + 1 < len(self.sibling_counters):
            for i in range(path_level + 1, len(self.sibling_counters)):
                self.sibling_counters[i] = -1
        
        counter = self.sibling_counters[path_level]
        slug_text = slugify(re.sub(r'[`*]', '', title))
        
        manifest_id = str(uuid.uuid4())
        dir_name = f"{counter:04d}_{manifest_id}_{slug_text}"
        
        self.path_parts = self.path_parts[:path_level]
        self.path_parts.append(dir_name)
        
        self._add_manifest(title, manifest_id=manifest_id)
        return ""

    def paragraph(self, token, state):
        content = self.render_children(token, state).strip()
        if not content:
            return ""

        # Check if we should capture this paragraph as an abstract
        if self.capture_next_paragraph_as_abstract and self.last_manifest_path:
            try:
                # Load the manifest data from our in-memory dict, update abstract, and write back
                manifest_data = yaml.safe_load(self.output_files[self.last_manifest_path])
                manifest_data['abstract'] = content
                self.output_files[self.last_manifest_path] = yaml.dump(manifest_data, sort_keys=False)
                
                # Reset the flag so we don't capture again for this manifest
                self.capture_next_paragraph_as_abstract = False
                self.last_manifest_path = None # Clear it to be safe
                return "" # Stop processing; do not create a redundant .doc file
            except (KeyError, yaml.YAMLError):
                # Fallback in case of an error (e.g., path not found), just create a doc file
                pass
        
        # If not capturing, create a normal doc file
        self._add_doc_file(content, 'paragraph')
        return ""

    def block_code(self, token, state):
        # Any other block-level element cancels the abstract capture
        self.capture_next_paragraph_as_abstract = False
        code = token['raw']
        info = token.get('info')
        lang = info or ''
        content = f"```{lang}\n{code.rstrip()}\n```"
        self._add_doc_file(content, 'code')
        return ""

    def list(self, token, state):
        # Any other block-level element cancels the abstract capture
        self.capture_next_paragraph_as_abstract = False
            
        if self.is_processing_list:
            return super().list(token, state)

        self.is_processing_list = True
        list_text = super().list(token, state).strip()
        if list_text:
            self._add_doc_file(list_text, 'list')
        self.is_processing_list = False
        
        return ""

    def finalize(self):
        return self.output_files

def convert_markdown_to_sdf(markdown_text: str, root_title: Optional[str] = None) -> Dict[str, str]:
    frontmatter, content = parse_frontmatter(markdown_text)
    
    # Title can come from frontmatter, function argument, or fallback
    final_root_title = frontmatter.get('title', root_title or "SDF Document")
    root_id = frontmatter.get('id')
    root_abstract = frontmatter.get('abstract')
    
    renderer = SdfRenderer(
        root_title=final_root_title,
        root_id=root_id,
        root_abstract=root_abstract
    )
    markdown = mistune.Markdown(renderer=renderer)
    markdown(content)
    return renderer.finalize()