<!-- sdf-id: fa6dd35c-4c20-43e1-afbd-0e6bbea7093d -->
# Sdf V3

Specification section for 'Sdf V3'.

<!-- sdf-id: cf705c67-e832-45f8-8689-2df9f7ec45a1 -->
## 1. Introduction

Specification section for '1. Introduction'.

<!-- sdf-id: 5cdc78e2-b1fe-4db4-abe1-f2a8f01f9d0e -->
Provides a high-level overview of SDF v3.0, its purpose, and its core value proposition for the DDI-O ecosystem.

<!-- sdf-id: 8092ab49-9b63-4955-9689-2636329e4577 -->
This document proposes a paradigm shift in how the DDI-O framework represents and interacts with documentation. We move from traditional, monolithic Markdown files to a granular, semantically-structured representation called the Structured Documentation Framework (SDF). In this model, the filesystem itself is used to physically represent the documentation's semantic tree, with individual ideas stored as small, atomic YAML files.

<!-- sdf-id: 4b43ce60-245f-4eb2-ae00-fdc9fae4de9f -->
This AI-first architecture is designed for maximum efficiency, consistency, and verifiability. It enables DDI-O agents to navigate, comprehend, and modify the project's knowledge base with surgical precision, operating under the principle of minimum necessary context. The SDF transforms documentation from a passive artifact into an active, queryable knowledge graph, making it a first-class component of the DDI-O ecosystem. Human interaction is maintained through a build process that assembles the atomic fragments into familiar, readable documents for review and consumption.

<!-- sdf-id: 43e5b03b-a085-4021-8733-25349b9201ee -->
## 2. Guiding Principles

Specification section for '2. Guiding Principles'.

<!-- sdf-id: b8b71a68-9eca-420c-a129-d352fa000535 -->
Defines the core philosophical principles that underpin the SDF v3.0 architecture.

<!-- sdf-id: 688d4248-19eb-4aa3-9c37-1d3303431486 -->
- **AI-First, Not AI-Only:** The primary consumer is the DDI-O agent. The representation is optimized for machine traversal, querying, and manipulation. Humans act as supervisors.
- **Atomic Idea Units:** Each file contains one and only one indivisible semantic unit.
- **Structure as Semantics:** The physical directory hierarchy represents the logical structure of the knowledge.
- **UUID as Identity:** An item's identity is a unique, immutable UUID, completely decoupled from its filename or position in a sequence. This allows for robust cross-referencing and transactional safety during reordering operations.
- **Explicit Governance:** High-level intent, ownership, and architectural relationships are explicitly declared in machine-readable manifest files.

<!-- sdf-id: da965e51-8d30-4738-8c90-88d590010383 -->
## 3. Core Architecture

Specification section for '3. Core Architecture'.

<!-- sdf-id: 16404fbd-b158-461a-bfd2-9711c2174c10 -->
Describes the fundamental components of the SDF, including the atomic unit, the governance manifest, and the universal ordering mechanism.

<!-- sdf-id: 3fd27e6b-f11b-4319-bd20-c21386736c27 -->
### 3.1. The Atomic Unit: The .doc.yaml File

Specification section for '3.1. The Atomic Unit: The .doc.yaml File'.

<!-- sdf-id: 766be0cb-aead-467b-b4e6-1aa42a3f6a9f -->
Details the schema and purpose of the .doc.yaml file, the smallest semantic node in the SDF.

<!-- sdf-id: 9b187497-f94a-4e03-9aee-616a8465152c -->
The smallest unit of documentation is a single semantic node, stored in a file with a .doc.yaml extension.

<!-- sdf-id: 1c214477-c88f-49b3-a1c0-2f20325466c7 -->
```
id: unique-semantic-uuid             # Required, immutable UUID for cross-referencing.
type: paragraph                     # Required. e.g., 'heading-1', 'paragraph', 'list-item-bullet'.
status: finalized                   # Required. e.g., 'draft', 'finalized', 'deprecated'.
tags: [api, security]               # Optional. Keywords for non-hierarchical discovery.
references:                         # Optional. Links to other fragments by their UUIDs.
  - doc_id: some-other-fragment-uuid
content: |                          # Required. The single, atomic piece of content in Markdown.
  This is one idea.
```

<!-- sdf-id: 62e70ffc-9f8b-472a-902e-f18274ee484f -->
### 3.2. The Governance Unit: The _topic.manifest.yaml File

Specification section for '3.2. The Governance Unit: The _topic.manifest.yaml File'.

<!-- sdf-id: cac6cd19-9add-4f4e-80b4-63d905845a8a -->
Details the schema and purpose of the _topic.manifest.yaml file, the authoritative summary and governance document for each topic branch.

<!-- sdf-id: 7106858e-c048-4fca-ad48-61c37eb8b26d -->
Every directory must contain a `_topic.manifest.yaml` file. This file serves as the authoritative, machine-readable summary and governance document for its entire topic branch, acting as the primary entry point for an agent assessing context.

<!-- sdf-id: 53bc6de6-db9c-4d30-ae3c-8d02a45d3cef -->
```
id: topic-unique-uuid             # Required. The primary key for this topic.
title: Human-Readable Title        # Required.
version: "1.0"                     # Optional. Semantic version of this topic section.
status: finalized                  # Required. Lifecycle status of the topic.
owner: architect-agent@1.0         # Optional. The primary responsible agent/role.
abstract: |                        # Required. A high-level summary of the topic's intent.
  This section details...
tags: [high-level, concept]        # Optional. Topic-level keywords.
relations:                         # Optional. High-level links to OTHER topics by UUID.
  - type: depends_on
    topic_id: other-topic-uuid
```

<!-- sdf-id: cfcffabd-12ce-4b18-a6bf-c34061f69ab3 -->
### 3.3. The Universal Ordering Mechanism

Specification section for '3.3. The Universal Ordering Mechanism'.

<!-- sdf-id: 9095097d-818c-4f91-a539-c8c205108ffe -->
Explains the file naming convention that enables efficient, transactionally safe reordering of content.

<!-- sdf-id: 3f6fcd5a-a2d7-47bd-bc93-73f7bf781b62 -->
All filesystem entries (files and directories) follow a universal naming convention that encodes order and identity: `[index]_[uuid]_[slug].[type].yaml` for files, and `[index]_[uuid]_[slug]` for directories.

<!-- sdf-id: 4384ce3b-b2c0-40f0-95c0-d505485294b7 -->
- `index`: A zero-padded integer representing the item's sequence. For insertions, a decimal may be used temporarily (e.g., `0001.001`).
- `uuid`: The immutable, unique identifier for the content.
- `slug`: A human-readable, URL-friendly name derived from the title.

<!-- sdf-id: b2e95f2b-a123-47be-a5ba-6bccdc4255d0 -->
**Benefit:** This convention decouples an item's identity (its UUID) from its position (its index). An agent can insert new content by creating a file with a decimal index. A separate, deterministic `renumber` utility is then responsible for resolving these decimals into a clean integer sequence in a single, atomic transaction. This prevents the cascading renames required by linked-list-on-filesystem models and simplifies agent logic.

<!-- sdf-id: cca02251-192c-4ec7-b437-fa7de2305314 -->
## 4. The Operational Workflow

Specification section for '4. The Operational Workflow'.

<!-- sdf-id: b2f7bb3a-7ea7-4564-a48d-ded1e24704b9 -->
Outlines the typical modification cycle for an agent to modify the SDF knowledge base.

<!-- sdf-id: 1cfc66c5-cd3c-459b-aee5-fb8806ede4e2 -->
1. **Context Retrieval (CIS):** An agent queries the CIS, which navigates the tree by reading `_topic.manifest.yaml` files to gain efficient context, retrieving specific `.doc.yaml` fragments only when necessary.
2. **Proposal Generation (Agent):** The agent generates a declarative JSON proposal listing the desired atomic filesystem operations (create, update, delete). For insertions, it MUST use a decimal index.
3. **Pre-Flight Verification (CIS):** The proposal is sent to the CIS for deterministic validation against SDF rules.
4. **Integration (Orchestrator):** The validated proposal is sent to the Orchestrator. The Orchestrator executes the filesystem operations and then invokes the `renumber` utility on any modified directories to finalize the change as a single atomic transaction.

<!-- sdf-id: 3320935d-9944-4dcf-813e-3599cb4e0900 -->
## 5. Validation Rules

Specification section for '5. Validation Rules'.

<!-- sdf-id: e93038d3-b3a5-45de-acc0-1090b0460e4c -->
Defines the set of enforceable rules that ensure the SDF knowledge base remains efficient, reliable, and consistent.

<!-- sdf-id: abc0d53e-797c-40ca-9441-141f454112b6 -->
These rules are enforced by the `ddio docs validate` tool to ensure the knowledge base remains efficient and reliable.

<!-- sdf-id: acb4d5c6-e9c0-4b67-af33-0cfa857f52c4 -->
- **Structure & Naming:** All files and directories must conform to the `[index]_[uuid]_[slug]` naming convention. Every directory must contain a `_topic.manifest.yaml` file.
- **UUID Integrity:** All `id` fields within YAML files must be valid UUIDs. UUIDs must be unique across the entire knowledge base.
- **Content & Abstraction:** Every `.doc.yaml` must contain one indivisible idea. Information must flow from general to specific as one descends the tree.
- **Manifest Governance:** A manifest `abstract` must accurately summarize its direct children. Its `relations` can only link to other topic UUIDs.

<!-- sdf-id: 0ce4580c-539f-4e27-b289-5cdfcd22559c -->
## 6. Core Tooling

Specification section for '6. Core Tooling'.

<!-- sdf-id: e81edd70-3cd9-419b-be92-05db029fed2d -->
Lists and describes the essential CLI commands for working with the SDF.

<!-- sdf-id: 6a02e388-3b8d-42cb-8819-d1947956ba59 -->
A suite of command-line tools is provided to interact with the SDF knowledge base.

<!-- sdf-id: a845d20b-41d8-49bc-87c1-ab60da0ebb3b -->
- **`ddio docs assemble`**: Traverses the tree and renders fragments into human-readable documents (e.g., Markdown) in a `build/` directory.
- **`ddio docs validate`**: The linter and governance tool. It enforces all rules defined in Section 5.
- **`ddio docs diff`**: The Semantic Diff viewer. It uses UUIDs to track items, providing a human-readable summary of logical changes (e.g., reporting `REORDERED` instead of a raw file rename).
- **`ddio docs renumber [path]`**: A deterministic utility that scans a directory for decimal indexes and renumbers all items into a clean, sequential series.
