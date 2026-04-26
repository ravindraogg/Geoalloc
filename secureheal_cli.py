#!/usr/bin/env python3
"""
SecureHeal Agent CLI
────────────────────────────────────
A command-line interface to interact with the SecureHeal Agent deployed on Hugging Face Spaces.
It automatically scans local files, directories, or GitHub repositories, sends the code 
to the HF Space for analysis, and can autonomously apply generated patches.
"""

import argparse
import os
import requests
import tempfile
import subprocess
import time
import json
import re

# Update this if your Space URL changes
HF_SPACE_URL = "https://ravindraog-secureheal-trainer.hf.space"

def print_banner():
    print("="*65)
    print("   SecureHeal Autonomous Agent CLI")
    print("="*65)
    print(f"[*] Connected to Space: {HF_SPACE_URL}")
    print("="*65 + "\n")

def scan_file(filepath):
    print(f"[*] Scanning: {filepath}")
    url = f"{HF_SPACE_URL}/scan/file"
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'text/plain')}
            data = {'context': 'generic code', 'max_tokens': 512}
            response = requests.post(url, files=files, data=data, timeout=300)
            
        if response.status_code == 200:
            result = response.json()
            if result.get('vulnerabilities_found'):
                print(f"  [!!] Vulnerability Detected in {filepath}!")
                analysis = result.get('analysis', '')
                
                # Show full agent reasoning (excluding raw tool calls)
                clean_analysis = re.sub(r'<tool_call>.*?</tool_call>', '', analysis, flags=re.DOTALL).strip()
                if clean_analysis:
                    print(f"  [>] Agent Analysis: \n\n{clean_analysis}\n")
                
                # Extract and apply patch
                apply_patch(filepath, analysis)
            else:
                print(f"  [OK] All checks passed. No vulnerabilities found in {filepath}.")
        elif response.status_code == 503:
            print("  [WAIT] Model is loading on Hugging Face. Please try again in 1-2 minutes.")
        else:
            print(f"  [!] Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  [!] Failed to scan {filepath}: {str(e)}")

def apply_patch(filepath, analysis):
    """Parses tool calls from the agent output and applies patches locally."""
    match = re.search(r'<tool_call>\s*apply_patch\s*\((.*?)\)\s*</tool_call>', analysis, re.DOTALL)
    if match:
        print("  [PATCH] Autonomous Agent generated a patch. Applying...")
        try:
            patch_data = json.loads(match.group(1))
            patch_code = patch_data.get("patch_code") or patch_data.get("code") or patch_data.get("patch")
            if patch_code:
                print(f"\n  [>>>] Proposed Patch Code:\n----------------------------------------\n{patch_code}\n----------------------------------------\n")
                
                # Backup the original file
                backup_path = filepath + ".bak"
                os.rename(filepath, backup_path)
                
                # Write the patched file
                with open(filepath, 'w') as f:
                    f.write(patch_code)
                print(f"  [DONE] Patch applied to {filepath} successfully! (Backup saved to .bak)")
            else:
                print("  [!] Patch tool called, but no code was provided in the arguments.")
        except Exception as e:
            print(f"  [!] Failed to parse patch JSON automatically: {e}")
            # If JSON parsing fails, at least print the raw tool call so the user can see the code!
            print(f"\n  [>>>] Raw Agent Output (Manual Fix Required):\n----------------------------------------\n{match.group(1)}\n----------------------------------------\n")

def process_target(target):
    if target.startswith("http://") or target.startswith("https://"):
        if "github.com" in target or "gitlab.com" in target:
            print(f"[*] Cloning repository: {target}")
            temp_dir = tempfile.mkdtemp(prefix="secureheal_repo_")
            try:
                subprocess.run(["git", "clone", target, temp_dir], check=True, capture_output=True)
                scan_directory(temp_dir)
            except subprocess.CalledProcessError as e:
                print(f"[!] Git clone failed: {e.stderr.decode()}")
        else:
            print("[!] URL does not look like a Git repository.")
    elif os.path.isdir(target):
        scan_directory(target)
    elif os.path.isfile(target):
        scan_file(target)
    else:
        print(f"[!] Target {target} not found or invalid.")

def scan_directory(directory):
    print(f"[*] Scanning directory: {directory}")
    valid_exts = {'.py', '.js', '.ts', '.go', '.java', '.rb', '.php', '.cpp', '.c', '.cs'}
    scanned_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Ignore common hidden/vendor directories
        if any(ignored in root for ignored in ['.git', 'node_modules', 'venv', '__pycache__', 'env']):
            continue
            
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in valid_exts:
                filepath = os.path.join(root, file)
                scan_file(filepath)
                scanned_count += 1
                time.sleep(1) # Slight delay to avoid hammering the HF API
                
    if scanned_count == 0:
        print("[!] No supported source code files found in the directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SecureHeal CLI - Autonomous Vulnerability Scanner & Patcher")
    parser.add_argument("target", help="Local directory path, file path, or GitHub repository URL to scan.")
    args = parser.parse_args()
    
    print_banner()
    process_target(args.target)
    print("\n[*] Scan complete.")
