import discord
import json
import os
import time

DATA_FILE = "tasks.json"


def load_data():
    """Načte data z JSONu. Pokud neexistuje, vrátí prázdnou strukturu."""
    if not os.path.exists(DATA_FILE):
        return {"message_id": None, "tasks": []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Zpětná kompatibilita pro starý formát (pokud existoval)
            if isinstance(data, list):
                return {"message_id": None, "tasks": data}
            return data
    except:
        return {"message_id": None, "tasks": []}


def save_data(data):
    """Uloží kompletní data (ID zprávy i úkoly) do JSONu."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_message_id():
    data = load_data()
    return data.get("message_id")


def set_message_id(msg_id):
    data = load_data()
    data["message_id"] = msg_id
    save_data(data)


def add_task(description, author_name):
    data = load_data()
    tasks = data["tasks"]

    # Generování nového ID
    if tasks:
        new_id = max(t['id'] for t in tasks) + 1
    else:
        new_id = 1

    new_task = {
        "id": new_id,
        "task": description,
        "author": author_name,
        # ZDE SE UKLÁDÁ ČAS DO SOUBORU (přežije restart)
        "created_at": int(time.time())
    }
    tasks.append(new_task)
    data["tasks"] = tasks
    save_data(data)
    return new_id


def complete_task(task_id):
    data = load_data()
    tasks = data["tasks"]

    # Odstraníme úkol podle ID
    new_tasks = [t for t in tasks if t['id'] != task_id]

    if len(new_tasks) < len(tasks):
        data["tasks"] = new_tasks
        save_data(data)
        return True
    return False


def create_todo_embed():
    data = load_data()
    tasks = data["tasks"]

    embed = discord.Embed(title="To-Do List", color=0x2ecc71)
    # Ikona (set_thumbnail) byla odstraněna dle požadavku

    if not tasks:
        embed.description = "**Vše hotovo!** Seznam je prázdný.\n\n*Přidej úkol pomocí `/to-do`*"
        embed.color = 0x95a5a6
    else:
        desc_lines = []
        for t in tasks:
            # Načteme čas vytvoření z JSONu. Pokud u starých tasků chybí, použijeme aktuální.
            created_at = t.get('created_at', int(time.time()))

            # Discord formátování času <t:TIMESTAMP:R> (např. "před 2 hodinami")
            timestamp_code = f"<t:{created_at}:R>"

            line = (
                f"**#{t['id']}**: **{t['task']}**\n"
                f"└  {t['author']}•{timestamp_code}"
            )
            desc_lines.append(line)

        embed.description = "\n\n".join(desc_lines)

    embed.set_footer(text="Příkazy: /to-do [text] | /vybavene [id]")
    embed.timestamp = discord.utils.utcnow()
    return embed