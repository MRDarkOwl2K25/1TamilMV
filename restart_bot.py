#!/usr/bin/env python3
"""
Restart script for Tamil RSS Bot
This script cleans up corrupted session files and restarts the bot
"""

import os
import sys
import time
import subprocess
import signal

def cleanup_sessions():
    """Clean up old session files that might be corrupted"""
    session_files = [
        "MN-Bot.session", 
        "MN-Bot.session-journal",
        "MN-Bot.session.lock"
    ]
    
    cleaned = []
    for file in session_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                cleaned.append(file)
                print(f"✓ Cleaned up: {file}")
            except Exception as e:
                print(f"✗ Could not remove {file}: {e}")
    
    return cleaned

def kill_existing_process():
    """Kill any existing bot processes"""
    try:
        # Find Python processes running bot.py
        result = subprocess.run(
            ["pgrep", "-f", "python.*bot.py"], 
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✓ Killed existing process: {pid}")
                        time.sleep(2)
                    except Exception as e:
                        print(f"✗ Could not kill process {pid}: {e}")
    except Exception as e:
        print(f"Note: Could not check for existing processes: {e}")

def restart_bot():
    """Restart the bot with clean session"""
    print("🔄 Restarting Tamil RSS Bot...")
    
    # Clean up old sessions
    cleaned_files = cleanup_sessions()
    if cleaned_files:
        print(f"Cleaned up {len(cleaned_files)} session files")
    
    # Kill existing processes
    kill_existing_process()
    
    # Wait a moment for cleanup
    time.sleep(3)
    
    # Start the bot
    print("🚀 Starting bot...")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Bot failed to start: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🤖 Tamil RSS Bot Restart Utility")
    print("=" * 40)
    
    restart_bot() 