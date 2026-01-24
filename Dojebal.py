import discord
import os
import asyncio
import json
import datetime
import random
from discord import app_commands
from discord.ext import tasks
from config import Config

# ---------------------------------------------------------
# KONFIGURACE
# ---------------------------------------------------------

TOKEN = Config.DISCORD_TOKEN
STATS_CHANNEL_ID = Config.STATS_CHANNEL_ID
DATA_FILE = "stats.json"

# --- GIFY ---
DOJEBAL_GIFS = [
    "https://tenor.com/o66e6Hw2Vpx.gif",
    "https://tenor.com/27Hi.gif",
    "https://tenor.com/98bR.gif",
    "https://tenor.com/bW0Nl.gif",
    "https://tenor.com/bqeRn.gif",
    "https://tenor.com/bUS7o.gif"
]

NEDOJEBAL_GIFS = [
    "https://tenor.com/jyQAUkmCdVw.gif",
    "https://tenor.com/sIJOPgXK92o.gif",
    "https://tenor.com/lTFto2VFSTI.gif",
    "https://tenor.com/cdzvfoJLwLC.gif",
    "https://tenor.com/m26akGvUwhq.gif",
    "https://tenor.com/iraH7VKfvnw.gif",
    "https://tenor.com/bUS8W.gif",
]

# Emotikony číslic
DIGIT_EMOJIS = {
    '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
    '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
}

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ---------------------------------------------------------
# PRÁCE S DATY
# ---------------------------------------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def update_stats(user_id, action_type):
    """
    action_type: 'dojebal' nebo 'nedojebal'
    """
    data = load_data()
    user_id_str = str(user_id)

    # Pokud uživatel neexistuje nebo je starý formát (číslo), resetujeme na slovník
    if user_id_str not in data or not isinstance(data[user_id_str], dict):
        data[user_id_str] = {"dojebal": 0, "nedojebal": 0}

    # Přičteme 1 k dané akci
    data[user_id_str][action_type] += 1

    save_data(data)
    return data[user_id_str]  # Vracíme slovník statistik uživatele


# ---------------------------------------------------------
# POMOCNÉ FUNKCE
# ---------------------------------------------------------

def number_to_emojis(number):
    return [DIGIT_EMOJIS[digit] for digit in str(number)]


async def find_last_number(channel):
    async for message in channel.history(limit=200):
        if message.author != client.user:
            continue

        my_reactions = [r for r in message.reactions if r.me]
        if not my_reactions:
            continue

        found_digits = []
        for reaction in message.reactions:
            if reaction.me and str(reaction.emoji) in DIGIT_EMOJIS.values():
                found_digits.append(str(reaction.emoji))

        if found_digits:
            emoji_to_digit = {v: k for k, v in DIGIT_EMOJIS.items()}
            number_str = "".join([emoji_to_digit[e] for e in found_digits if e in emoji_to_digit])
            if number_str:
                return int(number_str)
    return 0


async def create_stats_embed():
    data = load_data()

    # Seřadíme uživatele podle "čistého fuckup skóre" (Dojebal - Nedojebal)
    # Tzn. kdo má hodně Dojebal a málo Nedojebal, bude první.
    sorted_users = sorted(
        data.items(),
        key=lambda item: (item[1].get('dojebal', 0) - item[1].get('nedojebal', 0)) if isinstance(item[1], dict) else 0,
        reverse=True
    )

    top_5 = sorted_users[:5]

    # Spočítáme celkové statistiky serveru
    total_dojebal = 0
    total_nedojebal = 0
    for uid, stats in data.items():
        if isinstance(stats, dict):
            total_dojebal += stats.get('dojebal', 0)
            total_nedojebal += stats.get('nedojebal', 0)

    embed = discord.Embed(title="📊 Bilance Dojebání", color=0x3498db)
    embed.add_field(name="Globální statistika",
                    value=f"Celkem Dojebáno: **{total_dojebal}**\n Celkem Zachráněno: **{total_nedojebal}**",
                    inline=False)

    leaderboard_text = ""
    for index, (user_id, stats) in enumerate(top_5, start=1):
        try:
            user = await client.fetch_user(int(user_id))
            user_name = user.display_name
        except:
            user_name = f"Neznámý ({user_id})"

        # Ošetření pro případ starých dat
        if not isinstance(stats, dict): continue

        d_count = stats.get('dojebal', 0)
        n_count = stats.get('nedojebal', 0)

        # Ikonka podle převahy
        if d_count > n_count:
            icon = "💀"
        elif n_count > d_count:
            icon = "😇"
        else:
            icon = "⚖️"

        leaderboard_text += f"**{index}.** {icon} **{user_name}**\n   Opravdové staty: 👺 {d_count} | ✨ {n_count}\n"

    if not leaderboard_text:
        leaderboard_text = "Zatím žádná data."

    embed.description = leaderboard_text
    embed.set_footer(text="Řazeno podle (Dojebal - Nedojebal)")
    return embed


# ---------------------------------------------------------
# SLASH COMMANDS
# ---------------------------------------------------------

@tree.command(name="dojebal", description="Přiznat fuckup (+1 Dojebal)")
@app_commands.describe(popis="Popiš, co jsi dojebal")
async def dojebal_cmd(interaction: discord.Interaction, popis: str):
    await interaction.response.defer()

    hresnik = interaction.user
    last_num = await find_last_number(interaction.channel)
    current_num = last_num + 1

    # Aktualizace statistik - typ 'dojebal'
    stats = update_stats(hresnik.id, 'dojebal')

    gif_url = random.choice(DOJEBAL_GIFS)

    text = f"# DOJEBAL #{current_num}\n"
    text += f"**Přiznal se:** {hresnik.mention}\n"
    text += f"**Co se stalo:** {popis}\n"
    # Výpis oddělených statistik
    text += f"**Jeho staty:** Dojebal: {stats['dojebal']} | Nedojebal: {stats['nedojebal']}\n"
    text += f"\n{gif_url}"

    msg = await interaction.followup.send(content=text)

    num_emojis = number_to_emojis(current_num)
    for emoji in num_emojis:
        await msg.add_reaction(emoji)
        await asyncio.sleep(0.1)


@tree.command(name="nedojebal", description="Zapsat si úspěch/záchranu (+1 Nedojebal)")
@app_commands.describe(popis="Popiš, co se povedlo")
async def nedojebal_cmd(interaction: discord.Interaction, popis: str):
    await interaction.response.defer()

    hrdina = interaction.user
    last_num = await find_last_number(interaction.channel)
    current_num = last_num + 1

    # Aktualizace statistik - typ 'nedojebal'
    stats = update_stats(hrdina.id, 'nedojebal')

    gif_url = random.choice(NEDOJEBAL_GIFS)

    text = f"# NEDOJEBAL #{current_num}\n"
    text += f"**Hrdina:** {hrdina.mention}\n"
    text += f"**Co se povedlo:** {popis}\n"
    # Výpis oddělených statistik
    text += f"**Jeho staty:** Dojebal: {stats['dojebal']} | Nedojebal: {stats['nedojebal']}\n"
    text += f"\n{gif_url}"

    msg = await interaction.followup.send(content=text)

    num_emojis = number_to_emojis(current_num)
    for emoji in num_emojis:
        await msg.add_reaction(emoji)
        await asyncio.sleep(0.1)


@tree.command(name="stats", description="Zobrazit žebříček skóre")
async def stats_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await create_stats_embed()
    await interaction.followup.send(embed=embed)


# ---------------------------------------------------------
# DENNÍ STATISTIKA
# ---------------------------------------------------------

@tasks.loop(time=datetime.time(hour=7, minute=0, second=0))
async def daily_stats_task():
    await client.wait_until_ready()
    channel = client.get_channel(STATS_CHANNEL_ID)
    if channel:
        embed = await create_stats_embed()
        embed.title = "Ranní přehled skóre"
        await channel.send(embed=embed)


# ---------------------------------------------------------
# START
# ---------------------------------------------------------

@client.event
async def on_ready():
    print(f'Bot připojen jako {client.user}')
    try:
        synced = await tree.sync()
        print(f"Synchronizováno {len(synced)} příkazů.")
    except Exception as e:
        print(f"Chyba synchronizace: {e}")

    if not daily_stats_task.is_running():
        daily_stats_task.start()


if __name__ == "__main__":
    if not TOKEN:
        print("CHYBA: Nenalezen DISCORD_TOKEN. Zkontroluj .env soubor!")
    else:
        client.run(TOKEN)