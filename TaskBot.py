import discord
import json
import os

DATA_FILE = "tasks.json"


def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_tasks(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)


def add_task(description, author_name):
    tasks = load_tasks()

    # Zjištění nového ID (najde nejvyšší ID a přičte 1, nebo začne od 1)
    if tasks:
        new_id = max(t['id'] for t in tasks) + 1
    else:
        new_id = 1

    new_task = {
        "id": new_id,
        "task": description,
        "author": author_name
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return new_id


def complete_task(task_id):
    tasks = load_tasks()

    # Filtrujeme seznam, necháme jen ty, co nemají zadané ID
    new_tasks = [t for t in tasks if t['id'] != task_id]

    # Pokud se délka seznamu změnila, úkol byl smazán (nalezen)
    if len(new_tasks) < len(tasks):
        save_tasks(new_tasks)
        return True
    return False


def create_todo_embed():
    tasks = load_tasks()

    embed = discord.Embed(title="📝 To-Do List", color=0xf1c40f)

    if not tasks:
        embed.description = "Vše hotovo! Žádné aktivní úkoly. 😎"
    else:
        # Vytvoříme hezký seznam
        description_lines = []
        for t in tasks:
            line = f"**#{t['id']}** | {t['task']} \n└ *Přidal: {t['author']}*"
            description_lines.append(line)

        embed.description = "\n\n".join(description_lines)

    embed.set_footer(text="Přidej úkol: /to-do | Splň úkol: /vybavene [id]")
    return embed