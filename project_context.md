# SecureHeal Arena — Project Context & Execution Plan
## Meta PyTorch OpenEnv Hackathon | India 2026

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Hackathon Rules & Judging](#2-hackathon-rules--judging)
3. [Technical Architecture](#3-technical-architecture)
4. [Environment Design](#4-environment-design)
5. [Reward Engineering](#5-reward-engineering)
6. [Training Pipeline](#6-training-pipeline)
7. [Team Roles & Division of Work](#7-team-roles--division-of-work)
8. [Phase-by-Phase Execution Plan](#8-phase-by-phase-execution-plan)
9. [Submission Checklist](#9-submission-checklist)
10. [Anti-Patterns to Avoid](#10-anti-patterns-to-avoid)
11. [Key Resources](#11-key-resources)

---

## 1. Project Overview

### Concept: SecureHeal Arena

A merged RL environment combining **SecureCode Arena X** (cybersecurity vulnerability detection + patching) and **DataHeal Arena** (autonomous system recovery). The agent operates inside a simulated live infrastructure environment where:

- Code is running and being actively attacked
- The agent must **detect vulnerabilities**, **simulate exploits**, **apply patches**, and **monitor system stability** as cascading failures unfold
- All within a single **long-horizon RL episode**

### Why This Wins

| Criterion | Weight | Strength |
|---|---|---|
| Environment Innovation | 40% | Novel domain — live security + infra recovery in one env |
| Storytelling | 30% | Clear before/after: vulnerable system → patched + stable |
| Training Evidence | 20% | RLVR (test execution) provides hard reward curves |
| Reward & Pipeline | 10% | 4 independent reward functions, anti-hack sandbox |

**Projected Score: 9.1 / 10**

### Hackathon Theme Coverage
- **Theme 2**: Long-horizon planning (multi-step patch + recovery episodes)
- **Theme 3.1**: World modeling / professional tasks (real infra tooling simulation)
- **Theme 1**: Multi-agent potential (attacker vs. defender extension)

---

## 2. Hackathon Rules & Judging

### Non-Negotiable Submission Requirements
- [ ] Use **OpenEnv (latest release)** — build on top of framework, do not reinvent
- [ ] Working **training script using Unsloth or HF TRL** — ideally as Colab notebook so judges can re-run
- [ ] **Evidence of actual training** — at minimum, loss + reward plots from a real run
- [ ] **Short writeup** — mini-blog on HuggingFace OR <2 min YouTube video explaining environment and training
- [ ] **Push environment to HuggingFace Space** — discoverable and runnable
- [ ] **README** that: motivates the problem, explains how env works, shows results, links all materials
- [ ] README must link: HF Space URL, video/blog, reward plots (as .png or .jpg committed to repo)
- [ ] Do NOT include large video files in env submission — use URL references

### Judging Criteria (Detailed)

**Innovation (40%)** — Does the environment:
- Teach an LLM something it currently cannot do well?
- Exist in an underexplored RL/LLM training domain?
- Feel like something a researcher could write a paper about?

**Storytelling (30%)** — Can you explain:
1. Problem — what capability gap are you targeting?
2. Environment — what does the agent see, do, and get rewarded for?
3. Results — what changed after training? Show it visually.
4. Why it matters — who cares and why?

**Training Evidence (20%)** — Must show:
- Training loop connected to environment (not static dataset)
- Trained agent vs random/untrained baseline (quantitative + qualitative)
- Reward curves with labeled axes (training step vs. reward)
- Plots committed as .png/.jpg to repo

**Reward & Pipeline (10%)** — Must show:
- Coherent reward logic
- Multiple independent reward functions
- Anti-reward hacking safeguards

---

## 3. Technical Architecture

### Full Stack

```
OpenEnv Environment (FastAPI server)
         ↕  reset() / step() / state()
    SecureHeal Arena Environment
    ┌─────────────────────────────┐
    │  Code Vulnerability Layer   │  ← from SecureCode Arena X
    │  System Stability Layer     │  ← from DataHeal Arena
    │  Sandbox Execution Engine   │
    │  Reward Verifier (4 fns)    │
    └─────────────────────────────┘
         ↕  rollouts + rewards
    TRL GRPOTrainer
         ↕  efficiency layer
    Unsloth (QLoRA)
         ↕
    Base Model: Qwen2.5-3B-Instruct (or Gemma 3-1B for fast iteration)
         ↓
    HuggingFace Space (deployed env)
    HuggingFace Hub (trained model)
```

### OpenEnv Compliance Requirements
- Must extend `Environment` or `MCPEnvironment` base class
- Must implement: `reset()`, `step(action)`, `state()`
- Must have valid `openenv.yaml` manifest
- Client/server separation — clients must NEVER import server internals
- Do NOT use reserved tool names: `reset`, `step`, `state`, `close` for MCP tools

### Environment API Shape

```python
# Observation (what agent sees)
class SecureHealObservation:
    code_snippet: str           # vulnerable code block
    system_logs: list[str]      # sensor/log data
    latency_metrics: dict       # current latency readings
    error_states: list[str]     # active errors
    anomaly_flags: list[str]    # detected anomaly types
    episode_step: int           # current step count
    available_actions: list[str]

# Actions (what agent can do)
ACTIONS = [
    "scan_code",          # from SecureCode — scan for vulnerabilities
    "simulate_attack",    # from SecureCode — test if exploit succeeds
    "apply_patch",        # from SecureCode — apply a code fix
    "run_tests",          # from SecureCode — execute test suite
    "restart_service",    # from DataHeal — restart a failing service
    "clean_data",         # from DataHeal — clear corrupted data
    "reallocate_resources", # from DataHeal — shift compute resources
    "classify_issue",     # from DataHeal — tag anomaly type
]

# State (environment internal)
class SecureHealState:
    vulnerability_present: bool
    exploit_possible: bool
    patch_applied: bool
    test_pass_rate: float        # 0.0 to 1.0 — RLVR signal
    system_stability: float      # 0.0 to 1.0 — heuristic signal
    cascading_failures: list     # active failure chain
    latency_delta: float         # latency improvement
    step_count: int
    done: bool
```

---

## 4. Environment Design

### Episode Flow

```
reset()
  → inject vulnerability into code
  → inject stochastic anomaly into system state
  → return initial observation

step(action) loop:
  Step 1: Agent observes code + system logs
  Step 2: Agent scans code (scan_code)
  Step 3: Agent simulates exploit (simulate_attack) → sandbox executes
  Step 4: Agent applies patch (apply_patch)
  Step 5: Agent validates fix (run_tests) → RLVR reward computed
  Step 6: Agent monitors system (classify_issue)
  Step 7: Agent stabilizes services (restart_service / reallocate_resources)
  Step 8: Environment checks cascading failures resolved
  → episode ends when: system stable + tests passing OR max_steps reached

reward() → computed at each step with 4 independent functions
```

### Curriculum Learning (CRITICAL — Start Simple)

**Level 1 (Start here):**
- Single vulnerability type (e.g., SQL injection)
- Single anomaly type (e.g., memory spike)
- Short episode (8 steps max)
- Deterministic injection

**Level 2 (After non-zero reward achieved):**
- Two vulnerability types
- Two anomaly types
- Medium episode (15 steps)
- Light stochasticity

**Level 3 (After stable training):**
- Multiple vulnerability classes
- Cascading failures enabled
- Long episodes (25 steps)
- Full stochastic anomaly injection

### Stochastic Anomaly Injection (DataHeal contribution)
- Random seed controls anomaly type and severity at `reset()`
- Cascading failures: patching triggers secondary anomaly 30% of time
- Latency degradation: starts at baseline, worsens if agent delays

### Sandbox Execution (SecureCode contribution)
- All code execution isolated (no globals, no file system access)
- Timeout: 5 seconds per `simulate_attack` or `run_tests` call
- Forbidden patterns: editing timers, caching results, modifying protected state

---

## 5. Reward Engineering

### Four Independent Reward Functions

| # | Signal | Source | Type | Weight |
|---|---|---|---|---|
| R1 | Exploit blocked | SecureCode | RLVR — binary verifiable | High |
| R2 | Test suite pass rate | SecureCode | RLVR — continuous (0.0–1.0) | High |
| R3 | System stability restored | DataHeal | Semi-verifiable (latency delta) | Medium |
| R4 | Cascading failures halted | DataHeal | Heuristic (anomaly count) | Medium |

### Reward Formula Per Step

```python
def compute_reward(state, action_result):
    r1 = 1.0 if state.exploit_blocked else -0.5   # binary RLVR
    r2 = state.test_pass_rate                       # continuous RLVR (0.0–1.0)
    r3 = max(0, state.stability_delta)              # semi-verifiable
    r4 = 1.0 if len(state.cascading_failures) == 0 else 0.0  # heuristic

    # Anti-cheat penalties
    penalty = 0.0
    if action_result.timeout:      penalty -= 1.0
    if action_result.forbidden_op: penalty -= 2.0
    if action_result.format_error: penalty -= 0.2

    return (0.35 * r1) + (0.35 * r2) + (0.20 * r3) + (0.10 * r4) + penalty
```

### Anti-Reward Hacking Safeguards
- All code executed in isolated sandbox (no file system, no network)
- Hard timeout on every action (5 seconds)
- Forbidden operations list checked before reward computed
- Protected state locked — agent cannot mutate `test_pass_rate` directly
- Periodic manual inspection of generations during training (every 50 steps)
- Terminate and rollback if reward rises but task quality drops

### Reward Design Principles (from docs)
- Start with sparse binary reward (R1 only) at Level 1
- Add R2 when model consistently gets non-zero R1
- Add R3 + R4 only when R1 + R2 are stable
- Never reward format compliance above correctness
- Reward outcomes first, process constraints second

---

## 6. Training Pipeline

### Recommended Stack
- **Model**: Qwen2.5-3B-Instruct (fast iteration) → scale to 7B if compute allows
- **Trainer**: TRL GRPOTrainer
- **Efficiency**: Unsloth (QLoRA — 4-bit, do NOT naively upcast to 16-bit before merge)
- **Environment**: OpenEnv (FastAPI server on HF Spaces)
- **Tracking**: Weights & Biases (link specific run in README)

### GRPO Training Config (Starter)

```python
from trl import GRPOTrainer, GRPOConfig
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-3B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)

training_args = GRPOConfig(
    output_dir="secureheal-grpo",
    per_device_train_batch_size=4,
    num_generations=8,          # rollouts per prompt
    max_new_tokens=512,
    learning_rate=5e-6,
    num_train_epochs=3,
    logging_steps=10,
    save_steps=100,
    report_to="wandb",
)
```

### Saving Models Correctly (CRITICAL)
```python
# CORRECT: use Unsloth's save method
model.save_pretrained_merged("secureheal-final", tokenizer, save_method="merged_16bit")

# WRONG — damages model quality:
# model = model.to(torch.float16)  # DO NOT DO THIS
# model.merge_and_unload()          # DO NOT DO THIS ALONE
```

### Rollout Function (connect env to trainer)

```python
import openenv

env_client = openenv.from_hub("your-hf-username/secureheal-arena")

def rollout_fn(prompt_batch):
    rewards = []
    for prompt in prompt_batch:
        obs = env_client.reset(seed=random.randint(0, 9999))
        done = False
        episode_reward = 0
        while not done:
            action = model.generate(format_prompt(obs, prompt))
            obs, reward, done, info = env_client.step(action)
            episode_reward += reward
        rewards.append(episode_reward)
    return rewards
```

### What to Monitor During Training
- `reward/mean` — overall trend (should rise)
- `reward/r1_exploit_blocked` — primary RLVR signal (watch this most)
- `reward/r2_test_pass_rate` — secondary RLVR signal
- `reward/timeout_rate` — should stay near zero (if rising = reward hacking)
- `rollout/length` — average episode length
- Sample 5–10 raw generations every 50 steps — check for suspicious shortcuts

---

## 7. Team Roles & Division of Work

> **Team Size: 4 members** — 3 technical + 1 demo/presentation

---

### Member 1 — Environment Engineer
**Primary: Build and deploy the OpenEnv environment**

**Owns:**
- `environment/server.py` — `reset()`, `step()`, `state()` logic
- `environment/actions.py` — action dataclasses and validation
- `environment/observations.py` — observation dataclasses
- `environment/sandbox.py` — isolated code execution engine
- `openenv.yaml` — manifest file
- Local and HF Spaces deployment

**Must deliver by Phase 3:**
- Working `reset()` + `step()` loop locally (Level 1 only)
- Deployed to HF Spaces with `/health` endpoint responding
- Timeout and sandbox isolation working

**Must deliver by Phase 6:**
- All 3 curriculum levels implemented
- Stochastic anomaly injection working
- Cascading failure logic working

---

### Member 2 — Reward Engineer
**Primary: Build verifiers and reward functions**

**Owns:**
- `rewards/verifier.py` — R1 (exploit check) + R2 (test suite execution)
- `rewards/stability.py` — R3 (latency delta) + R4 (cascading failure count)
- `rewards/anti_hack.py` — forbidden operations checker, timeout enforcer
- `rewards/rubric.py` — OpenEnv Rubric integration (composable rubrics)
- Test suite for reward functions themselves

**Must deliver by Phase 3:**
- R1 verifier working end-to-end (exploit blocked = 1.0, not blocked = -0.5)
- Anti-cheat sandbox checks passing

**Must deliver by Phase 6:**
- All 4 reward functions live and tested
- Reward hacking adversarial test cases written and passing
- Reward pipeline connected to environment `step()` output

**Key rule: Try to break your own reward before the model does.**

---

### Member 3 — Training Engineer
**Primary: Set up TRL + Unsloth, run experiments, track metrics**

**Owns:**
- `training/train.py` — GRPOTrainer config + rollout function
- `training/colab_notebook.ipynb` — runnable Colab notebook for judges
- `training/plots/` — reward curves (.png committed to repo)
- WandB run configuration and logging
- Baseline (untrained model) evaluation

**Must deliver by Phase 5:**
- Tiny TRL + Unsloth experiment running (even 10 steps)
- Reward curve output (even flat — proves loop works)
- Baseline model rollout recorded

**Must deliver by Phase 8:**
- Full training run with meaningful reward improvement
- Reward plots labeled: x-axis = training step, y-axis = reward
- Baseline vs trained comparison on same axes
- Colab notebook runnable end-to-end by a stranger

---

### Member 4 — Demo & Presentation
**Primary: README, HF blog, video, pitch deck**

**Owns:**
- `README.md` — full submission document
- HuggingFace blog post (mini, <500 words)
- YouTube video (<2 minutes)
- Slide deck for live pitch
- HF Space demo UI (simple interface for judges to try env)

**Must deliver by Phase 4:**
- Draft README with problem motivation and env explanation
- HF Space live with basic demo interface

**Must deliver by Phase 9:**
- Final README with reward plots embedded
- Video recorded and uploaded (URL in README)
- Blog post published on HF
- Pitch deck ready (problem → env → results → why it matters)

**Demo format (judge-facing):**
1. Show baseline model failing (vulnerable code not patched)
2. Show reward verifier output
3. Show trained model succeeding (code patched, system stable)
4. Show reward curve (before → after)
5. One sentence: "Here's how we prevented reward hacking"

---

## 8. Phase-by-Phase Execution Plan

> Hackathon is Day 1 (25 Apr) + Day 2 (26 Apr). Submission deadline: **5:00 PM Day 2**.

---

### PHASE 1 — Task Scoping (Day 1, First 1 hour)
**All members together**

- [ ] Finalize Level 1 environment scope: one vulnerability type (SQL injection), one anomaly type (memory spike), 8-step episodes
- [ ] Agree on action names (avoid reserved: `reset`, `step`, `state`, `close`)
- [ ] Set up shared repo, WandB project, HF org
- [ ] Claim HF credits ($30/person) — do this immediately
- [ ] Set up Cursor AI credits — do this immediately
- [ ] Member 3 installs TRL + Unsloth locally, confirms GPU access

**Exit criteria:** Everyone knows exactly what they're building. Repo exists.

---

### PHASE 2 — Environment Skeleton (Day 1, Hours 1–3)
**Member 1 leads | Member 2 supports**

- [ ] `openenv init secureheal-arena` — bootstrap scaffold
- [ ] Implement `reset()` — inject one hardcoded SQL injection vuln + memory anomaly
- [ ] Implement `step()` — action routing (just `scan_code` and `run_tests` for now)
- [ ] Implement `state()` — return basic observation dict
- [ ] Write `openenv.yaml` manifest
- [ ] Run loop locally: `reset() → step("scan_code") → step("run_tests")`

**Member 2 parallel:** Write the R1 verifier (exploit check) in isolation — does not need env yet.

**Exit criteria:** `env.reset()` and `env.step()` return data without crashing locally.

---

### PHASE 3 — Reward Verifier (Day 1, Hours 3–5)
**Member 2 leads | Member 1 integrates**

- [ ] R1 working: sandbox executes exploit attempt, returns 1.0 if blocked
- [ ] R2 working: test suite runs, returns pass_rate (0.0–1.0)
- [ ] Anti-hack checks: timeout enforcer + forbidden ops list
- [ ] Wire R1 + R2 into `step()` return value
- [ ] Write 3 adversarial test cases for reward hacking (try to game R1 manually)
- [ ] Deploy environment skeleton to HF Spaces (`openenv push`)

**Member 3 parallel:** Set up TRL GRPOConfig and rollout function scaffold — does not need full env yet.

**Member 4 parallel:** Draft README sections: Problem, Environment, Team.

**Exit criteria:** `env.step("run_tests")` returns a reward score. HF Space is live.

---

### PHASE 4 — First Training Loop (Day 1, Hours 5–7)
**Member 3 leads | All support**

- [ ] Connect rollout function to HF Spaces env endpoint
- [ ] Run tiny GRPO experiment: 10 steps, batch size 2, just to confirm loop works
- [ ] Confirm reward values appearing in WandB
- [ ] Record baseline (untrained) model rollout output — save as text file
- [ ] Member 4: publish basic HF Space demo page (just shows env API)

**Exit criteria:** Training loop runs without crashing. WandB shows reward values (even if flat/random).

---

### PHASE 5 — Reward Hacking Inspection (Day 1, Evening)
**Member 2 leads | Member 3 inspects generations**

- [ ] Sample 10 generations from tiny training run — read them manually
- [ ] Check for: formatting tricks, trivial patches, test manipulation
- [ ] Add any missing anti-hack constraints found during inspection
- [ ] Member 1: implement Level 2 environment (second vuln type + stochasticity)
- [ ] Midnight snacks break — mandatory

**Exit criteria:** No obvious reward hacking patterns observed. Level 2 env working locally.

---

### PHASE 6 — Full Environment + Rewards (Day 2, Morning)
**Members 1 & 2 together**

- [ ] R3 working: latency delta computed and returned in step
- [ ] R4 working: cascading failure count tracked and rewarded
- [ ] All 4 reward functions integrated and tested
- [ ] Level 3 environment (cascading failures, stochastic injection) working
- [ ] OpenEnv Rubric system used for composable reward scoring
- [ ] Final deploy to HF Spaces with full environment

**Member 3 parallel:** Run 30-minute training run — get real reward curves.

**Member 4 parallel:** Record 2-minute demo video of environment step-through (no trained model needed yet).

**Exit criteria:** All 4 rewards live. Real training run producing meaningful curves.

---

### PHASE 7 — Training Scale-Up (Day 2, Hours 2–4)
**Member 3 leads**

- [ ] Run full GRPO training (2–3 hours on HF Jobs T4 GPU)
- [ ] Monitor: reward/mean, r1_exploit_blocked, timeout_rate
- [ ] Save model correctly using Unsloth merged save path
- [ ] Test inference on saved model immediately
- [ ] Generate before/after comparison: baseline vs trained on same episode

**Members 1 & 2 parallel:** Polish environment code, add comments, clean up API.

**Member 4 parallel:** Draft HF blog post, write pitch deck.

**Exit criteria:** Trained model demonstrably better than baseline on at least R1 or R2.

---

### PHASE 8 — Demo & README (Day 2, Hours 4–5)
**Member 4 leads | All contribute**

- [ ] Embed reward plots in README (labeled axes, .png committed to repo)
- [ ] Add WandB run link to README
- [ ] Finalize README: Problem → Env → Results → Why It Matters
- [ ] Publish HF blog post
- [ ] Upload demo video to YouTube — add URL to README
- [ ] Add all links to README: HF Space, model, video, blog, plots
- [ ] Check: does `openenv.yaml` pass validation?

**Exit criteria:** README readable in 3–5 minutes. All links working.

---

### PHASE 9 — Submission (Day 2, Final Hour before 5 PM)
**All members**

- [ ] Final commit — no changes after submission deadline
- [ ] Submit HF Space URL as required
- [ ] Verify judges can: open Space, call `reset()`, call `step()`, see rewards
- [ ] Verify Colab notebook runs end-to-end (test in fresh Colab session)
- [ ] Verify plots are committed as .png to repo (not only in Colab cell)
- [ ] Double-check: no big video files in HF Hub repo (use URL links)
- [ ] Final README review against submission checklist

---

## 9. Submission Checklist

### Must Have (Non-Negotiable)
- [ ] OpenEnv latest release used
- [ ] `reset()`, `step()`, `state()` implemented and working
- [ ] Valid `openenv.yaml` manifest
- [ ] HF Space deployed and running
- [ ] Colab training notebook (runnable by judges)
- [ ] Loss + reward plots (.png in repo, labeled axes)
- [ ] README with: problem, env explanation, results, all links
- [ ] Mini-blog on HF OR YouTube video (<2 min)
- [ ] HF Space URL submitted before deadline

### Should Have (Score Boosters)
- [ ] Baseline vs trained comparison on same plot
- [ ] WandB run link in README
- [ ] 4 independent reward functions (not just 1)
- [ ] Anti-reward-hacking section in README
- [ ] Before/after behavior example (text output from baseline vs trained)
- [ ] Multi-agent attacker/defender mode (even as a description of future work)

### README Must Answer
1. What is the capability gap being targeted?
2. What does the agent observe, do, and get rewarded for?
3. What changed after training? (show plots + text examples)
4. Who would care about this? Why does it matter?

---

## 10. Anti-Patterns to Avoid

| Mistake | Why It Hurts | Fix |
|---|---|---|
| Single reward function | Trivially hackable | Use 4 independent reward functions |
| Training before env is stable | Bugs look like model failure | Debug env manually first |
| Only watching average reward | Reward can rise while quality drops | Also watch r1_exploit_blocked + sample generations |
| Task too hard at start | Model never gets reward → learning stalls | Start with Level 1 curriculum |
| Naively upcasting QLoRA to 16-bit | Damages model quality | Use Unsloth merged save path |
| Big video files in HF Hub | Disqualifies submission | Use YouTube URL in README |
| Not testing Colab notebook fresh | Judges can't re-run it | Test in a fresh Colab session before submitting |
| Plots only in Colab cell | Reviewers can't see them | Commit as .png to repo, embed in README |
| LLM-as-judge as only verifier | Model games the judge | Use hard execution checks as primary signal |

---

## 11. Key Resources

### OpenEnv
- GitHub: https://github.com/meta-pytorch/OpenEnv
- Docs: https://meta-pytorch.org/OpenEnv/
- TRL Integration: https://huggingface.co/docs/trl/en/openenv
- HF Spaces: https://huggingface.co/openenv/spaces

### Training Examples
- Unsloth Qwen2.5 GRPO (starter): https://github.com/meta-pytorch/OpenEnv/blob/main/tutorial/examples/unsloth_2048.ipynb
- TRL Wordle GRPO: https://github.com/huggingface/trl/blob/main/examples/notebooks/openenv_wordle_grpo.ipynb
- TRL Sudoku GRPO: https://github.com/huggingface/trl/blob/main/examples/notebooks/openenv_sudoku_grpo.ipynb

### YouTube (Recommended Order)
1. Mega Lecture (recommended): https://www.youtube.com/watch?v=Jew4lhAiqnw
2. Why OpenEnv (8:02–15:05): https://www.youtube.com/watch?v=1jU05MlENOI&t=482s
3. Building Your Own (43:45–50:20): https://www.youtube.com/watch?v=1jU05MlENOI&t=2625s
4. Training + TRL (1:53:20–2:07:12): https://www.youtube.com/watch?v=Jew4lhAiqnw&t=6800s

### RL Learning
- RL Lecture Chapters: https://openenv-india-apr-2026.lovable.app/
- Reward hacking (DeepMind): https://www.deepmind.com/blog/specification-gaming-the-flip-side-of-ai-ingenuity
- Reward hacking (Lilian Weng): https://lilianweng.github.io/posts/2024-11-28-reward-hacking/

### Research Papers
- RLVR: https://arxiv.org/abs/2408.10215
- RLVE (adaptive environments): https://arxiv.org/abs/2601.19100

### Compute Credits
- HF Credits ($30/person): https://huggingface.co/coupons/claim/hf-openenv-community
- HF Jobs (GPU access): https://huggingface.co/settings/jobs
- Scaler Dashboard (Cursor AI credits): https://tinyurl.com/sclr-openenv-dashboard

### Mentors (Discord)
- Sanyam Bhutani — Partner Engineer, Meta
- Yash Khare — Partner Engineer, Meta
- Ben Burtenshaw — Community Education AI, HuggingFace
- Aashay Sachdeva — Founding Team, Sarvam

---

*Last updated: April 25, 2026 | SecureHeal Arena | Meta PyTorch OpenEnv Hackathon India 2026*
