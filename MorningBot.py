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

    # Určíme cílový kanál, kam budeme posílat
    # Pokud je to z interakce, vezmeme kanál z ní, jinak použijeme předaný objekt channel
    target = interaction.channel if interaction else channel

    if not target:
        print("Chyba: Nebyl nalezen cílový kanál.")
        return

    # --- 1. ZPRÁVA: Text + Médium (Soubor nebo GIF link) ---
    first_msg_kwargs = {"content": text}

    if media_path:
        if media_path.startswith("http"):
            # Přidáme link na GIF přímo do textu
            first_msg_kwargs["content"] += f"\n{media_path}"
        else:
            # Připravíme lokální soubor z cesty v JSONu
            clean_path = media_path.lstrip("/").lstrip("\\")
            if os.path.exists(clean_path):
                first_msg_kwargs["file"] = discord.File(clean_path)

    try:
        # Odešleme první část
        await target.send(**first_msg_kwargs)

        # --- 2. ZPRÁVA: Pouze novinky ---
        if news_embed:
            # Posíláme jako úplně novou zprávu bez textu
            await target.send(embed=news_embed)

    except Exception as e:
        print(f"Chyba při odesílání: {e}")

    except Exception as e:
        print(f"Chyba při odesílání: {e}")