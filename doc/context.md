# Challenge

A productivity startup is building a voice-first to-do list. The frontend already captures speech with the Web Speech API and turns it into text. Your job is to build the backend that receives those transcriptions and turns them into real task actions.

The frontend talks to a single entry point:

## `POST /instruction`

- Receives a plain-text transcription
- Calls the Groq API (model such as `llama3-8b-8192`) to extract the user's intent and parameters
- Must return a JSON object that tells the frontend which internal endpoint to call next and with what arguments

## Internal task endpoints

All data is stored in a module-level list (no database, no files). Each task is a dictionary with `id`, `title`, and `done`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tasks` | Return the full list of tasks |
| `POST` | `/tasks` | Create a new task. Required: `title`. Optional: `done` (defaults to `false`) |
| `PUT` | `/tasks/<int:task_id>` | Replace a task entirely |
| `PATCH` | `/tasks/<int:task_id>` | Mark a task as done or update its title |
| `DELETE` | `/tasks/<int:task_id>` | Delete a task by ID |

## Groq integration

The system prompt must instruct the LLM to **never return free text** — only a JSON object in this shape:

```json
{
  "endpoint": "/tasks",
  "method": "POST",
  "params": { "title": "Buy groceries" }
}
```

## Goal

Demonstrate a full voice-to-action flow. For example, if a user says "add buy groceries to my list," the backend should process that through the Groq-powered `/instruction` endpoint and ultimately result in a new task appearing in the list.

---

## What You Need to Do

### 1. Setup

- [ ] Create a virtual environment and install **FastAPI**, **Uvicorn**, and the **Groq Python SDK**.
- [ ] Store your Groq API key in a `.env` file — never commit it to the repository.
- [ ] Configure CORS so the frontend can communicate with your API.

### 2. In-memory storage

- [ ] Declare a module-level list called `tasks` to serve as your data store.
- [ ] Each task must have `id` (integer), `title` (string), and `done` (boolean, default `false`).

### 3. Task endpoints

- [ ] `GET /tasks` — returns all tasks as a JSON array.
- [ ] `POST /tasks` — creates a task from the request body and appends it to the list; returns the created task with its assigned ID.
- [ ] `PUT /tasks/<task_id>` — replaces the full task object for the given ID.
- [ ] `PATCH /tasks/<task_id>` — partially updates a task (title and/or done status).
- [ ] `DELETE /tasks/<task_id>` — removes the task with the given ID; returns a confirmation message.

### 4. Instruction endpoint

- [ ] `POST /instruction` — receives a JSON body with a `transcription` field (plain text).
- [ ] Calls the Groq API with an appropriate system prompt that forces the LLM to respond only with a structured JSON object indicating `endpoint`, `method`, and `params`.
- [ ] Returns that JSON directly to the frontend.

### 5. End-to-end wiring

- [ ] Using the response from `/instruction`, the frontend calls the correct task endpoint automatically — verify this works for at least: create, list, update, and delete actions spoken aloud.

### Important

- Do not use a database. All data must live in a Python list in memory. The list resets every time the server restarts — that is expected behavior for this project.
- The `/instruction` endpoint must not contain hardcoded intent-matching logic (no `if "add" in text`). All routing decisions must come from the LLM response.

---

## What Needs to be evaluated

Use this checklist to evaluate the project after implementation:

- [x] All five task endpoints (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) are implemented and return appropriate HTTP status codes.
- [x] Each endpoint returns a properly serialized JSON response.
- [x] The `POST /instruction` endpoint calls the Groq API and returns the structured routing JSON. *(Verified endpoint is live and invokes Groq; full LLM JSON success requires your real `GROQ_API_KEY` in `.env`.)*
- [ ] The system prompt is well-crafted: the LLM consistently returns valid JSON in the required format across different voice inputs. *(Pending live Groq key — prompt uses JSON-only instructions + `response_format=json_object`.)*
- [x] CORS is configured so the provided frontend can communicate with the API without errors.
- [x] The `.env` file is listed in `.gitignore` and the API key is never exposed in the code.
- [x] The in-memory list is correctly managed: IDs are unique and items are properly added, updated, and removed.

**Note:** The frontend is provided and will not be evaluated. You are not expected to modify it.
