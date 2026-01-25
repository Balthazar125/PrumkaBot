import discord
import json
import random
import os
import re
import feedparser
from config import Config

NEWS_RSS_URL = "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"


def clean_html(raw_html):
    return re.sub(re.compile('<.*?>'), '', raw_html) if raw_html else ""


def get_news_embed():
    try:
        feed = feedparser.parse(NEWS_RSS_URL)
        if not feed.entries: return None
        entry = feed.entries[0]
        embed = discord.Embed(title=entry.title, description=clean_html(getattr(entry, 'summary', ''))[:250],
                              url=entry.link, color=0xd60000)
        return embed
    except:
        return None


def get_random_data():
    try:
        with open("sentences.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return f"{random.choice(data['prefix'])}\n{random.choice(data['messages'])}", random.choice(data['media'])
    except:
        return "Chyba dat.", None


async def send_morning_message(interaction=None, channel=None):
    text, media_path = get_random_data()
    news_embed = get_news_embed()

    # Příprava argumentů
    kwargs = {"content": text}
    if news_embed:
        kwargs["embed"] = news_embed

    # Zpracování souboru/média
    if media_path:
        if media_path.startswith("http"):
            kwargs["content"] += f"\n{media_path}"
        else:
            clean_path = media_path.lstrip("/").lstrip("\\")
            if os.path.exists(clean_path):
                kwargs["file"] = discord.File(clean_path)

    try:
        if interaction:
            # Pokud voláme z interakce (Slash Command), musíme použít followup,
            # protože v main.py děláme defer()
            await interaction.followup.send(**kwargs)
        elif channel:
            # Pokud voláme z task loopu (automaticky ráno)
            await channel.send(**kwargs)
    except Exception as e:
        print(f"Chyba při odesílání: {e}")