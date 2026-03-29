# MVS Harness CLI

This directory contains the Minimum Viable System (MVS) harness, a command-line tool that automates the execution and governance steps of the DDI-O development cycle.

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)
- A powerful LLM capable of following complex protocol instructions.

### Installation & Setup

1.  **Navigate to this directory:**
    ```sh
    cd mvs_cli
    ```

2.  **Install dependencies using Poetry:**
    ```sh
    poetry install
    ```

3.  **Activate the virtual environment:**
    ```sh
    poetry shell
    ```
    *Note: All subsequent `ddio` commands must be run from the **project root directory** while within this Poetry shell.*

## ⚙️ The DDI-O MVS2 Workflow Cycle

The project operates in atomic, state-driven cycles managed by the `ddio` CLI. The state of the current work cycle is governed by the presence or absence of a `.ddio/context_manifest.json` file in the project root.

### Step 1: Prepare the AI Prompt (Orchestration Turn)

This command analyzes the repository state and produces the complete context for the AI.

*   **Action:** From the project root, run the cycle start command.
    ```sh
    ddio cycle start
    ```
*   **Result:** A file named `project_state.json` is created in the root directory. The harness automatically determines whether to start an **execution cycle** (if `.ddio/context_manifest.json` exists) or a **planning cycle** (if it does not).

### Step 2: AI Generation and Proposal Refinement (Agent Turn)

*   **Action:**
    1.  Provide the contents of `project_state.json` to the AI.
    2.  Review the AI's proposal. Provide feedback (`REFINE`) until satisfied, or approve with `CONFIRM`.
    3.  Save the AI's final JSON output into `temp_proposal.json`.

### Step 3: Execute the Atomic Commit (Execution Turn)

This command validates the proposal, performs all file operations, manages the state for the next cycle, and creates the final git commit.

*   **Action:** Execute the proposal from the project root.
    ```sh
    ddio cycle execute --proposal temp_proposal.json
    ```
*   **Result:** The repository state is atomically updated. The harness will create or delete the `.ddio/context_manifest.json` file to correctly prepare for the next cycle.

## 📚 Documentation

This project's documentation, including the project plan and specifications, is written using the Structured Documentation Framework (SDF). To generate human-readable Markdown files from the SDF sources, run the build script:

```sh
# Make sure the script is executable first: chmod +x scripts/build_docs.sh
./scripts/build_docs.sh
```

This will compile all content from the `plan/` and `spec/` directories into the `build/docs/` directory.
