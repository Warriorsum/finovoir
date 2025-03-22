import subprocess
import sys
import time

# List of Python scripts to execute in sequence
scripts = ["filtered_funds.py", "scraper.py", "calculations.py", "app.py"]

def log_time(task_name, start_time):
    elapsed_time = time.time() - start_time
    print(f"⏳ {task_name} took {elapsed_time:.2f} seconds\n")

start_time = time.time()

# Execute each script and log its execution time
for script in scripts:
    step_start = time.time()
    print(f"🔹 Running {script}...")
    
    process = subprocess.run([sys.executable, script], check=True)  # Use venv Python
    
    log_time(script, step_start)
    print(f"✅ {script} completed.\n")

log_time("Total Execution", start_time)
print("🚀 Website is now live! Open your browser and go to: http://127.0.0.1:5000/")
