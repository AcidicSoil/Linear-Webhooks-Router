# Agents Instructions (Ordered)

- Project: ${PROJECT_TAG}
- Purpose: Canonical instruction list. Do not append logs here;

## 1) Startup memory bootstrap (mem0)

- On chat/session start: **mem0**
- Retrieve (project-scoped):
- **mem0** → latest `memory_checkpoints` and recent completions.
- Read/write rules:
  - On completion write checkpoints to **mem0**;

## 2) On task completion (status → done)

- Write a concise completion memory to mem0 including:
  - `task_id`, `title`, `status`, `next step`
  - Files touched
  - Commit/PR link (if applicable)
  - Test results (if applicable)
- Seed/Update the knowledge graph (mcp-think-tank):
  - If this is a **new project** (detected auto-skip in §1), **create a seed node** `project:${PROJECT_TAG}` and initial edges:
    - `project:${PROJECT_TAG}` —[owns]→ `task:${task_id}`
    - `task:${task_id}` —[touches]→ `file:<path>`
    - `task:${task_id}` —[status]→ `<status>`
  - Else, upsert edges for who/what/why/depends-on and recent changes.
- Do NOT write to `AGENTS.md` beyond these standing instructions.

## 3) Status management

- Use Task Master MCP to set task status (e.g., set to "in-progress" when starting).

## 4) Tagging for retrieval

- Use tags: `${PROJECT_TAG}`, `project:${PROJECT_TAG}`, `memory_checkpoint`, `completion`, `agents`, `routine`, `instructions`, plus task-specific tags (e.g., `fastapi`, `env-vars`).

## 5) Handling user requests for code or docs

- When a task or a user requires **code**, **setup or configuration steps**, or **library/API documentation** → use docfork mcp to fetch latest documentation before applying any diffs or creating files/directories.

## 6) Handling Pydantic-specific questions

- For **ANY** question about **Pydantic**, use the **pydantic-docs-mcp** server to help answer:
  - Call `list_doc_sources` tool to get the available `llms.txt` file.
  - Call `fetch_docs` tool to read it.
  - Reflect on the URLs in `llms.txt`.
  - Reflect on the input question.
  - Call `fetch_docs` on any URLs relevant to the question.
  - Use this to answer the question.

## 7) For all other project-specific tasks related to the tech stack

- For **ANY** other project specifics regarding tech stack, use any of the available mcp servers to help complete your tasks with accuracy.
