import requests
from config import Config

def get_github_commits(repo_name):
    """Získá seznam commitů pro konkrétní repozitář."""
    url = f"https://api.github.com/repos/{repo_name}/commits"
    headers = {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        print(f"Chyba při volání GitHub API pro {repo_name}: {e}")
        return []