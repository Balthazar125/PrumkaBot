import discord

BOT_LORE = """
Jsi sarkastický asistent pro studenty průmyslovky. 
Máš rád technický humor, IT, 3D tisk a League of Legends. 
Jsi znalec událostí 11. září 2001. Stručný a vtipný.
"""

async def get_chat_history(channel, limit=10):
    messages = []
    async for msg in channel.history(limit=limit):
        if msg.content:
            messages.append(f"[{msg.author.name}]: {msg.content}")
    return "HISTORIE:\n" + "\n".join(reversed(messages))