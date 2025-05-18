import os
import subprocess
import sys

def run_fire_monitor():
    """Run the fire_monitor.py script to generate today's reports"""
    print("Running fire monitoring script...")
    fire_monitor_path = os.path.join("scripts", "fire_monitor.py")
    
    try:
        result = subprocess.run([sys.executable, fire_monitor_path], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              universal_newlines=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running fire_monitor.py: {e}")
        print(e.stderr)
        return False

def update_website_data():
    """Run the update_web_data.py script to update JSON files"""
    print("Updating website data...")
    try:
        result = subprocess.run([sys.executable, "update_web_data.py"], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              universal_newlines=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating website data: {e}")
        print(e.stderr)
        return False

def main():
    """Run the full daily update process"""
    # Ensure output directories exist
    os.makedirs("fire_reports", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Run fire monitoring script
    if run_fire_monitor():
        # Update website data
        if update_website_data():
            print("Daily update completed successfully!")
            return 0
        else:
            print("Failed to update website data.")
            return 1
    else:
        print("Failed to run fire monitoring script.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 