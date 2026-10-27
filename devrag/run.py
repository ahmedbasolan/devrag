"""DevRAG launcher - loads .env before starting Streamlit."""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# Start Streamlit — bound to localhost only
sys.argv = [
    "streamlit",
    "run",
    "src/app.py",
    "--server.port=8501",
    "--server.headless=true",
    "--server.address=127.0.0.1",
]
from streamlit.web.cli import main  # noqa: E402

main()
