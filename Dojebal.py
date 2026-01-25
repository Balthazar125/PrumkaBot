import discord
import os
import asyncio
import json
import random
from config import Config

# Konstany ponecháme pro main.py
STATS_CHANNEL_ID = Config.STATS_CHANNEL_ID
DATA_FILE = "stats.json"

DOJEBAL_GIFS = [
    "https://tenor.com/o66e6Hw2Vpx.gif", "https://tenor.com/27Hi.gif",
    "https://tenor.com/98bR.gif", "https://tenor.com/bW0Nl.gif",
    "https://tenor.com/bqeRn.gif", "https://tenor.com/bUS7o.gif"
]
NEDOJEBAL_GIFS = [
    "https://tenor.com/jyQAUkmCdVw.gif", "https://tenor.com/sIJOPgXK92o.gif",
    "https://tenor.com/lTFto2VFSTI.gif", "https://tenor.com/cdzvfoJLwLC.gif",
    "https://tenor.com/m26akGvUwhq.gif", "https://tenor.com/iraH7VKfvnw.gif",
    "https://tenor.com/bUS8W.gif"
]
DIGIT_EMOJIS = {
    '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
    '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
}


def load_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)


def update_stats(user_id, action_type):
    data = load_data()
    uid = str(user_id)
    if uid not in data or not isinstance(data[uid], dict):
        data[uid] = {"dojebal": 0, "nedojebal": 0}
    data[uid][action_type] += 1
    save_data(data)
    return data[uid]


def number_to_emojis(number):
    return [DIGIT_EMOJIS[digit] for digit in str(number)]


# Uprav v Dojebal.py tuto funkci
async def find_last_number(channel):
    # Snížíme limit z 100 na 50 pro rychlost,
    # prohledávání historie je v Discord.py relativně pomalé.
    async for message in channel.history(limit=50):
        if not message.reactions:
            continue

        # Hledáme reakce od bota (DIGIT_EMOJIS)
        found_digits = []
        # Použijeme seznam hodnot pro rychlejší look-up
        emoji_values = set(DIGIT_EMOJIS.values())

        for r in message.reactions:
            if str(r.emoji) in emoji_values:
                found_digits.append(str(r.emoji))

        if found_digits:
            emoji_to_digit = {v: k for k, v in DIGIT_EMOJIS.items()}
            # Musíme zachovat pořadí, jak byly reakce přidány (nebo jak jsou v seznamu)
            num_str = "".join([emoji_to_digit[e] for e in found_digits])
            if num_str.isdigit():
                return int(num_str)
    return 0

async def create_stats_embed(bot_client):
    data = load_data()
    sorted_users = sorted(data.items(), key=lambda x: (x[1].get('dojebal', 0) - x[1].get('nedojebal', 0)), reverse=True)

    total_d = sum(s.get('dojebal', 0) for u, s in data.items() if isinstance(s, dict))
    total_n = sum(s.get('nedojebal', 0) for u, s in data.items() if isinstance(s, dict))

    embed = discord.Embed(title="Bilance Dojebání", color=0x3498db)
    embed.add_field(name="Globální statistika", value=f"Dojebáno: **{total_d}** | Zachráněno: **{total_n}**",
                    inline=False)

    leaderboard = ""
    for i, (uid, stats) in enumerate(sorted_users[:5], 1):
        try:
            user = await bot_client.fetch_user(int(uid))
            name = user.display_name
        except:
            name = f"Neznámý ({uid})"
        leaderboard += f"**{i}.** {name} ({stats['dojebal']} | {stats['nedojebal']})\n"

    embed.description = leaderboard or "Zatím žádná data."
    return embed