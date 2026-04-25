import gradio as gr
import json
import pandas as pd
from secureheal_arena.server.secureheal_environment import SecureHealEnvironment

# ────────────────────────────────────────────────────────────────────────
# Gradio Frontend for SecureHeal Arena
# ────────────────────────────────────────────────────────────────────────

# Custom CSS for a professional, "hacker/cybersecurity" yet clean aesthetic
custom_css = """
.container { max-width: 1200px; margin: auto; }
.header-text { text-align: center; font-weight: bold; color: #2D3748; }
.status-good { color: #38A169; font-weight: bold; }
.status-bad { color: #E53E3E; font-weight: bold; }
.status-warn { color: #D69E2E; font-weight: bold; }
.log-box { background-color: #1A202C; color: #A0AEC0; font-family: monospace; padding: 10px; border-radius: 5px; }
.code-box { border-left: 4px solid #3182CE; }
"""

def create_demo():
    # We will use Gradio's State to persist the environment across interactions
    # However, since SecureHealEnvironment is a complex object, we can store it in state
    # if it's picklable, or keep a global dictionary of sessions if needed. 
    # For a simple demo, a global instance is easiest, but State is better for multiple users.
    
    with gr.Blocks(title="🛡️ SecureHeal Arena Dashboard", css=custom_css, theme=gr.themes.Default(primary_hue="blue", secondary_hue="indigo")) as demo:
        
        # State to hold the environment instance
        env_state = gr.State()

        gr.Markdown(
            """
            # 🛡️ SecureHeal Arena: Autonomous System Recovery
            Welcome to the interactive dashboard for the **Meta OpenEnv Hackathon**.
            This interface allows you to act as the AI Agent, exploring the environment's capabilities to detect vulnerabilities, patch code, and stabilize infrastructure.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                curriculum_level = gr.Radio(choices=[1, 2, 3], value=1, label="Curriculum Level", info="1: Easy, 2: Medium, 3: Hard")
                reset_btn = gr.Button("🔄 Initialize / Reset Environment", variant="primary")
                
                gr.Markdown("### 🛠️ Agent Actions")
                with gr.Accordion("Security Actions", open=True):
                    scan_btn = gr.Button("🔍 Scan Code")
                    sim_btn = gr.Button("🧨 Simulate Attack")
                    patch_input = gr.Code(language="python", label="Patch Code")
                    patch_btn = gr.Button("🛠️ Apply Patch")
                    test_btn = gr.Button("🧪 Run Tests")
                
                with gr.Accordion("Infrastructure Actions", open=True):
                    service_input = gr.Dropdown(choices=["auth-service", "api-gateway", "db-layer", "payment-service"], label="Service Name", value="auth-service")
                    restart_btn = gr.Button("🔄 Restart Service")
                    realloc_btn = gr.Button("⚖️ Reallocate Resources")
                    clean_btn = gr.Button("🧹 Clean Data")
                    classify_input = gr.Textbox(label="Anomaly Classification", placeholder="e.g., MEMORY_SPIKE")
                    classify_btn = gr.Button("🏷️ Classify Issue")
                    
            with gr.Column(scale=2):
                gr.Markdown("### 📊 System Telemetry")
                with gr.Row():
                    stability_gauge = gr.Number(label="System Stability (0-1)", value=1.0, interactive=False)
                    latency_gauge = gr.Number(label="Current Latency (ms)", value=50.0, interactive=False)
                    test_pass_gauge = gr.Number(label="Test Pass Rate", value=0.0, interactive=False)
                    reward_gauge = gr.Number(label="Total Reward", value=0.0, interactive=False)
                
                with gr.Row():
                    services_df = gr.Dataframe(headers=["Service", "Status"], label="Services Status")
                    alerts_box = gr.Textbox(label="Active Alerts", lines=3, interactive=False)
                
                gr.Markdown("### 💻 Application Source Code")
                code_display = gr.Code(language="python", interactive=False, label="Current Code")
                
                gr.Markdown("### 📜 Environment Logs")
                action_result_display = gr.Textbox(label="Last Action Result", lines=3, interactive=False)
                logs_display = gr.Textbox(label="System Logs", lines=6, interactive=False, elem_classes="log-box")

        # --- Backend Logic ---

        def update_ui_from_state(env: SecureHealEnvironment, last_result: str = ""):
            if not env:
                return [gr.update() for _ in range(9)]
            
            state = env.state
            
            # Format services for dataframe
            services_data = [[k, v] for k, v in state.services_status.items()]
            
            # Format alerts
            alerts = []
            if state.vulnerability_present: alerts.append(f"VULNERABILITY: {state.vulnerability_type}")
            if state.anomaly_type: alerts.append(f"ANOMALY: {state.anomaly_type}")
            for cf in state.cascading_failures: alerts.append(f"CASCADING: {cf}")
            if state.data_corrupted: alerts.append("CORRUPTION: Data integrity check failed.")
            alerts_text = "\n".join(alerts) if alerts else "✅ System Healthy"
            
            # Format logs
            logs = env._build_system_logs()
            logs_text = "\n".join(logs)
            
            return [
                state.system_stability,
                state.latency_current,
                state.test_pass_rate,
                state.total_reward,
                services_data,
                alerts_text,
                env._current_code,
                last_result,
                logs_text
            ]

        def reset_env(level):
            env = SecureHealEnvironment(curriculum_level=level)
            obs = env.reset()
            msg = obs.metadata.get("action_result", "Environment initialized.")
            updates = update_ui_from_state(env, msg)
            return [env] + updates

        def perform_action(env, action_name, **kwargs):
            if not env:
                return [env] + [gr.update()] * 9
            
            # Dispatch to internal handlers
            if action_name == "scan_code": res = env._handle_scan_code()
            elif action_name == "simulate_attack": res = env._handle_simulate_attack()
            elif action_name == "apply_patch": res = env._handle_apply_patch(kwargs.get("patch_code", ""))
            elif action_name == "run_tests": res = env._handle_run_tests()
            elif action_name == "restart_service": res = env._handle_restart_service(kwargs.get("service", ""))
            elif action_name == "reallocate_resources": res = env._handle_reallocate_resources()
            elif action_name == "clean_data": res = env._handle_clean_data()
            elif action_name == "classify_issue": res = env._handle_classify_issue(kwargs.get("classification", ""))
            else: res = {"result": "Unknown action"}
            
            updates = update_ui_from_state(env, res.get("result", ""))
            return [env] + updates

        # Event Listeners
        outputs = [env_state, stability_gauge, latency_gauge, test_pass_gauge, reward_gauge, services_df, alerts_box, code_display, action_result_display, logs_display]
        
        reset_btn.click(reset_env, inputs=[curriculum_level], outputs=outputs)
        
        scan_btn.click(lambda e: perform_action(e, "scan_code"), inputs=[env_state], outputs=outputs)
        sim_btn.click(lambda e: perform_action(e, "simulate_attack"), inputs=[env_state], outputs=outputs)
        patch_btn.click(lambda e, p: perform_action(e, "apply_patch", patch_code=p), inputs=[env_state, patch_input], outputs=outputs)
        test_btn.click(lambda e: perform_action(e, "run_tests"), inputs=[env_state], outputs=outputs)
        
        restart_btn.click(lambda e, s: perform_action(e, "restart_service", service=s), inputs=[env_state, service_input], outputs=outputs)
        realloc_btn.click(lambda e: perform_action(e, "reallocate_resources"), inputs=[env_state], outputs=outputs)
        clean_btn.click(lambda e: perform_action(e, "clean_data"), inputs=[env_state], outputs=outputs)
        classify_btn.click(lambda e, c: perform_action(e, "classify_issue", classification=c), inputs=[env_state, classify_input], outputs=outputs)

    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
