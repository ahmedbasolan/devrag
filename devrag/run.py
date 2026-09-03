"""DevRAG launcher - loads .env before starting Streamlit."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

print(f"GEMINI_API_KEY loaded: {bool(os.getenv('GEMINI_API_KEY'))}")

# Start Streamlit
sys.argv = ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.headless=true"]
from streamlit.web.cli import main
main()
