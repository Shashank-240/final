from pyngrok import ngrok
import subprocess
import time
import sys

print("Starting Streamlit Server...")
process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"])

time.sleep(3) # Wait for streamlit to start

print("Opening public tunnel...")
public_url = ngrok.connect(8501).public_url
print("\n" + "="*50)
print(f"YOUR LIVE APPLICATION IS HERE: {public_url}")
print("="*50 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    ngrok.kill()
    process.terminate()
