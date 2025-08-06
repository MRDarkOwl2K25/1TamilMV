#!/usr/bin/env python3
"""
Restart script for Tamil RSS Bot (Windows Version)
This script cleans up corrupted session files and restarts the bot on Windows
"""

import os
import sys
import time
import subprocess
import signal

def cleanup_corrupted_sessions():
    """Clean up only corrupted session files, preserve working ones and bot data"""
    session_files = [
        "MN-Bot.session-journal",
        "MN-Bot.session.lock"
    ]
    
    cleaned = []
    for file in session_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                cleaned.append(file)
                print(f"✓ Cleaned up corrupted session file: {file}")
            except Exception as e:
                print(f"✗ Could not remove {file}: {e}")
    
    # Only remove main session file if it's corrupted (very small or empty)
    main_session = "MN-Bot.session"
    if os.path.exists(main_session):
        try:
            size = os.path.getsize(main_session)
            if size < 100:  # Very small session file is likely corrupted
                os.remove(main_session)
                cleaned.append(main_session)
                print(f"✓ Removed corrupted main session file (size: {size} bytes)")
            else:
                print(f"✓ Keeping main session file (size: {size} bytes)")
        except Exception as e:
            print(f"✗ Could not check session file {main_session}: {e}")
    
    # Preserve bot data files
    bot_data_files = ["bot_data.pkl"]
    for file in bot_data_files:
        if os.path.exists(file):
            print(f"✓ Preserving bot data: {file}")
    
    return cleaned

def kill_existing_process():
    """Kill any existing bot processes on Windows"""
    try:
        # Find Python processes running bot.py using tasklist
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"], 
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if 'bot.py' in line:
                    # Extract PID from CSV format
                    parts = line.split(',')
                    if len(parts) > 1:
                        pid = parts[1].strip('"')
                        try:
                            # Kill the process
                            subprocess.run(["taskkill", "/PID", pid, "/F"], check=True)
                            print(f"✓ Killed existing process: {pid}")
                            time.sleep(2)
                        except Exception as e:
                            print(f"✗ Could not kill process {pid}: {e}")
    except Exception as e:
        print(f"Note: Could not check for existing processes: {e}")

def restart_bot():
    """Restart the bot with clean session but preserve data"""
    print("🔄 Restarting Tamil RSS Bot...")
    
    # Clean up only corrupted sessions
    cleaned_files = cleanup_corrupted_sessions()
    if cleaned_files:
        print(f"Cleaned up {len(cleaned_files)} corrupted session files")
    else:
        print("No corrupted session files found")
    
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
    print("🤖 Tamil RSS Bot Restart Utility (Windows)")
    print("=" * 45)
    print("📊 This will preserve your bot's tracking data")
    print("🔧 Only corrupted session files will be removed")
    print()
    
    restart_bot() 