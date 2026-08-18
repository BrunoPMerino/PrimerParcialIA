# Backend — Emergency Control

Python API that exposes `POST /api/solve`.

The backend now uses a real **Uniform Cost Search (UCS)** agent to generate a valid and minimum-cost plan for the scenario.

The search implementation includes:

- Graph Search.
- Canonical state representation.
- Battery dominance pruning.
- Relevance filtering from the goal.
- Restricted `DROP` generation.
- Internal `DROP + PICKUP` optimization.
- Scenario preprocessing to reduce repeated work during search.

The scenario remains the source of truth. The agent does not modify `scenario.json` to make the problem easier.

See `project/design.md` for the complete problem formulation and design decisions.

## Run

```bash
cd project/backend
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --app-dir src --port 8000
```

Or from `backend/src`:

```bash
cd project/backend/src
uvicorn main:app --reload --port 8000
```

The API includes:

```text
GET /api/health
GET /api/scenario
POST /api/solve
```

## Tests

```bash
cd project/backend
python tests/test_agent.py
```

The tests validate:

- equivalent states;
- relevant state information;
- UCS selection by minimum cost;
- scenarios with no solution;
- alternative routes;
- frontend operation contract;
- execution of the generated plan using `simulator.py`.

If all tests pass, the final output should include:

```text
TODAS LAS PRUEBAS PASARON
```
