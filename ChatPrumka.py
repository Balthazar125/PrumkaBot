import discord
import google.generativeai as genai
import os
import logging
import sys
from config import Config

# =============================================================================
#                               LOGOVÁNÍ
# =============================================================================
logging.basicConfig(
    level=logging.INFO,  # Přepnuto na INFO (už nepotřebujeme vidět HTTP requesty na wiki)
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PrumkaBot")

# =============================================================================
#                               KONFIGURACE
# =============================================================================

# 1. DISCORD TOKEN
DISCORD_TOKEN = Config.DISCORD_TOKEN

# 2. GEMINI API KEY
GEMINI_API_KEY = Config.GEMINI_API_KEY

# 3. OSOBNOST BOTA (LORE)
# Upravil jsem to, aby se nespoléhal na data, která už nemá.
BOT_LORE = """
Jsi sarkastický asistent pro studenty průmyslovky.
Máš rád technický humor a jsi stručný.
Jsi expert na IT, elektrotechniku, strojírenství, 3D tisk a programování.
Když se tě někdo zeptá na konkrétní věci o škole (rozvrhy, učitelé),
řekni něco vtipného o tom, že nemáš přístup do školní databáze,
nebo improvizuj obecnou radou, ale nevymýšlej si fakta, která nemůžeš vědět. Jsi znalec událostí jedenáctého zaří roku 2001
a hraješ league of legends.
"""

# =============================================================================
#                               SETUP
# =============================================================================

logger.info("--- STARTUJI OŘEZANOU VERZI BOTA ---")

# Nastavení Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    logger.info("Gemini API připojeno.")
except Exception as e:
    logger.critical(f"Chyba Gemini klíče: {e}")
    sys.exit(1)

# Nastavení Discord
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


# =============================================================================
#                               FUNKCE
# =============================================================================

async def get_chat_history(channel, limit=100):
    """
    Stáhne posledních X zpráv pro kontext konverzace.
    """
    logger.info(f"Stahuji historii ({limit} zpráv)...")
    messages = []
    async for msg in channel.history(limit=limit):
        if msg.content:
            # Formát: [Uživatel]: Text
            messages.append(f"[{msg.author.name}]: {msg.content}")

    # Discord vrací od nejnovější, my to otočíme pro AI (od nejstarší)
    return "HISTORIE CHATU (Kontext):\n" + "\n".join(reversed(messages))


# =============================================================================
#                               DISCORD EVENTY
# =============================================================================

@client.event
async def on_ready():
    logger.info(f'Bot je online: {client.user}')


@client.event
async def on_message(message):
    # Ignorovat vlastní zprávy
    if message.author == client.user:
        return

    # Reagovat pouze na ping
    if client.user in message.mentions:
        logger.info(f"Ping od uživatele: {message.author.name}")

        async with message.channel.typing():
            # 1. Získání čistého dotazu
            user_query = message.content.replace(f'<@{client.user.id}>', '').strip()

            if not user_query:
                await message.channel.send("??")
                return

            # 2. Načtení paměti
            history = await get_chat_history(message.channel)

            # 3. Sestavení promptu (Už bez Wiki)
            final_prompt = (
                f"SYSTEM LORE:\n{BOT_LORE}\n\n"
                f"{history}\n\n"
                f"AKTUÁLNÍ DOTAZ ({message.author.name}):\n{user_query}\n\n"
                "ODPOVĚĎ BOTA:"
            )

            try:
                # 4. Generování
                response = model.generate_content(final_prompt)
                reply = response.text

                # 5. Odeslání (ošetření délky 2000 znaků)
                if len(reply) > 2000:
                    for i in range(0, len(reply), 2000):
                        await message.channel.send(reply[i:i + 2000])
                else:
                    await message.channel.send(reply)

            except Exception as e:
                logger.error(f"Chyba při generování: {e}")
                await message.channel.send("Error. Můj mozek neodpovídá.")


# Spuštění
client.run(DISCORD_TOKEN)