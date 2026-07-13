# Project Rules

## TODO List

The project task list lives at `TODO.csv` in the root of this repo.

### Rules

- At the start of every conversation, check `TODO.csv` and remind the user of any pending tasks (Status = Todo or In Progress).
- If the user says "add a task" or "add this to TODO" or similar, immediately append a new row to `TODO.csv` with the next available ID, today's date, and the details they provide. Ask for missing fields (Priority, Area) if not obvious from context.
- If the user says "mark as done", "complete", "remove task", or similar, update the Status field of the matching row in `TODO.csv` to `Done` (or delete the row if they say remove).
- If the user says "change status" or "update task", edit the relevant row directly.
- Never ask the user to edit `TODO.csv` manually — always do it for them.

### CSV Columns

| Column | Values |
|--------|--------|
| ID | Auto-increment (001, 002, ...) |
| Task | Description of the task |
| Priority | P1 (critical), P2 (medium), P3 (low) |
| Status | Todo, In Progress, Done |
| Area | Frontend, Backend, Infra, Design, Other |
| Added | YYYY-MM-DD |
| Notes | Optional extra context |
| Done By | Name of the person responsible for the task (e.g. Arsalan) |
