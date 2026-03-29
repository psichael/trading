<!-- sdf-id: c6b33ad6-3839-4628-87af-a0366a1b2486 -->
# Plan Sdf

Specification section for 'Plan Sdf'.

<!-- sdf-id: 6a844cc3-fe41-498d-8444-54c1c25144ce -->
## 1. The Epic Manifest (`_topic.manifest.yaml`)

Specification section for '1. The Epic Manifest (`_topic.manifest.yaml`)'.

<!-- sdf-id: 8ae5bae7-f06f-4d7a-8775-ed8fa2310f4b -->
Defines the schema for an "epic," which corresponds to a directory in the plan. The epic is governed by a standard SDF `_topic.manifest.yaml` file.

<!-- sdf-id: 18102be3-d94e-4090-b635-96ba97c68391 -->
An epic is a container for a collection of related tasks, represented as a directory. The epic's metadata is defined in a `_topic.manifest.yaml` file within that directory, leveraging the standard SDF governance schema.

<!-- sdf-id: 591d2340-9743-4cac-90a7-dcfbb5a5e198 -->
```
id: epic-unique-identifier        # Required. A stable, unique ID for the epic.
title: Human-Readable Epic Title   # Required.
status: in-progress                # Required. The lifecycle status of the epic.
                                   # e.g., 'pending', 'in-progress', 'completed', 'blocked'.
owner: agent-role@1.0              # Optional. The primary responsible role.
abstract: |                        # Required. A high-level summary of the epic's goal.
  This epic covers the work to...
relations:                         # Optional. Defines dependencies on OTHER epics.
  - type: depends_on
    topic_id: another-epic-id
```

<!-- sdf-id: a306b1c0-d984-458a-8bb7-b42355727e90 -->
## 2. The Task Document (`.doc.yaml`)

Specification section for '2. The Task Document (`.doc.yaml`)'.

<!-- sdf-id: 87bacb84-845c-4a05-a22c-d7de5b9e9169 -->
Defines the schema for a "task," which is an atomic unit of work represented by a standard SDF `.doc.yaml` file with a specific type.

<!-- sdf-id: 3b8f45f0-276d-49b4-9cab-5abfe517ffde -->
A task is the smallest unit of work, represented by a `.doc.yaml` file. It follows the SDF atomic unit schema with specific conventions for planning.

<!-- sdf-id: b2594751-b8ce-44b2-af6d-bcc7157c34ca -->
```
id: task-unique-identifier         # Required, stable ID for cross-referencing.
type: task                          # Required. MUST be 'task'.
status: ready                       # Required. The lifecycle status of the task.
                                    # e.g., 'ready', 'active', 'completed', 'blocked'.
dependencies:                       # Optional. A list of task `id`s that must be completed first.
  - another-task-id
content: |                          # Required. The task description in Markdown.
  **Goal:** ...
  **Acceptance Criteria:**
  1. ...
```

<!-- sdf-id: cc2f989b-45ad-4d9e-b028-0e29aa2e5887 -->
## 3. Example Directory Structure

Specification section for '3. Example Directory Structure'.

<!-- sdf-id: 31d42982-f48b-4184-bc7a-db74be8c0782 -->
Provides a concrete example of a project plan represented as an SDF directory tree, demonstrating the relationship between epics and tasks.

<!-- sdf-id: 6b2a6288-ef69-47a0-84ed-45c5f7affb30 -->
This example shows how an epic with several sequential tasks would be represented on the filesystem, following the SDF universal ordering convention (`[predecessor_id]_[my_id]_[name]`).

<!-- sdf-id: 5d5e9b7f-f477-4f69-9115-3c6761543861 -->
```
plan/
└── 0000_e22a_mvs2-sdf-unification/    # Epic Directory
    ├── _topic.manifest.yaml            # Epic Manifest (id: mvs2-sdf-unification)
    |
    ├── 0000_t4f1_define-plan.doc.yaml  # Task 1 (id: define-plan-sdf)
    |
    ├── t4f1_t8b3_update-harness.doc.yaml # Task 2 (id: update-harness-read-sdf)
    |
    └── t8b3_tc9e_migrate-plan.doc.yaml   # Task 3 (id: migrate-plan-to-sdf)
```
