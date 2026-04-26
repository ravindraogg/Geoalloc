@echo off
REM ============================================================
REM   SecureHeal CLI Demo Script
REM   Scans a medium-difficulty vulnerable Flask app using the
REM   SecureHeal Agent deployed on Hugging Face Spaces.
REM ============================================================
REM
REM   Usage: run_demo.bat
REM
REM   Prerequisites:
REM     - Python 3.8+
REM     - pip install requests
REM     - The HF Space must be running at:
REM       https://ravindraog-secureheal-trainer.hf.space
REM
REM ============================================================

echo.
echo ============================================================
echo   SecureHeal CLI Demo
echo   Scanning: demo\vulnerable_app.py
echo ============================================================
echo.

REM Step 1: Check that the Space is healthy
echo [1/3] Checking if the HF Space is alive...
curl -s https://ravindraog-secureheal-trainer.hf.space/health
echo.
echo.

REM Step 2: Run the CLI against the vulnerable file
echo [2/3] Running SecureHeal CLI scanner...
echo.
python secureheal_cli.py demo\vulnerable_app.py

REM Step 3: Show the diff if a patch was applied
echo.
echo [3/3] Checking for applied patches...
if exist demo\vulnerable_app.py.bak (
    echo.
    echo Patch was applied. Showing diff between original and patched file:
    echo ============================================================
    fc demo\vulnerable_app.py.bak demo\vulnerable_app.py
    echo ============================================================
    echo.
    echo Original backed up to: demo\vulnerable_app.py.bak
) else (
    echo No patch was applied during this run.
)

echo.
echo Demo complete.
pause
