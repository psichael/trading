# scripts/test_prompt_builder.py
"""
A simulation script to test the output of the new AgentPromptBuilder.

This script creates a temporary mock project, runs the builder, and prints
the resulting AgentPrompt JSON to stdout for verification.
"""
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Ensure the script can find the mvs_harness module
import sys
project_root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root_dir))

from mvs_harness.schemas.models import WorkOrder
from mvs_harness.prompt_builder.builder import AgentPromptBuilder

def setup_mock_project(tmp_path: Path):
    """Creates a mock project structure in a temporary directory."""
    # 1. Create ddio_framework.json
    framework_data = {"v": "3.10", "purpose": "Simulation Framework"}
    (tmp_path / "ddio_framework.json").write_text(json.dumps(framework_data))

    # 2. Create agent protocol
    build_spec_dir = tmp_path / "build" / "spec"
    build_spec_dir.mkdir(parents=True)
    protocol_content = "# Simulation Agent Protocol"
    (build_spec_dir / "protocols__agent-protocol.md").write_text(protocol_content)

    # 3. Create event log
    ddio_dir = tmp_path / ".ddio"
    ddio_dir.mkdir()
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": "sim", "summary": "Simulation start"}
    (ddio_dir / "events.log").write_text(json.dumps(event) + "\n")

    # 4. Create sample files for context
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello simulation')")
    
    # 5. Create proposal schema for context
    schema_dir = tmp_path / "mvs_harness" / "schemas"
    schema_dir.mkdir(parents=True)
    schema_content = '{"title": "MVS Proposal"}'
    (schema_dir / "proposal.schema.json").write_text(schema_content)


    # 6. Create a sample task file
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    task_content = "content: 'This is the simulation task.'"
    (plan_dir / "task.doc.yaml").write_text(task_content)
    
    print(f"Mock project created at: {tmp_path}")
    return task_content

def main():
    """Main simulation function."""
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        project_root = Path(tmp_dir_str)
        task_content = setup_mock_project(project_root)

        # Define the WorkOrder for our simulation
        work_order = WorkOrder(
            active_task="plan/task.doc.yaml",
            task_content=task_content,
            required_context_files=["src/main.py"]
        )

        print("\n--- Running AgentPromptBuilder Simulation ---")
        try:
            # Instantiate and run the builder
            builder = AgentPromptBuilder(work_order=work_order, project_root=project_root)
            prompt = builder.assemble()

            # Reorder the dictionary to place the protocol first for clarity
            prompt_dict = prompt.model_dump()
            ordered_prompt_dict = {
                "operational_protocol": prompt_dict.pop("operational_protocol"),
                **prompt_dict
            }
            output_json = json.dumps(ordered_prompt_dict, indent=2)
            
            print("\n--- Simulation Output (AgentPrompt JSON) ---")
            print(output_json)
            print("\n--- Simulation Complete ---")

        except Exception as e:
            print(f"\n--- SIMULATION FAILED ---")
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
