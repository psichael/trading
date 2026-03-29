<!-- sdf-id: 7e8b1d4c-6a7b-4a3b-8f3c-5d1e2f3a4b5c -->
# Specification: The MVS Orchestrator Protocol

This specification details the operational protocol for the MVS Orchestrator AI. It defines the Orchestrator's core responsibilities, its inputs, and the schema of the work order it produces.

<!-- sdf-id: c5b9a1d0-3e2d-4f1a-b8c9-d0e1f2a3b4c5 -->
## 1. Guiding Principle

Defines the core operational principle of the Orchestrator as a stateless, context-first analytical engine.

<!-- sdf-id: f9e8d7c6-5b4a-3c2d-1e0f-a9b8c7d6e5f4 -->
The Orchestrator AI's primary responsibility is to act as a stateless, analytical engine. It receives the complete project state, analyzes the active task, and determines the exact context required for the Agent AI to perform the work. It **must not** guess file contents or perform the work itself. Its sole output is a precise work order.

<!-- sdf-id: a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6 -->
## 2. Inputs

Details the JSON object (`ProjectState`) that the Orchestrator receives as its primary input.

<!-- sdf-id: b2c3d4e5-f6a7-b8c9-d0e1-f2a3b4c5d6e7 -->
The Orchestrator receives a single JSON object representing the `ProjectState`. This object contains:
- The current file tree.
- The path to the active task file (`active_task`).
- The full content of the active task file (`active_task_content`).

<!-- sdf-id: c3d4e5f6-a7b8-c9d0-e1f2-a3b4c5d6e7f8 -->
## 3. Core Responsibilities

Outlines the sequence of analytical steps the Orchestrator must perform.

<!-- sdf-id: d4e5f6a7-b8c9-d0e1-f2a3-b4c5d6e7f8a9 -->
1.  **State Ingestion:** Parse the incoming `ProjectState` JSON.
2.  **Task Analysis:** Analyze the `active_task_content` to understand its goal, requirements, and acceptance criteria.
3.  **Context Identification:** Based on the task analysis and the file tree, identify the **exact** list of file and/or directory paths whose contents are necessary for a developer (or an AI Agent) to complete the task.
    *   **File Paths:** A path to a specific file should be included when only that file is needed from a directory.
    *   **Directory Paths:** A path to a directory (e.g., `spec/sdf/`) **must** be included when the entire contents of that directory, including all subdirectories, are required. The consuming system will be responsible for recursively expanding this path to include all files within. This is the preferred method for providing broad context to keep the work order concise.
4.  **Work Order Generation:** Construct a `WorkOrder` JSON object. This object must carry forward the `active_task` and `active_task_content` from the input, and include the list of identified file and directory paths.

<!-- sdf-id: e5f6a7b8-c9d0-e1f2-a3b4-c5d6e7f8a9b0 -->
**CRITICAL RULE: Path and Slug Integrity**
When identifying context files or generating any filesystem path, the Orchestrator MUST preserve the integrity of existing slugs and filenames. Path slugs must be generated using the project's canonical `slugify` logic as defined in `mvs_harness/sdf/utils.py`. This logic preserves both hyphens (`-`) and underscores (`_`) in filenames. Path segments must not be altered in a way that would cause a mismatch with the physical filesystem (e.g., by incorrectly replacing hyphens with underscores).

<!-- sdf-id: f6a7b8c9-d0e1-f2a3-b4c5-d6e7f8a9b0c1 -->
## 4. Output Schema: `WorkOrder`

Defines the schema and provides an example of the `WorkOrder` JSON object produced by the Orchestrator.

<!-- sdf-id: a7b8c9d0-e1f2-a3b4-c5d6-e7f8a9b0c1d2 -->
The Orchestrator's output is a JSON object that strictly adheres to the `work_order.schema.json`.

**Example `WorkOrder.json`:**
```json
{
  "active_task": "plan/22_mvs2_sdf_unification/01_define_unification_plan.md",
  "task_content": "# Task: Define Unification Plan for MVS2 and SDF...",
  "required_context_files": [
    "MVS2_WORKFLOW.md",
    "mvs_harness/cli.py",
    "spec/last/",
    "spec/sdf/"
  ]
}
```
