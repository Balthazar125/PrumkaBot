import discord
import requests
from discord.ext import tasks, commands
from config import Config

# Nastavení z Configu
TOKEN = Config.DISCORD_TOKEN
GH_TOKEN = Config.GITHUB_TOKEN
REPO = Config.GITHUB_REPO
CHANNEL_ID = Config.GITHUB_CHANNEL_ID

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Pomocná proměnná pro ukládání posledního commitu, aby se neposílaly duplicity
last_commit_sha = None


def get_github_commits():
    """Získá seznam commitů z GitHub API."""
    url = f"https://api.github.com/repos/{REPO}/commits"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Chyba GitHub API: {response.status_code}")
        return []


@tasks.loop(minutes=1.0)
async def check_github_updates():
    global last_commit_sha
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    commits = get_github_commits()
    if not commits:
        return

    latest_commit = commits[0]
    sha = latest_commit['sha']

    if last_commit_sha is not None and sha != last_commit_sha:
        # Načtení dat z API
        author_name = latest_commit['commit']['author']['name']
        commit_message = latest_commit['commit']['message']
        url = latest_commit['html_url']

        # Sestavení Embedu podle tvých požadavků
        embed = discord.Embed(
            title="Nový commit",  # V hlavičce je jasně "Nový commit"
            description=f"**{author_name}**: {commit_message}",  # Formát Jméno: Zpráva
            color=0x2b2d31,
            url=url
        )

        # Volitelně: přidání miniatury autora z GitHubu
        avatar_url = latest_commit.get('author', {}).get('avatar_url', "")
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        embed.set_footer(text=f"SHA: {sha[:7]}")

        await channel.send(embed=embed)

    last_commit_sha = sha


@client.event
async def on_ready():
    print(f'Github Watcher připojen jako {client.user}')

    # Inicializace posledního commitu při startu, aby neposlal spam hned po zapnutí
    commits = get_github_commits()
    if commits:
        global last_commit_sha
        last_commit_sha = commits[0]['sha']

    if not check_github_updates.is_running():
        check_github_updates.start()


if __name__ == "__main__":
    client.run(TOKEN)