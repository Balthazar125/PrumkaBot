import discord
import json
import os
import time

DATA_FILE = "tasks.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"message_id": None, "tasks": []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Základní migrace, kdyby soubor existoval ve starém formátu
            if isinstance(data, list):
                return {"message_id": None, "tasks": data}
            return data
    except:
        return {"message_id": None, "tasks": []}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_message_id():
    """Vrátí ID zprávy s embedem, pokud existuje."""
    data = load_data()
    return data.get("message_id")


def set_message_id(msg_id):
    """Uloží ID zprávy, abychom ji příště mohli editovat."""
    data = load_data()
    data["message_id"] = msg_id
    save_data(data)


def add_task(description, author_name):
    data = load_data()
    tasks = data["tasks"]

    if tasks:
        new_id = max(t['id'] for t in tasks) + 1
    else:
        new_id = 1

    new_task = {
        "id": new_id,
        "task": description,
        "author": author_name,
        "created_at": int(time.time())  # Uložíme aktuální čas
    }
    tasks.append(new_task)
    data["tasks"] = tasks
    save_data(data)
    return new_id


def complete_task(task_id):
    data = load_data()
    tasks = data["tasks"]

    new_tasks = [t for t in tasks if t['id'] != task_id]

    if len(new_tasks) < len(tasks):
        data["tasks"] = new_tasks
        save_data(data)
        return True
    return False


def create_todo_embed():
    data = load_data()
    tasks = data["tasks"]

    embed = discord.Embed(title="📋 Interaktivní To-Do List", color=0x2ecc71)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4697/4697260.png")  # Volitelná ikona

    if not tasks:
        embed.description = "✅ **Vše hotovo!** Seznam je prázdný.\n\n*Přidej úkol pomocí `/to-do`*"
        embed.color = 0x95a5a6  # Šedá, když je prázdno
    else:
        desc_lines = []
        for t in tasks:
            # <t:timestamp:R> udělá relativní čas (např. "před 2 hodinami")
            timestamp_code = f"<t:{t.get('created_at', int(time.time()))}:R>"

            line = (
                f"**#{t['id']}** ⬜ **{t['task']}**\n"
                f"└ 👤 {t['author']} • 🕒 {timestamp_code}"
            )
            desc_lines.append(line)

        embed.description = "\n\n".join(desc_lines)

    embed.set_footer(text="Příkazy: /to-do [text] | /vybavene [id]")
    embed.timestamp = discord.utils.utcnow()
    return embed