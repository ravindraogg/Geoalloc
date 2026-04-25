# SecureHeal Arena: 2-Minute Demo Video Script

## 0:00 - 0:15 | The Problem (Visual: Split screen - clean code vs vulnerable code)
**Narrator:** "Modern infrastructure moves fast, but vulnerabilities move faster. When an exploit hits a live system, SREs and Security teams scramble. But what if an AI agent could detect the vulnerability, test the exploit, write the patch, and stabilize the infrastructure—all autonomously?"

## 0:15 - 0:40 | The Environment (Visual: Gradio UI Screen Recording)
**Narrator:** "Welcome to SecureHeal Arena. We built an OpenEnv environment that combines a live code sandbox with system infrastructure telemetry. 
*Action on screen:* Mouse clicking through the Gradio UI 'Mission Control' panel.
**Narrator:** "The agent observes application code, system stability metrics, and live logs. It can scan code, simulate attacks in a secure sandbox, apply patches, and even reallocate server resources to handle cascading failures."

## 0:40 - 1:10 | Baseline vs. Trained Agent (Visual: Terminal / UI split)
**Narrator:** "Here is an untrained base model. It sees a memory spike, panics, and outputs invalid formatting or hallucinates tools. The system crashes."
*Action on screen:* UI shows 'System Stability' dropping to 0%, red text "Cascading Failure".
**Narrator:** "But after using TRL and Unsloth for GRPO training, our agent learned a multi-step recovery policy. Watch."
*Action on screen:* Trained agent executes `scan_code` -> `simulate_attack` -> `apply_patch` -> `run_tests` -> `restart_service`. 
**Narrator:** "It patches the SQL injection, runs the test suite, and restarts the degraded service. Stability is restored."

## 1:10 - 1:40 | The Reward Design (Visual: 4 Reward Curves Plot)
**Narrator:** "We achieved this using four independent reward functions: Exploit blocked (RLVR verifiable), Test suite pass rate, System stability delta, and Cascading failure resolution.
*Action on screen:* Highlight the WandB training plots showing rewards going up.
**Narrator:** "To prevent reward hacking, all execution happens in an isolated sandbox with hard timeouts and forbidden operation checks."

## 1:40 - 2:00 | Conclusion (Visual: SecureHeal Logo & Meta/HF Logos)
**Narrator:** "SecureHeal Arena proves that we can train LLMs for long-horizon, multi-domain recovery tasks. Try the live demo in our Hugging Face Space, or check out the code on GitHub. Thanks to Meta, PyTorch, and Hugging Face for the OpenEnv Hackathon!"
