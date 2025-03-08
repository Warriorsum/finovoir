import subprocess
import sys

# List of Python scripts to execute in sequence
scripts = ["filtered_funds.py", "scraper.py", "calculations.py", "app.py"]

# Execute each script using the Python from the virtual environment
for script in scripts:
    print(f"🔹 Running {script}...")
    process = subprocess.run([sys.executable, script], check=True)  # Use venv Python
    print(f"✅ {script} completed.\n")

print("🚀 Website is now live! Open your browser and go to: http://127.0.0.1:5000/")
