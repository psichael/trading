from pathlib import Path

from mvs_harness.schemas.models import AgentPrompt, WorkOrder, ContextFile

# CORRECTED IMPORT: Use absolute path to the functional utility
from mvs_harness.state_assembler.file_tree import generate_file_tree

from .loaders.protocol_loader import load_operational_protocol
from .loaders.context_files_loader import load_context_files
from .loaders.recent_events_loader import load_recent_events
from .loaders.knowledge_loader import load_core_knowledge

# Directories whose contents are already embedded in the prompt header
EMBEDDED_CONTEXT_DIRS = [
    'spec/implementer_protocol/',
    'spec/planner_protocol/',
    'spec/orchestrator_protocol/',
    'spec/agent_knowledge/'
]


class AgentPromptBuilder:
    """
    Orchestrates the assembly of the AgentPrompt using modular loaders.
    """
    def __init__(self, work_order: WorkOrder, project_root: Path):
        """
        Initializes the builder with the necessary inputs.

        Args:
            work_order: The WorkOrder for the current task.
            project_root: The root directory of the project.
        """
        self.work_order = work_order
        self.project_root = project_root

    def assemble(self) -> AgentPrompt:
        """
        Constructs the complete AgentPrompt by calling all data loaders.

        Returns:
            A fully populated and validated AgentPrompt object.
        """
        # Determine which protocol to load based on the agent's role.
        if "planner-agent" in self.work_order.active_task:
            protocol_name = "planner_protocol"
        else:
            protocol_name = "implementer_protocol"

        # Load all the individual components using the dedicated loaders
        protocol_content = load_operational_protocol(self.project_root, protocol_name)
        core_knowledge_content = load_core_knowledge(self.project_root)

        # Load all requested context files from the WorkOrder
        all_context_files = load_context_files(self.work_order, self.project_root)

        # Filter out protocol/knowledge files that are already embedded
        filtered_context_files: list[ContextFile] = []

        for context_file in all_context_files:
            is_embedded = False
            for prefix in EMBEDDED_CONTEXT_DIRS:
                if context_file.path.startswith(prefix):
                    is_embedded = True
                    break

            if not is_embedded:
                filtered_context_files.append(context_file)

        context_files_data = filtered_context_files

        recent_events_data = load_recent_events(self.project_root)
        file_tree_str = generate_file_tree(self.project_root)

        # Assemble and validate the final AgentPrompt object
        agent_prompt = AgentPrompt(
            operational_protocol=protocol_content,
            agent_knowledge_base=core_knowledge_content if core_knowledge_content else None,
            core_context={},
            epic_context=None,  # Epic context loading is not part of this refactor
            work_order=self.work_order,
            context_files=context_files_data,
            recent_events=recent_events_data,
            file_tree=file_tree_str
        )

        return agent_prompt
