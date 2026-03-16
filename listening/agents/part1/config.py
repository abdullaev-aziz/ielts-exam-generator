import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-5.4-2026-03-05"
