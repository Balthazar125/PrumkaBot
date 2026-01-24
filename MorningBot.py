import discord
import json
import random
import datetime
import os
from discord import app_commands
from discord.ext import tasks
from config import Config

# Konfigurace
TOKEN = Config.DISCORD_TOKEN
CHANNEL_ID = Config.STATS_CHANNEL_ID

# Nastavení role pro test
ALLOWED_ROLE = 1461082689779138795  # Nebo ID role jako int: 123456789

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def get_random_data():
    """
    Vrátí tuple: (text_zpravy, cesta_k_mediu_nebo_url)
    """
    try:
        with open("sentences.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        prefix = random.choice(data["prefix"])
        message = random.choice(data["messages"])
        media = random.choice(data["media"])

        # Sestavení textu
        full_text = f"{prefix}\n\n{message}"

        return full_text, media

    except Exception as e:
        print(f"Chyba při čtení sentences.json: {e}")
        return "Chyba při generování zprávy.", None


async def send_morning_message(interaction=None, channel=None):
    """Univerzální funkce pro odeslání (používá ji task i slash command)"""

    text, media_path = get_random_data()

    # Pokud nemáme kam posílat
    if not interaction and not channel:
        return

    # Logika pro odeslání (Interakce vs. Kanál)
    send_func = interaction.response.send_message if interaction else channel.send

    # 1. Pokud je to URL (Tenor gif, odkaz)
    if media_path and media_path.startswith("http"):
        # Přidáme odkaz na konec zprávy, Discord si náhled vytvoří sám
        final_text = f"{text}\n\n{media_path}"
        await send_func(content=final_text)

    # 2. Pokud je to lokální soubor (ve složce media)
    elif media_path:
        # Odstraníme úvodní lomítko, pokud tam je (aby cesta byla relativní k main.py)
        clean_path = media_path.lstrip("/").lstrip("\\")

        if os.path.exists(clean_path):
            file_to_send = discord.File(clean_path)
            await send_func(content=text, file=file_to_send)
        else:
            # Soubor nenalezen - pošleme jen text a chybovou hlášku do konzole
            print(f"POZOR: Soubor {clean_path} nenalezen!")
            await send_func(content=f"{text}\n\n(Obrázek se ztratil v Matrixu: {clean_path})")

    # 3. Žádné médium
    else:
        await send_func(content=text)


# --- SLASH COMMANDS ---

@tree.command(name="test_morning", description="Odešle testovací ranní zprávu (pouze pro vyvolené)")
@app_commands.checks.has_any_role(ALLOWED_ROLE)
async def test_morning(interaction: discord.Interaction):
    await send_morning_message(interaction=interaction)


@test_morning.error
async def test_morning_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message("Na tohle nemáš dostatečné oprávnění.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Chyba: {error}", ephemeral=True)


# --- AUTOMATICKÝ ÚKOL ---

@tasks.loop(time=datetime.time(hour=7, minute=0, second=0))
async def morning_greeting():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await send_morning_message(channel=channel)
        print("Ranní zpráva odeslána.")


@client.event
async def on_ready():
    print(f'MorningBot připojen jako {client.user}')
    await tree.sync()
    if not morning_greeting.is_running():
        morning_greeting.start()


if __name__ == "__main__":
    client.run(TOKEN)