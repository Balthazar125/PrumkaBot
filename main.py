import discord
import asyncio
import datetime
import random
import logging
import sys
import google.generativeai as genai
from discord import app_commands
from discord.ext import tasks, commands

# Importy z tvých modulů
from config import Config
import Dojebal
import MorningBot
import GitBot
import ChatPrumka
import TaskBot
import MonsterCheck

# --- LOGOVÁNÍ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PrumkaBot")

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Gemini Setup
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Slovník pro sledování více repozitářů
last_commits = {}


# ---------------------------------------------------------
# POMOCNÁ FUNKCE PRO STATICKÝ EMBED
# ---------------------------------------------------------
async def refresh_todo_list(bot_instance):
    """
    Tato funkce se stará o statický embed.
    Buď edituje existující zprávu, nebo pošle novou a uloží si její ID.
    """
    channel = bot_instance.get_channel(Config.TODO_CHANNEL_ID)
    if not channel:
        logger.warning("TODO_CHANNEL_ID není nastaven nebo kanál neexistuje.")
        return

    embed = TaskBot.create_todo_embed()
    stored_msg_id = TaskBot.get_message_id()

    # Zkusíme najít a editovat starou zprávu
    if stored_msg_id:
        try:
            msg = await channel.fetch_message(stored_msg_id)
            await msg.edit(embed=embed)
            return  # Hotovo, editace proběhla
        except discord.NotFound:
            logger.info("Stará To-Do zpráva nenalezena, vytvářím novou.")
        except Exception as e:
            logger.error(f"Chyba při editaci To-Do zprávy: {e}")

    # Pokud zpráva neexistuje (nebo smazána), pošleme novou
    try:
        # Volitelně můžeme smazat staré zprávy v kanálu, aby byl clean (pozor na smazání cizích zpráv)
        # await channel.purge(limit=5)

        msg = await channel.send(embed=embed)
        TaskBot.set_message_id(msg.id)
    except Exception as e:
        logger.error(f"Nelze odeslat novou To-Do zprávu: {e}")


# ---------------------------------------------------------
# SLASH COMMANDS
# ---------------------------------------------------------

@bot.tree.command(name="dojebal", description="Přiznat fuckup (+1 Dojebal)")
async def dojebal_cmd(interaction: discord.Interaction, popis: str):
    await interaction.response.defer()
    try:
        stats = Dojebal.update_stats(interaction.user.id, 'dojebal')
        last_num = await Dojebal.find_last_number(interaction.channel)
        current_num = last_num + 1
        gif = random.choice(Dojebal.DOJEBAL_GIFS)
        text = (f"# DOJEBAL #{current_num}\n"
                f"**Hříšník:** {interaction.user.mention}\n"
                f"**Co se stalo:** {popis}\n"
                f"**Staty:** Dojebal: {stats['dojebal']} | Nedojebal: {stats['nedojebal']}\n\n{gif}")
        msg = await interaction.followup.send(content=text)
        for emoji in Dojebal.number_to_emojis(current_num):
            await msg.add_reaction(emoji)
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Chyba v dojebal_cmd: {e}")


@bot.tree.command(name="nedojebal", description="Zapsat si úspěch (+1 Nedojebal)")
async def nedojebal_cmd(interaction: discord.Interaction, popis: str):
    await interaction.response.defer()
    try:
        stats = Dojebal.update_stats(interaction.user.id, 'nedojebal')
        last_num = await Dojebal.find_last_number(interaction.channel)
        current_num = last_num + 1
        gif = random.choice(Dojebal.NEDOJEBAL_GIFS)
        text = (f"# NEDOJEBAL #{current_num}\n"
                f"**Hrdina:** {interaction.user.mention}\n"
                f"**Úspěch:** {popis}\n"
                f"**Staty:** Dojebal: {stats['dojebal']} | Nedojebal: {stats['nedojebal']}\n\n{gif}")
        msg = await interaction.followup.send(content=text)
        for emoji in Dojebal.number_to_emojis(current_num):
            await msg.add_reaction(emoji)
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Chyba v nedojebal_cmd: {e}")


@bot.tree.command(name="stats", description="Zobrazit žebříček skóre")
async def stats_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await Dojebal.create_stats_embed(bot)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="test_morning", description="Test ranní zprávy")
@app_commands.checks.has_any_role(1461082689779138795)
async def test_morning(interaction: discord.Interaction):
    await interaction.response.defer()
    await MorningBot.send_morning_message(interaction=interaction)


# --- TASK COMMANDS (Upravené) ---

@bot.tree.command(name="to-do", description="Přidat úkol do seznamu")
async def todo_add_cmd(interaction: discord.Interaction, co_udelat: str):
    # Odpovíme jen "ephemeral" (vidí to jen uživatel), aby se nezasíral chat
    await interaction.response.defer(ephemeral=True)
    try:
        author = interaction.user.display_name
        TaskBot.add_task(co_udelat, author)

        # Aktualizujeme statický embed
        await refresh_todo_list(bot)

        await interaction.followup.send(content=f"Úkol přidán.")
    except Exception as e:
        logger.error(f"Chyba v todo_add_cmd: {e}")
        await interaction.followup.send("Chyba při ukládání úkolu.")


@bot.tree.command(name="vybavene", description="Označit úkol jako hotový (podle ID)")
async def todo_done_cmd(interaction: discord.Interaction, id_ukolu: int):
    await interaction.response.defer(ephemeral=True)
    try:
        success = TaskBot.complete_task(id_ukolu)

        if success:
            # Aktualizujeme statický embed
            await refresh_todo_list(bot)
            await interaction.followup.send(content=f"Úkol #{id_ukolu} hotov a smazán.")
        else:
            await interaction.followup.send(content=f"Úkol s ID #{id_ukolu} neexistuje.")
    except Exception as e:
        logger.error(f"Chyba v todo_done_cmd: {e}")
        await interaction.followup.send("Chyba.")


# ---------------------------------------------------------
# TASKS
# ---------------------------------------------------------

@tasks.loop(time=datetime.time(hour=8, minute=0))
async def daily_routine():
    m_channel = bot.get_channel(Config.MORNING_CHANNEL_ID)
    if m_channel:
        await MorningBot.send_morning_message(channel=m_channel)
    s_channel = bot.get_channel(Config.STATS_CHANNEL_ID)
    if s_channel:
        embed = await Dojebal.create_stats_embed(bot)
        embed.title = "Ranní přehled dojebání"
        await s_channel.send(embed=embed)


@tasks.loop(minutes=1.0)
async def github_loop():
    channel = bot.get_channel(Config.GITHUB_CHANNEL_ID)
    if not channel: return
    try:
        repos = [r.strip() for r in Config.GITHUB_REPO.split(",")]
    except AttributeError:
        return

    for repo in repos:
        commits = GitBot.get_github_commits(repo)
        if not commits or 'sha' not in commits[0]: continue

        new_sha = commits[0]['sha']
        if repo not in last_commits:
            last_commits[repo] = new_sha
            continue

        if new_sha != last_commits[repo]:
            c = commits[0]
            repo_short = repo.split("/")[-1]
            embed = discord.Embed(
                title=f"Nový commit: {repo_short}",
                description=f"**{c['commit']['author']['name']}**: {c['commit']['message']}",
                url=c['html_url'],
                color=0x2b2d31
            )
            embed.set_footer(text=f"Repo: {repo} | SHA: {new_sha[:7]}")
            await channel.send(embed=embed)
            last_commits[repo] = new_sha

# --- NOVÁ SMYČKA PRO MONSTER CHECK (každé 4 hodiny) ---
@tasks.loop(hours=4)
async def monster_loop():
    # Pro jistotu jen logneme, že kontrola běží
    logger.info("Spouštím kontrolu slev (MonsterCheck)...")
    try:
        await MonsterCheck.check_discounts(bot)
    except Exception as e:
        logger.error(f"Chyba v MonsterCheck loopu: {e}")

# ---------------------------------------------------------
# EVENTS
# ---------------------------------------------------------

@bot.event
async def on_message(message):
    if message.author == bot.user: return

    if bot.user in message.mentions:
        async with message.channel.typing():
            query = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if not query: return
            history = await ChatPrumka.get_chat_history(message.channel)
            prompt = f"SYSTEM LORE:\n{ChatPrumka.BOT_LORE}\n\n{history}\n\nDOTAZ: {query}\nODPOVĚĎ:"
            try:
                response = model.generate_content(prompt)
                await message.channel.send(response.text[:2000])
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                await message.channel.send("Můj digitální mozek má výpadek.")


@bot.event
async def on_ready():
    logger.info(f'Sjednocený bot spuštěn jako {bot.user}')

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synchronizováno {len(synced)} slash příkazů.")
    except Exception as e:
        logger.error(f"Sync error: {e}")

    # Inicializace SHA pro GitHub
    if Config.GITHUB_REPO:
        repos = [r.strip() for r in Config.GITHUB_REPO.split(",")]
        for r in repos:
            c = GitBot.get_github_commits(r)
            if c and 'sha' in c[0]:
                last_commits[r] = c[0]['sha']


    await refresh_todo_list(bot)

    # Start smyček
    if not github_loop.is_running():
        github_loop.start()
    if not daily_routine.is_running():
        daily_routine.start()
    if not monster_loop.is_running():
        monster_loop.start()


# --- RUN ---
if __name__ == "__main__":
    bot.run(Config.DISCORD_TOKEN)