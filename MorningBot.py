import discord
import json
import random
import datetime
import os
import re
import feedparser
from discord import app_commands
from discord.ext import tasks
from config import Config

# --- KONFIGURACE ---
TOKEN = Config.DISCORD_TOKEN
CHANNEL_ID = Config.STATS_CHANNEL_ID
ALLOWED_ROLE = 1461082689779138795  # Nebo ID role (int)
NEWS_RSS_URL = "https://ct24.ceskatelevize.cz/rss/hlavni-zpravy"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# --- POMOCNÉ FUNKCE ---

def clean_html(raw_html):
    """Odstraní HTML značky z textu."""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)


def get_news_embed():
    """Stáhne RSS a vrátí Discord Embed. Pokud selže, vrátí None."""
    try:
        feed = feedparser.parse(NEWS_RSS_URL)
        if not feed.entries:
            return None

        entry = feed.entries[0]
        title = entry.title
        link = entry.link
        summary = clean_html(getattr(entry, 'summary', ''))

        if len(summary) > 250:
            summary = summary[:250] + "..."

        # Vytvoření karty (Embed)
        embed = discord.Embed(
            title=title,
            description=summary,
            url=link,
            color=0xd60000
        )
        embed.set_author(name="ČT24 - Hlavní zprávy", icon_url="https://ct24.ceskatelevize.cz/favicon.ico")

        # Hledání obrázku
        image_url = None
        if 'media_content' in entry:
            image_url = entry.media_content[0]['url']
        elif 'links' in entry:
            for l in entry.links:
                if 'image' in l['type']:
                    image_url = l['href']
                    break

        if image_url:
            embed.set_thumbnail(url=image_url)

        embed.set_footer(text="Ranní přehled světa")
        return embed

    except Exception as e:
        print(f"Chyba při stahování RSS: {e}")
        return None


def get_random_data():
    """Vrátí (text, cesta_k_mediu)."""
    try:
        with open("sentences.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        prefix = random.choice(data["prefix"])
        message = random.choice(data["messages"])
        media = random.choice(data["media"])

        return f"{prefix}\n{message}", media
    except Exception as e:
        print(f"Chyba json: {e}")
        return "Chyba dat.", None


async def send_morning_message(interaction=None, channel=None):
    text, media_path = get_random_data()
    news_embed = get_news_embed()  # Může být None!

    if not interaction and not channel:
        return

    # Určení metody odeslání
    send_func = interaction.response.send_message if interaction else channel.send

    # Příprava argumentů pro odeslání (kwargs)
    # Tímto zajistíme, že tam nepošleme 'None' hodnoty
    message_kwargs = {}

    # 1. Zpracování Média (Soubor vs Odkaz)
    file_to_send = None
    if media_path:
        if media_path.startswith("http"):
            text += f"\n{media_path}"  # Odkaz přidáme do textu
        else:
            # Lokální soubor
            clean_path = media_path.lstrip("/").lstrip("\\")
            # Cesta je relativní k rootu projektu, takže "media/obrazek.jpg"
            if os.path.exists(clean_path):
                file_to_send = discord.File(clean_path)
                message_kwargs["file"] = file_to_send
            else:
                text += f"\n\n(Chyba: Soubor {clean_path} nenalezen)"

    # 2. Naplnění argumentů
    message_kwargs["content"] = text

    # DŮLEŽITÁ OPRAVA: Embed přidáme do zprávy jen tehdy, pokud existuje
    if news_embed is not None:
        message_kwargs["embed"] = news_embed

    # 3. Odeslání
    try:
        await send_func(**message_kwargs)
    except Exception as e:
        print(f"Chyba při odesílání: {e}")
        # Fallback - pokud to spadlo (např. moc velký soubor), zkusíme poslat jen text
        if interaction:
            await interaction.followup.send("Došlo k chybě při odesílání přílohy/embedu.")
        elif channel:
            await channel.send(f"{text}\n(Chyba přílohy)")


# --- SLASH COMMANDS ---

@tree.command(name="test_morning", description="Test ranní zprávy")
@app_commands.checks.has_any_role(ALLOWED_ROLE)
async def test_morning(interaction: discord.Interaction):
    await send_morning_message(interaction=interaction)


@test_morning.error
async def test_morning_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.response.send_message(f"Chyba: {error}", ephemeral=True)


# --- START ---

@tasks.loop(time=datetime.time(hour=7, minute=0, second=0))
async def morning_greeting():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await send_morning_message(channel=channel)


@client.event
async def on_ready():
    print(f'MorningBot připojen jako {client.user}')
    await tree.sync()
    if not morning_greeting.is_running():
        morning_greeting.start()


if __name__ == "__main__":
    client.run(TOKEN)