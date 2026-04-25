import gradio as gr
import json
import pandas as pd
from secureheal_arena.server.secureheal_environment import SecureHealEnvironment

# ────────────────────────────────────────────────────────────────────────
# Modern Gradio Frontend for SecureHeal Arena
# ────────────────────────────────────────────────────────────────────────

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

body, .gradio-container {
    font-family: 'Inter', sans-serif !important;
    background: radial-gradient(circle at top right, #1a202c, #0f172a, #000000);
    color: #e2e8f0;
}

/* Glassmorphism Panels */
.glass-panel {
    background: rgba(30, 41, 59, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    padding: 20px;
}

/* Glowing text for numbers */
.glow-text {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(to right, #00f2fe, #4facfe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(79, 172, 254, 0.5);
    margin: 0;
}

.glow-red { background: linear-gradient(to right, #ff0844, #ffb199); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.glow-green { background: linear-gradient(to right, #0ba360, #3cba92); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

/* Buttons */
button.primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 20px -10px rgba(118, 75, 162, 0.8) !important;
}

/* Code and Logs */
.log-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #0d1117 !important;
    color: #58a6ff !important;
    border: 1px solid #30363d !important;
}
"""

def create_demo():
    with gr.Blocks(title="SecureHeal Arena") as demo:
        env_state = gr.State()

        with gr.Column(elem_classes="glass-panel"):
            gr.HTML("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="font-size: 3rem; margin-bottom: 0; background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🛡️ SecureHeal Arena</h1>
                <p style="font-size: 1.2rem; color: #94a3b8; margin-top: 5px;">Autonomous System Recovery & Vulnerability Patching Command Center</p>
            </div>
            """)

        with gr.Row():
            # --- LEFT COLUMN: CONTROLS ---
            with gr.Column(scale=1, elem_classes="glass-panel"):
                gr.Markdown("### 🎛️ Mission Control")
                with gr.Row():
                    curriculum_level = gr.Radio(choices=[1, 2, 3], value=1, label="Curriculum Level", container=False)
                    reset_btn = gr.Button("🚀 Initialize Scenario", variant="primary")
                
                gr.Markdown("### 🤖 Agent Action Deck", elem_classes="mt-4")
                with gr.Accordion("🔒 Security Operations", open=True):
                    with gr.Row():
                        scan_btn = gr.Button("🔍 Scan Code")
                        sim_btn = gr.Button("🧨 Simulate Attack")
                    patch_input = gr.Code(language="python", label="Patch Code")
                    with gr.Row():
                        patch_btn = gr.Button("🛠️ Apply Patch", variant="primary")
                        test_btn = gr.Button("🧪 Run Tests")
                
                with gr.Accordion("⚡ Infrastructure Operations", open=False):
                    service_input = gr.Dropdown(choices=["auth-service", "api-gateway", "db-layer", "payment-service"], label="Target Service", value="auth-service")
                    with gr.Row():
                        restart_btn = gr.Button("🔄 Restart Service")
                        realloc_btn = gr.Button("⚖️ Reallocate Resources")
                    clean_btn = gr.Button("🧹 Clean Data Cache")
                    classify_input = gr.Textbox(label="Anomaly Classification", placeholder="e.g., MEMORY_SPIKE")
                    classify_btn = gr.Button("🏷️ Classify Issue")
                    
            # --- RIGHT COLUMN: TELEMETRY & LOGS ---
            with gr.Column(scale=2):
                with gr.Row(elem_classes="glass-panel"):
                    # HTML Telemetry Cards
                    stability_html = gr.HTML(value="<div style='text-align:center'><p style='color:#94a3b8;margin:0'>System Stability</p><h2 class='glow-text'>--</h2></div>")
                    latency_html = gr.HTML(value="<div style='text-align:center'><p style='color:#94a3b8;margin:0'>Current Latency</p><h2 class='glow-text'>--</h2></div>")
                    reward_html = gr.HTML(value="<div style='text-align:center'><p style='color:#94a3b8;margin:0'>Total Reward</p><h2 class='glow-text'>--</h2></div>")
                
                with gr.Row(elem_classes="glass-panel"):
                    with gr.Column():
                        services_df = gr.Dataframe(headers=["Microservice", "Health Status"], label="Infrastructure Status", interactive=False)
                    with gr.Column():
                        alerts_box = gr.Textbox(label="🚨 Active Threat Alerts", lines=4, interactive=False)
                
                with gr.Column(elem_classes="glass-panel"):
                    code_display = gr.Code(language="python", interactive=False, label="Application Source Code")
                
                with gr.Row(elem_classes="glass-panel"):
                    with gr.Column():
                        action_result_display = gr.Textbox(label="Agent Action Result", lines=6, interactive=False)
                    with gr.Column():
                        logs_display = gr.Textbox(label="System Kernel Logs", lines=6, interactive=False, elem_classes="log-box")

        # --- Backend Logic ---

        def update_ui_from_state(env: SecureHealEnvironment, last_result: str = ""):
            if not env:
                return [gr.update() for _ in range(9)]
            
            state = env.state
            
            # Formatted HTML gauges
            stab_color = "glow-green" if state.system_stability > 0.8 else ("glow-red" if state.system_stability < 0.4 else "glow-text")
            stab_html = f"<div style='text-align:center'><p style='color:#94a3b8;margin:0'>System Stability</p><h2 class='{stab_color}'>{state.system_stability:.0%}</h2></div>"
            
            lat_color = "glow-red" if state.latency_current > 150 else "glow-text"
            lat_html = f"<div style='text-align:center'><p style='color:#94a3b8;margin:0'>Current Latency</p><h2 class='{lat_color}'>{state.latency_current:.0f}ms</h2></div>"
            
            rew_html = f"<div style='text-align:center'><p style='color:#94a3b8;margin:0'>Total Reward</p><h2 class='glow-text'>{state.total_reward:.2f}</h2></div>"
            
            services_data = [[k, "🟢 Healthy" if v=="up" else ("🔴 Down" if v=="down" else "🟡 Degraded")] for k, v in state.services_status.items()]
            
            alerts = []
            if state.vulnerability_present: alerts.append(f"[!] Vulnerability: {state.vulnerability_type}")
            if state.anomaly_type: alerts.append(f"[!] Anomaly: {state.anomaly_type}")
            for cf in state.cascading_failures: alerts.append(f"[!] Cascading: {cf}")
            if state.data_corrupted: alerts.append("[!] Data Corruption Detected")
            alerts_text = "\n".join(alerts) if alerts else "✅ All Systems Nominal"
            
            logs = env._build_system_logs()
            logs_text = "\n".join(logs)
            
            return [stab_html, lat_html, rew_html, services_data, alerts_text, env._current_code, last_result, logs_text]

        def reset_env(level):
            env = SecureHealEnvironment(curriculum_level=level)
            obs = env.reset()
            msg = obs.metadata.get("action_result", "Environment initialized. Awaiting agent directives.")
            updates = update_ui_from_state(env, msg)
            return [env] + updates

        def perform_action(env, action_name, **kwargs):
            if not env:
                return [env] + [gr.update()] * 8
            
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
        outputs = [env_state, stability_html, latency_html, reward_html, services_df, alerts_box, code_display, action_result_display, logs_display]
        
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
    theme = gr.themes.Base(
        primary_hue="cyan",
        secondary_hue="blue",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
    )
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, css=custom_css, theme=theme)
