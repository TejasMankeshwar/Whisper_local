import pyperclip
import subprocess
import time

def paste_text(text):
    # Copy text to clipboard
    pyperclip.copy(text)
    
    # Wait a tiny bit for clipboard to register
    time.sleep(0.1)
    
    # Simulate Cmd+V using AppleScript
    # This works gracefully on macOS and requires Accessibility permissions (which the whole app needs anyway)
    applescript = """
    tell application "System Events"
        keystroke "v" using command down
    end tell
    """
    
    try:
        print("Simulating Cmd+V paste...")
        subprocess.run(['osascript', '-e', applescript], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error simulating paste: {e}")
