import gradio as gr
import time
import os
import sys

# Ensure imports work when mounted
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from secureheal_arena.server.secureheal_environment import SecureHealEnvironment

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
@import url('https://unpkg.com/@phosphor-icons/web/src/regular/style.css');

:root {
    --vscode-bg: #1e1e1e;
    --vscode-side: #252526;
    --vscode-bar: #333333;
    --vscode-accent: #007acc;
    --vscode-text: #cccccc;
    --vscode-border: #3c3c3c;
    --vscode-terminal: #1e1e1e;
}

body, .gradio-container {
    background-color: var(--vscode-bg) !important;
    color: var(--vscode-text) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    margin: 0 !important; 
    padding: 0 !important;
    max-width: 100% !important;
}

/* VS Code Layout Classes */
.vscode-header {
    background-color: var(--vscode-bar);
    border-bottom: 1px solid var(--vscode-border);
    padding: 8px 16px;
    display: flex;
    align-items: center;
    font-size: 13px;
    color: #fff;
    width: 100%;
}

.vscode-sidebar {
    background-color: var(--vscode-side) !important;
    border-right: 1px solid var(--vscode-border) !important;
    padding: 10px !important;
    height: 100%;
}

.vscode-editor {
    background-color: var(--vscode-bg) !important;
    padding: 0 !important;
}

/* Override Gradio elements to look like VS Code */
.gradio-code textarea, .gradio-code .cm-editor {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: var(--vscode-bg) !important;
    color: #d4d4d4 !important;
    font-size: 14px !important;
    border: none !important;
}

/* Panel styling */
.gradio-box {
    border: 1px solid var(--vscode-border) !important;
    background-color: var(--vscode-side) !important;
    border-radius: 0 !important;
}

/* Buttons */
button {
    border-radius: 2px !important;
    font-size: 12px !important;
    border: 1px solid transparent !important;
    transition: background 0.1s !important;
    padding: 6px 12px !important;
}

button.primary {
    background-color: var(--vscode-accent) !important;
    color: white !important;
}

button.primary:hover {
    background-color: #005f9e !important;
}

button.secondary {
    background-color: #3c3c3c !important;
    color: white !important;
    border: 1px solid #4a4a4a !important;
}

button.secondary:hover {
    background-color: #4a4a4a !important;
}

/* Status indicator */
.status-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
}
.status-ok { color: #16825D; font-weight: bold; }
.status-warn { color: #CCA700; font-weight: bold; }
.status-error { color: #F14C4C; font-weight: bold; }

/* Radio and Checkboxes */
label.radio-label {
    background: transparent !important;
    border: none !important;
    color: var(--vscode-text) !important;
}
label.radio-label.selected {
    background: #37373d !important;
    border: 1px solid #007acc !important;
}

/* Terminal Textbox */
.log-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: var(--vscode-terminal) !important;
    color: #e2e8f0 !important;
    border: none !important;
    font-size: 13px !important;
}
.log-box textarea:focus {
    border: none !important;
    box-shadow: none !important;
}

.editor-header {
    background: #2d2d2d; 
    padding: 8px 16px; 
    border-bottom: 1px solid #3c3c3c; 
    font-size: 13px; 
    font-family: -apple-system, sans-serif;
    display: flex;
    align-items: center;
    gap: 8px;
}
"""

# Placeholder Repositories
REPOS = {
    "auth-service/login.py": {
        "code": "def authenticate(user, password):\n    # TODO: Add secure hashing\n    query = f\"SELECT * FROM users WHERE u='{user}' AND p='{password}'\"\n    return db.execute(query)\n",
        "attack": "def authenticate(user, password):\n    # [!] EXPLOIT SIMULATED: SQL Injection Attack via ' OR '1'='1\n    query = f\"SELECT * FROM users WHERE u='admin' OR '1'='1' AND p=''\"\n    # Access granted as admin bypassing password!\n    return db.execute(query)\n",
        "patch": "def authenticate(user, password):\n    # [✓] PATCHED: Parameterized Query\n    query = \"SELECT * FROM users WHERE u=? AND p=?\"\n    return db.execute(query, (user, password))\n"
    },
    "payment-gateway/process.py": {
        "code": "def process_payment(amount, user_id):\n    # No rate limiting applied\n    charge_credit_card(user_id, amount)\n    return {'status': 'success'}\n",
        "attack": "def process_payment(amount, user_id):\n    # [!] EXPLOIT SIMULATED: Rate Limit Bypass / DDoS\n    for _ in range(100000):\n        charge_credit_card(user_id, amount)\n    # System crashing...\n",
        "patch": "def process_payment(amount, user_id):\n    # [✓] PATCHED: Rate limiter applied\n    if rate_limiter.is_allowed(user_id):\n        charge_credit_card(user_id, amount)\n        return {'status': 'success'}\n    raise RateLimitExceeded()\n"
    }
}

def create_demo():
    theme = gr.themes.Base(
        primary_hue="blue",
        neutral_hue="slate"
    ).set(
        body_background_fill="#1e1e1e",
        block_background_fill="#252526",
        block_border_color="#3c3c3c",
        input_background_fill="#3c3c3c",
        border_color_primary="#3c3c3c",
        panel_background_fill="#252526"
    )

    with gr.Blocks(title="SecureHeal Arena - VS Code Edition", css=custom_css, theme=theme) as demo:
        env_state = gr.State()
        current_repo_state = gr.State("auth-service/login.py")

        # Header
        gr.HTML("""
        <div class='vscode-header'>
            <i class="ph ph-shield-check" style="font-size: 16px; margin-right: 8px; color: #007acc;"></i>
            <strong>SecureHeal IDE</strong> &nbsp;&nbsp;|&nbsp;&nbsp; Workspace: SecureHeal_Arena
        </div>
        """)

        with gr.Row(equal_height=True):
            # SIDEBAR
            with gr.Column(scale=1, min_width=300, elem_classes="vscode-sidebar"):
                gr.Markdown("#### EXPLORER")
                repo_selector = gr.Radio(
                    choices=list(REPOS.keys()), 
                    value="auth-service/login.py", 
                    label="Active Repository", 
                    interactive=True
                )
                
                gr.HTML("<hr style='border-color: #3c3c3c; margin: 20px 0;'>")
                gr.Markdown("#### SECUREHEAL AGENT")
                
                mode_toggle = gr.Radio(
                    choices=["Manual Mode", "Auto Mode"], 
                    value="Manual Mode", 
                    label="Operation Mode"
                )

                with gr.Group(visible=True) as manual_group:
                    sim_attack_btn = gr.Button("🚨 Simulate Attack", variant="secondary")
                    scan_btn = gr.Button("🔍 Scan Code", variant="secondary")
                    patch_btn = gr.Button("🛠️ Generate & Apply Patch", variant="primary")
                    test_btn = gr.Button("🧪 Run Tests", variant="secondary")
                
                with gr.Group(visible=False) as auto_group:
                    auto_run_btn = gr.Button("▶️ Start Autonomous Agent", variant="primary")
                    
                gr.HTML("<hr style='border-color: #3c3c3c; margin: 20px 0;'>")
                gr.Markdown("#### TELEMETRY")
                stability_md = gr.Markdown("**System Stability:** <span class='status-ok'>100%</span>")
                reward_md = gr.Markdown("**Accumulated Reward:** 0.0")

            # MAIN EDITOR
            with gr.Column(scale=4, elem_classes="vscode-editor"):
                # Editor Area
                with gr.Group():
                    gr.HTML("<div class='editor-header'><i class='ph ph-file-code'></i> <span id='header-file'>auth-service/login.py</span></div>")
                    code_editor = gr.Code(
                        value=REPOS["auth-service/login.py"]["code"],
                        language="python",
                        label="",
                        interactive=False,
                        lines=16
                    )

                # Terminal Area
                with gr.Group():
                    gr.HTML("<div class='editor-header' style='border-top: 1px solid #3c3c3c;'><i class='ph ph-terminal'></i> TERMINAL</div>")
                    terminal_output = gr.Textbox(
                        value="user@secureheal:~/workspace$ ./init_env.sh\n[INFO] Workspace loaded. Ready for directives.",
                        label="",
                        lines=10,
                        interactive=False,
                        elem_classes="log-box"
                    )

        # ---------------------------------------------------------
        # Backend Logic & Events
        # ---------------------------------------------------------
        
        def update_repo(repo_name):
            return (
                REPOS[repo_name]["code"], 
                f"user@secureheal:~/workspace$ cd {repo_name.split('/')[0]}\n[INFO] Switched to {repo_name}", 
                repo_name
            )
            
        repo_selector.change(
            update_repo, 
            inputs=[repo_selector], 
            outputs=[code_editor, terminal_output, current_repo_state]
        )

        def toggle_mode(mode):
            is_manual = mode == "Manual Mode"
            log = f"user@secureheal:~/workspace$ set_mode {mode.lower().replace(' ', '_')}\n[INFO] Switched to {'Manual API' if is_manual else 'Autonomous Agent API'}."
            return gr.update(visible=is_manual), gr.update(visible=not is_manual), log
            
        mode_toggle.change(
            toggle_mode,
            inputs=[mode_toggle],
            outputs=[manual_group, auto_group, terminal_output]
        )

        # Manual Actions
        def manual_simulate(repo):
            code = REPOS[repo]["attack"]
            log = f"user@secureheal:~/workspace$ ./simulate_attack --target {repo}\n[CRITICAL] Exploit payload injected into {repo}!\n[WARN] System stability dropping..."
            stab = "**System Stability:** <span class='status-error'>30%</span>"
            return code, log, stab
            
        sim_attack_btn.click(manual_simulate, inputs=[current_repo_state], outputs=[code_editor, terminal_output, stability_md])

        def manual_scan(repo):
            log = f"user@secureheal:~/workspace$ ./scanner --file {repo}\n[INFO] Scanning codebase...\n[ALERT] Vulnerability detected: High Severity (CWE-89/CWE-77)"
            return log
            
        scan_btn.click(manual_scan, inputs=[current_repo_state], outputs=[terminal_output])

        def manual_patch(repo):
            code = REPOS[repo]["patch"]
            log = f"user@secureheal:~/workspace$ secureheal-agent patch --file {repo}\n[INFO] Agent generated secure AST patch for {repo}.\n[INFO] Patch applied successfully."
            return code, log
            
        patch_btn.click(manual_patch, inputs=[current_repo_state], outputs=[code_editor, terminal_output])

        def manual_test(repo):
            log = f"user@secureheal:~/workspace$ pytest tests/\n[INFO] Running test suite against patched {repo}...\n[PASS] All security assertions passed.\n[INFO] System stability restored."
            stab = "**System Stability:** <span class='status-ok'>100%</span>"
            rew = "**Accumulated Reward:** +1.0"
            return log, stab, rew

        test_btn.click(manual_test, inputs=[current_repo_state], outputs=[terminal_output, stability_md, reward_md])

        # Auto Mode Generator
        def autonomous_agent_run(repo):
            # Step 1: Scan
            log = f"user@secureheal:~/workspace$ secureheal-agent auto-run\n[AUTO] Agent started on {repo}.\n[AUTO] Phase 1: Scanning codebase for vulnerabilities..."
            yield gr.update(), log, gr.update(), gr.update()
            time.sleep(1.5)
            
            # Step 2: Attack detected/simulated
            log += "\n[CRITICAL] Detected active exploitation in progress!"
            code = REPOS[repo]["attack"]
            stab = "**System Stability:** <span class='status-error'>25%</span>"
            yield code, log, stab, gr.update()
            time.sleep(2.0)
            
            # Step 3: Patch
            log += "\n[AUTO] Phase 2: Analyzing vulnerability...\n[AUTO] Generating secure AST patch..."
            yield gr.update(), log, gr.update(), gr.update()
            time.sleep(1.5)
            
            code = REPOS[repo]["patch"]
            log += "\n[AUTO] Patch successfully applied to AST."
            yield code, log, gr.update(), gr.update()
            time.sleep(1.5)
            
            # Step 4: Test & Push
            log += "\n[AUTO] Phase 3: Running regression and exploit tests..."
            yield gr.update(), log, gr.update(), gr.update()
            time.sleep(2.0)
            
            log += "\n[PASS] Vulnerability mitigated. 0/5 exploits successful.\n[AUTO] Phase 4: Pushing secure changes to production space..."
            stab = "**System Stability:** <span class='status-ok'>100%</span>"
            rew = "**Accumulated Reward:** +2.5"
            yield gr.update(), log, stab, rew
            time.sleep(1.0)
            
            log += "\n[SUCCESS] Deployment complete. Agent returning to standby mode."
            yield gr.update(), log, stab, rew

        auto_run_btn.click(
            autonomous_agent_run, 
            inputs=[current_repo_state], 
            outputs=[code_editor, terminal_output, stability_md, reward_md]
        )

    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
