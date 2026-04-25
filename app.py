import gradio as gr
import json
import pandas as pd
from secureheal_arena.server.secureheal_environment import SecureHealEnvironment

# ────────────────────────────────────────────────────────────────────────
# Modern Pastel SaaS Frontend for SecureHeal Arena
# ────────────────────────────────────────────────────────────────────────

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');
@import url('https://unpkg.com/@phosphor-icons/web/src/regular/style.css');

body, .gradio-container {
    font-family: 'Inter', sans-serif !important;
    background-color: #F8FAFC !important; /* Soft pastel slate background */
    color: #334155 !important;
}

/* Flat, clean panels */
.glass-panel {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05) !important;
    padding: 24px;
}

/* Pastel metric text */
.metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #475569;
    margin: 0;
}

.metric-green { color: #16A34A; }
.metric-red { color: #DC2626; }
.metric-blue { color: #2563EB; }

/* Buttons */
button.primary {
    background-color: #BAE6FD !important; /* Pastel Blue */
    color: #0369A1 !important;
    border: 1px solid #7DD3FC !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}
button.primary:hover {
    background-color: #7DD3FC !important;
}

button.secondary {
    background-color: #F1F5F9 !important;
    color: #475569 !important;
    border: 1px solid #CBD5E1 !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}
button.secondary:hover {
    background-color: #E2E8F0 !important;
}

/* Code and Logs */
.log-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #F1F5F9 !important;
    color: #334155 !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 8px !important;
}

.icon-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.25rem;
    font-weight: 600;
    color: #1E293B;
    margin-bottom: 16px;
}
"""

def create_demo():
    # Use the base theme as a clean slate
    with gr.Blocks(title="SecureHeal Arena", css=custom_css, theme=gr.themes.Base()) as demo:
        env_state = gr.State()

        with gr.Column(elem_classes="glass-panel"):
            gr.HTML("""
            <div style="text-align: center; margin-bottom: 10px;">
                <i class="ph ph-shield-check" style="font-size: 3rem; color: #3B82F6;"></i>
                <h1 style="font-size: 2.5rem; margin-top: 10px; margin-bottom: 0; color: #0F172A;">SecureHeal Arena</h1>
                <p style="font-size: 1.1rem; color: #64748B; margin-top: 5px;">Autonomous System Recovery & Vulnerability Patching Command Center</p>
            </div>
            """)

        with gr.Row():
            # --- LEFT COLUMN: CONTROLS ---
            with gr.Column(scale=1, elem_classes="glass-panel"):
                gr.HTML("<div class='icon-header'><i class='ph ph-sliders'></i> Mission Control</div>")
                with gr.Row():
                    curriculum_level = gr.Radio(choices=[1, 2, 3], value=1, label="Curriculum Level", container=False)
                    reset_btn = gr.Button("Initialize Scenario", variant="primary")
                
                gr.HTML("<div class='icon-header' style='margin-top: 24px;'><i class='ph ph-robot'></i> Agent Action Deck</div>")
                with gr.Accordion("Security Operations", open=True):
                    with gr.Row():
                        scan_btn = gr.Button("Scan Code")
                        sim_btn = gr.Button("Simulate Attack")
                    patch_input = gr.Code(language="python", label="Patch Code")
                    with gr.Row():
                        patch_btn = gr.Button("Apply Patch", variant="primary")
                        test_btn = gr.Button("Run Tests")
                
                with gr.Accordion("Infrastructure Operations", open=False):
                    service_input = gr.Dropdown(choices=["auth-service", "api-gateway", "db-layer", "payment-service"], label="Target Service", value="auth-service")
                    with gr.Row():
                        restart_btn = gr.Button("Restart Service")
                        realloc_btn = gr.Button("Reallocate Resources")
                    clean_btn = gr.Button("Clean Data Cache")
                    classify_input = gr.Textbox(label="Anomaly Classification", placeholder="e.g., MEMORY_SPIKE")
                    classify_btn = gr.Button("Classify Issue")
                    
            # --- RIGHT COLUMN: TELEMETRY & LOGS ---
            with gr.Column(scale=2):
                with gr.Row(elem_classes="glass-panel"):
                    stability_html = gr.HTML(value="<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>System Stability</p><h2 class='metric-value'>--</h2></div>")
                    latency_html = gr.HTML(value="<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>Current Latency</p><h2 class='metric-value'>--</h2></div>")
                    reward_html = gr.HTML(value="<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>Total Reward</p><h2 class='metric-value'>--</h2></div>")
                
                with gr.Row(elem_classes="glass-panel"):
                    with gr.Column():
                        services_df = gr.Dataframe(headers=["Microservice", "Health Status"], label="Infrastructure Status", interactive=False)
                    with gr.Column():
                        alerts_box = gr.Textbox(label="Active Threat Alerts", lines=4, interactive=False)
                
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
            
            stab_color = "metric-green" if state.system_stability > 0.8 else ("metric-red" if state.system_stability < 0.4 else "metric-value")
            stab_html = f"<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>System Stability</p><h2 class='{stab_color}'>{state.system_stability:.0%}</h2></div>"
            
            lat_color = "metric-red" if state.latency_current > 150 else "metric-value"
            lat_html = f"<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>Current Latency</p><h2 class='{lat_color}'>{state.latency_current:.0f}ms</h2></div>"
            
            rew_html = f"<div style='text-align:center'><p style='color:#64748B;margin:0;font-weight:500'>Total Reward</p><h2 class='metric-blue'>{state.total_reward:.2f}</h2></div>"
            
            services_data = [[k, "Healthy" if v=="up" else ("Down" if v=="down" else "Degraded")] for k, v in state.services_status.items()]
            
            alerts = []
            if state.vulnerability_present: alerts.append(f"[!] Vulnerability: {state.vulnerability_type}")
            if state.anomaly_type: alerts.append(f"[!] Anomaly: {state.anomaly_type}")
            for cf in state.cascading_failures: alerts.append(f"[!] Cascading: {cf}")
            if state.data_corrupted: alerts.append("[!] Data Corruption Detected")
            alerts_text = "\n".join(alerts) if alerts else "All Systems Nominal"
            
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
