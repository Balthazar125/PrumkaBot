# config.py
import os
from dotenv import load_dotenv

# Načte proměnné ze souboru .env
load_dotenv()


class Config:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    STATS_CHANNEL_ID = int(os.getenv("STATS_CHANNEL_ID", 0))
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    GITHUB_CHANNEL_ID = int(os.getenv("GITHUB_CHANNEL_ID", 0))
    MORNING_CHANNEL_ID = int(os.getenv("MORNING_CHANNEL_ID", 0))
    TODO_CHANNEL_ID = int(os.getenv("TODO_CHANNEL_ID", 0))