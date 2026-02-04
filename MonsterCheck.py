import requests
from bs4 import BeautifulSoup
import re
import json
import os
import discord
from config import Config

# --- KONFIGURACE ---
PRODUCTS_FILE = "products.json"
CACHE_FILE = "discounts_cache.json"

# --- TVOJE LOKÁLNÍ OBCHODY ---
# (Sem si doplň své odkazy na mapy)
MY_LOCAL_STORES = {
    "kaufland": "https://maps.app.goo.gl/iYESm2yzmMgG3sPaA",
    "billa": "https://maps.app.goo.gl/hC45MqJidmZLrvPC9",
    "albert": "https://maps.app.goo.gl/5e72mvhfTC5JrGwo7",
    "penny": "https://maps.app.goo.gl/zEo1GrN3NMR4bzHm9",
    "tesco": "https://maps.app.goo.gl/crQd9odvPRKPtDhq6",
    "lidl": "https://maps.app.goo.gl/Sz1sDmxSvdxRyWJS6"
}

# --- PRIORITA OBCHODŮ ---
# 1 = Nejvyšší priorita (chci to vidět nejvíc)
# Vyšší číslo = Nižší priorita
STORE_PRIORITY = {
    "billa": 1,
    "albert": 2,
    "tesco": 3,
    "lidl": 4,
    "kaufland": 5,
    "penny": 6
}

TARGET_SHOPS = ["billa", "kaufland", "albert", "penny", "tesco", "lidl"]


def get_store_color(shop_key):
    """Vrátí barvu pro Discord embed podle obchodu."""
    if shop_key == "kaufland": return 0xDD0000
    if shop_key == "billa": return 0xFFCC00
    if shop_key == "albert": return 0x005EB8
    if shop_key == "penny": return 0xCC0000
    if shop_key == "tesco": return 0x00539F
    if shop_key == "lidl": return 0x0050AA
    return 0x2C2F33


def get_my_store_link(shop_key):
    """Vrátí odkaz z tvého seznamu podle klíče obchodu."""
    return MY_LOCAL_STORES.get(shop_key, f"https://www.google.com/maps/search/{shop_key}")


def load_json(filename):
    if not os.path.exists(filename): return [] if filename == PRODUCTS_FILE else {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def scrape_url(url):
    """Stáhne a zpracuje stránku produktu."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return []
    except:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found_discounts = []

    images = soup.find_all("img")

    for img in images:
        alt_text = img.get("alt", "").lower()

        # Zjistíme, který obchod to je (vrátí klíč např. "billa")
        matched_key = next((s for s in TARGET_SHOPS if s in alt_text), None)

        if not matched_key: continue

        shop_display_name = img.get("alt")  # Hezký název z webu
        parent = img.parent
        price = None
        validity = "Neuvedeno"

        for _ in range(4):
            if parent is None: break

            if not price:
                text = parent.get_text()
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*Kč", text)
                if match: price = float(match.group(1).replace(",", "."))

            if validity == "Neuvedeno":
                val_tag = parent.find(class_=re.compile("validity|date"))
                if val_tag: validity = val_tag.get_text(strip=True)

            if price:
                # ID slevy: Obchod + Cena + Platnost
                discount_id = f"{matched_key}_{price}_{validity}"

                if not any(d['id'] == discount_id for d in found_discounts):
                    found_discounts.append({
                        "id": discount_id,
                        "shop_key": matched_key,  # Klíč pro prioritu (billa)
                        "shop_name": shop_display_name,  # Název pro zobrazení (Billa Supermarket)
                        "price": price,
                        "validity": validity,
                        "link": get_my_store_link(matched_key),
                        "color": get_store_color(matched_key),
                        # Defaultně priorita 99, pokud by obchod nebyl v seznamu
                        "priority": STORE_PRIORITY.get(matched_key, 99)
                    })
                break
            parent = parent.parent

    return found_discounts


async def check_discounts(bot_instance):
    """Hlavní funkce - kontroluje slevy."""
    channel_id = Config.MONSTER_CHANNEL_ID
    if not channel_id: return
    channel = bot_instance.get_channel(channel_id)
    if not channel: return

    products = load_json(PRODUCTS_FILE)
    cache = load_json(CACHE_FILE)

    new_cache = cache.copy()
    data_changed = False

    # Procházíme produkt po produktu (co produkt, to max 1 embed)
    for product in products:
        prod_id = product['id']
        if prod_id not in new_cache: new_cache[prod_id] = []

        # 1. Získáme všechny aktuální slevy
        current_discounts = scrape_url(product['url'])
        if not current_discounts: continue

        # 2. Seřadíme slevy podle PRIORITY (1. je nejlepší), poté podle ceny
        # Tím zajistíme, že na indexu [0] bude vždy ten nejvíce prioritní obchod
        current_discounts.sort(key=lambda x: (x['priority'], x['price']))

        # 3. Vybereme VÍTĚZE (ten s nejvyšší prioritou)
        winner = current_discounts[0]

        # 4. Zkontrolujeme, zda už jsme tohoto vítěze neposlali
        # Pokud je vítěz v cache, znamená to, že uživatel o něm ví -> nic neposíláme
        # I kdyby byly slevy v jiných (horších) obchodech, nezajímají nás
        if winner['id'] in new_cache[prod_id]:
            continue

        # 5. Odeslání Embedu
        embed = discord.Embed(
            title=f"{winner['shop_name']}: {product['name']}",
            description=f"Našel jsem slevu v prioritním obchodě.",
            color=winner['color'],
            url=product['url']
        )

        if "image" in product and product["image"]:
            embed.set_thumbnail(url=product["image"])

        # Žádné složité listy, jen data o vítězi
        embed.add_field(name="Cena", value=f"**{winner['price']} Kč**", inline=True)
        embed.add_field(name="Platnost", value=winner['validity'], inline=True)
        embed.add_field(name="Kde", value=f"[Otevřít mapu]({winner['link']})", inline=False)

        embed.set_footer(text="MonsterBot Priority Check")

        await channel.send(embed=embed)

        # 6. Uložíme vítěze do cache
        new_cache[prod_id].append(winner['id'])
        data_changed = True

    # Uložení změn do souboru
    if data_changed:
        save_json(CACHE_FILE, new_cache)