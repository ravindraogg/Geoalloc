import gradio as gr
import json
import pandas as pd
from secureheal_arena.server.secureheal_environment import SecureHealEnvironment

# ────────────────────────────────────────────────────────────────────────
# Modern Pastel SaaS Frontend for SecureHeal Arena
# ────────────────────────────────────────────────────────────────────────

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
@import url('https://unpkg.com/@phosphor-icons/web/src/regular/style.css');

:root {
    --bg-color: #0b0f19;
    --panel-bg: rgba(17, 24, 39, 0.7);
    --border-color: rgba(255, 255, 255, 0.1);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
}

body, .gradio-container {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg-color) !important;
    background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(239, 68, 68, 0.15) 0px, transparent 50%);
    color: var(--text-main) !important;
}

/* Glassmorphism Panels */
.glass-panel {
    background-color: var(--panel-bg) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5) !important;
    padding: 24px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.glass-panel:hover {
    box-shadow: 0 12px 48px 0 rgba(0, 0, 0, 0.6) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
}

/* Header Text */
.header-title {
    font-size: 3rem !important;
    font-weight: 800 !important;
    background: linear-gradient(to right, #60a5fa, #a78bfa) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    margin: 10px 0 0 0 !important;
    text-shadow: 0 0 40px rgba(96, 165, 250, 0.3);
}

/* Metric text */
.metric-value {
    font-size: 3rem !important;
    font-weight: 800 !important;
    font-family: 'JetBrains Mono', monospace !important;
    margin: 0 !important;
    text-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
}

.metric-green { color: #34d399 !important; text-shadow: 0 0 20px rgba(52, 211, 153, 0.4); }
.metric-red { color: #f87171 !important; text-shadow: 0 0 20px rgba(248, 113, 113, 0.4); }
.metric-blue { color: #60a5fa !important; text-shadow: 0 0 20px rgba(96, 165, 250, 0.4); }

/* Buttons */
button {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.025em !important;
    font-size: 0.9rem !important;
}

button.primary {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.4) !important;
}

button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px 0 rgba(59, 130, 246, 0.6) !important;
}

button.secondary {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

button.secondary:hover {
    background-color: rgba(255, 255, 255, 0.1) !important;
    transform: translateY(-1px) !important;
}

/* Code and Logs */
.log-box textarea, .gradio-code textarea, .gradio-code .cm-editor {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: rgba(15, 23, 42, 0.6) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
}

.log-box textarea:focus, .gradio-code .cm-focused {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
}

.icon-header {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #f8fafc !important;
    margin-bottom: 20px !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 10px;
}
"""

def create_demo():
    # Use the base theme as a clean slate
    with gr.Blocks(title="SecureHeal Arena", css=custom_css, theme=gr.themes.Base()) as demo:
        env_state = gr.State()

        with gr.Column(elem_classes="glass-panel"):
            gr.HTML("""
            <div style="text-align: center; margin-bottom: 10px;">
                <i class="ph ph-shield-check" style="font-size: 4rem; color: #60A5FA; text-shadow: 0 0 20px rgba(96,165,250,0.5);"></i>
                <h1 class="header-title">SecureHeal Arena</h1>
                <p style="font-size: 1.2rem; color: #94A3B8; margin-top: 5px; font-weight: 500;">Autonomous System Recovery & Vulnerability Patching Command Center</p>
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
            stab_html = f"<div style='text-align:center'><p style='color:#94A3B8;margin:0;font-weight:600;letter-spacing:0.05em;'>SYSTEM STABILITY</p><h2 class='{stab_color}'>{state.system_stability:.0%}</h2></div>"
            
            lat_color = "metric-red" if state.latency_current > 150 else "metric-blue"
            lat_html = f"<div style='text-align:center'><p style='color:#94A3B8;margin:0;font-weight:600;letter-spacing:0.05em;'>CURRENT LATENCY</p><h2 class='{lat_color}'>{state.latency_current:.0f}ms</h2></div>"
            
            rew_html = f"<div style='text-align:center'><p style='color:#94A3B8;margin:0;font-weight:600;letter-spacing:0.05em;'>TOTAL REWARD</p><h2 class='metric-blue'>{state.total_reward:.2f}</h2></div>"
            
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
    # Use dark mode base with slate accents
    theme = gr.themes.Base(
        primary_hue="blue",
        secondary_hue="indigo",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
    ).set(
        body_background_fill="*neutral_950",
        block_background_fill="*neutral_900",
        block_border_width="1px",
        block_border_color="*neutral_800",
        input_background_fill="*neutral_800",
    )
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, css=custom_css, theme=theme)
