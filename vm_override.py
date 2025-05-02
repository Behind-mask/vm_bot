#!/usr/bin/env python3
import sys
import os
import json
import logging
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/logs/vm_monitor.log'),
        logging.StreamHandler()
    ]
)

def save_override(username):
    """Save the override request to a file that the monitor can read"""
    override_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vm_override.json')
    try:
        with open(override_file, 'w') as f:
            json.dump({
                'username': username,
                'timestamp': str(datetime.datetime.now())
            }, f)
        logging.info(f"Override request saved for user: {username}")
        print(f"Override request registered for {username}. The VM will not shut down tonight.")
        return True
    except Exception as e:
        logging.error(f"Failed to save override request: {e}")
        print("Error: Failed to register override request.")
        return False

def remove_override():
    """Remove the override file to re-enable automatic monitoring"""
    override_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vm_override.json')
    try:
        if os.path.exists(override_file):
            os.remove(override_file)
            logging.info("Override cancelled - automatic monitoring restored")
            print("Override cancelled. VM will resume automatic monitoring and shutdown schedule.")
            return True
        else:
            print("No active override found.")
            return False
    except Exception as e:
        logging.error(f"Failed to remove override: {e}")
        print("Error: Failed to cancel override.")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  To override shutdown: vm_override <your_name>")
        print("  To cancel override:  vm_override cancel")
        print("Examples:")
        print("  vm_override john_doe")
        print("  vm_override cancel")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    if command == 'cancel':
        remove_override()
    else:
        save_override(command)

if __name__ == "__main__":
    main() 