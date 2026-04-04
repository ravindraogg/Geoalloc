# GeoAllocEnv: Strategic Resource Allocation under Geopolitical Constraints

GeoAllocEnv is a deterministic, real-world simulation environment built to the **OpenEnv** specification. It challenges an AI agent to allocate limited oil resources across multiple countries while balancing unmet demand, stability, and geopolitical tension.

## 🌍 Strategic Objective
The agent acts as a resource administrator, distributing oil to satisfy country demands. However, every allocation potentially increases **geopolitical tension** depending on the target country's enemy network. If global tension reaches 100%, the simulation terminates immediately.

## 🚀 Key Features
- **OpenEnv Specification Compliant**: Implements `step()`, `reset()`, and `state()` with strict Pydantic v2 validation.
- **Geopolitical Tension Mechanics**: Tension increases by `0.15 * (allocation_ratio) * number_of_enemies`, requiring strategic planning.
- **Deterministic Evaluation**: Guaranteed reproducibility for automated grading.
- **Three Task Levels**: 
  - **Easy**: 2 countries, no enemies. Basic allocation.
  - **Medium**: 3 countries, 1 enemy pair. Balancing trade-offs.
  - **Hard**: 5 countries, dense enemy network, severe oil scarcity. Highly sensitive to tension.
- **FastAPI-powered Server**: Exposes the environment as a web service using `openenv-core`.

---

## 🛠️ Project Structure
```text
geoalloc-env/
├── server/            # OpenEnv server implementation
│   ├── app.py         # FastAPI entry point
│   └── geoalloc_environment.py  # Core environment logic
├── env/               # Local environment and task definitions
│   ├── tasks/         # Task-level generators (Easy, Medium, Hard)
│   └── graders/       # Normalized scoring logic [0.0 - 1.0]
├── models.py          # Root-level OpenEnv base models
├── openenv.yaml       # Deployment configuration for Hugging Face
├── pyproject.toml     # Modern Python project metadata (uv-compatible)
├── uv.lock            # Resolved dependency lockfile
├── inference.py       # LLM Agent inference and evaluation runner
└── Dockerfile         # Official OpenEnv multi-stage build template
```

---

## 📖 How to Run

### 1. Local Testing (Inference Runner)
This will run the built-in LLM agent against the three task levels.
```powershell
$env:API_BASE_URL = "https://your-api-base-url"
$env:MODEL_NAME = "your-model-name"
$env:OPENAI_API_KEY = "your-key"
python inference.py
```

### 2. Start the OpenEnv Server (Step 4)
This starts the FastAPI server as specified in the OpenEnv framework.
```powershell
# Install dependencies and start
uv run server
```

### 3. Deploy (Step 5)
Push the environment to your Hugging Face Space.
```powershell
openenv push --repo-id your-username/geoalloc-env
```

---

## 🛡️ Strategic Allocation Rules for Agents
Agents should follow these rules for maximum score:
1.  **Priority**: Allocate to countries with 0 enemies first (Safe Countries).
2.  **Batching**: Split large allocations into smaller batches for countries with high enemy counts.
3.  **Tension Cap**: Monitor `global_tension`. If it exceeds 0.7, use `no_op` steps to evaluate wait-and-see periods.
4.  **Normalization**: The environment reward is normalized from `[0, 1]`. Aim for `score >= 0.5` for a passing task.

---

## 🎓 Metadata
- **Spec Version**: 1
- **Target Deadline**: 8 April 2026, 11:59 PM IST
- **Framework**: OpenEnv-Core 0.2.x
