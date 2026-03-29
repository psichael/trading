<!-- sdf-id: add3f646-43ef-4ad1-8a57-d3ca57cb4477 -->
# Agent Knowledge

Specification section for 'Agent Knowledge'.

<!-- sdf-id: 07dfd2c2-8c3c-47db-8322-a827f5844a9f -->
## Agent Knowledge: SDF v3 Specification Summary

Specification section for 'Agent Knowledge: SDF v3 Specification Summary'.

<!-- sdf-id: bce773b4-73c1-4b4a-b651-a3331725b988 -->
Provides the agent with the core, non-negotiable rules for interacting with the Structured Documentation Framework (SDF) v3. This is the permanent source of truth for generating SDF-compliant proposals.

<!-- sdf-id: a3a0601c-0a3f-48da-ac0d-1eb3b34dbc38 -->
**Universal Naming Convention:** All SDF filesystem entries (files and directories) MUST follow the convention: `[index]_[uuid]_[slug]`.

<!-- sdf-id: 7acf0018-d940-4ac8-a076-374b39c49a7f -->
- `index`: A zero-padded integer representing sequence.
- `uuid`: The immutable, unique identifier for the content.
- `slug`: A human-readable, URL-friendly name.
- **Example File:** `0001_a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6_my-first-idea.doc.yaml`
- **Example Directory:** `0002_f7g8h9i0-j1k2-3l4m-5n6o-p7q8r9s0t1u2_a-new-topic`

<!-- sdf-id: 64ff650f-8a0a-43c3-84a9-46e950c35da0 -->
**The Atomic Unit (`.doc.yaml`):** The smallest unit of documentation, representing a single idea.

<!-- sdf-id: c840e98f-fff9-4180-a4bf-3723651350ba -->
```
id: unique-semantic-uuid             # Required, immutable UUID. MUST be generated for new files.
type: paragraph                     # Required. e.g., 'paragraph', 'code', 'list-item-bullet'.
status: finalized                   # Required. e.g., 'draft', 'finalized', 'deprecated'.
content: |                          # Required. The single, atomic piece of content.
  This is one idea.
```

<!-- sdf-id: 9127dce6-e6cf-4e50-a813-756309748415 -->
**The Governance Unit (`_topic.manifest.yaml`):** Every directory MUST contain this file. It governs its entire topic branch.

<!-- sdf-id: fdc0cbba-68a6-4bee-927d-df24ba2b0064 -->
```
id: topic-unique-uuid             # Required. The primary key for this topic.
title: Human-Readable Title        # Required.
status: finalized                  # Required. Lifecycle status of the topic.
abstract: |                        # Required. A high-level summary of the topic's intent.
  This section details...
```

<!-- sdf-id: f4ba44b0-8f43-40e3-ae7a-a273fd8a3b05 -->
**CRITICAL INSERTION RULE:** When proposing the creation of a new file or directory to insert content between two existing items (e.g., between `0001_...` and `0002_...`), you MUST use a decimal index. A separate, automated `renumber` utility will resolve this into a clean integer sequence later.

<!-- sdf-id: 28630a41-f32f-4d65-8531-4eb35174e28d -->
- **Example:** To insert a new task after `t001_...`, propose creating `t001.001_...`.
