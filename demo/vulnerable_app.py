"""
SecureHeal Demo - Extremely Vulnerable App
Target for CLI Autonomous Scanning & Patching
"""
import sqlite3
import os

def login(username, password):
    # VULNERABILITY: Blatant SQL Injection
    # The agent should easily detect this f-string injection
    db = sqlite3.connect("users.db")
    cursor = db.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    return cursor.fetchone()

def run_backup(user_input_path):
    # VULNERABILITY: Blatant Command Injection
    # Using os.system with direct user input
    print(f"Running backup for {user_input_path}...")
    os.system("cp -r " + user_input_path + " /backup/")

def get_user_file(filename):
    # VULNERABILITY: Path Traversal
    # Direct access to file system via user input
    with open("data/" + filename, "r") as f:
        return f.read()

if __name__ == "__main__":
    # Test calls
    print(login("admin' OR '1'='1", "password"))
    run_backup("; rm -rf / ;")
    print(get_user_file("../../etc/passwd"))
