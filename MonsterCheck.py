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

MY_LOCAL_STORES = {
    "kaufland": "https://maps.app.goo.gl/iYESm2yzmMgG3sPaA",
    "billa": "https://maps.app.goo.gl/hC45MqJidmZLrvPC9",
    "albert": "https://maps.app.goo.gl/5e72mvhfTC5JrGwo7",
    "penny": "https://maps.app.goo.gl/zEo1GrN3NMR4bzHm9",
    "tesco": "https://maps.app.goo.gl/crQd9odvPRKPtDhq6",
    "lidl": "https://maps.app.goo.gl/Sz1sDmxSvdxRyWJS6"
}

TARGET_SHOPS = ["billa", "kaufland", "albert", "penny", "tesco", "lidl"]


def get_store_color(shop_name):
    """Vrátí barvu pro Discord embed podle obchodu."""
    name = shop_name.lower()
    if "kaufland" in name: return 0xDD0000
    if "billa" in name: return 0xFFCC00
    if "albert" in name: return 0x005EB8
    if "penny" in name: return 0xCC0000
    if "tesco" in name: return 0x00539F
    if "lidl" in name: return 0x0050AA
    return 0x2C2F33


def get_my_store_link(shop_name):
    """
    Pokusí se najít tvůj konkrétní odkaz.
    Když ho nenajde, vrátí obecné vyhledávání na mapách.
    """
    name_lower = shop_name.lower()

    # Projdeme tvůj seznam a hledáme shodu
    for key, url in MY_LOCAL_STORES.items():
        if key in name_lower:
            return url

    # Fallback: Pokud obchod nemáš definovaný, vrátí obecné hledání
    return f"https://www.google.com/maps/search/{shop_name}"


def load_json(filename):
    if not os.path.exists(filename): return [] if filename == PRODUCTS_FILE else {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def scrape_url(url):
    """Scrapuje slevy z Kupi.cz."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return []
    except:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found_discounts = []

    # Hledáme obrázky obchodů
    images = soup.find_all("img")

    for img in images:
        alt_text = img.get("alt", "").lower()

        # Zkontrolujeme, zda je to jeden z našich cílových obchodů
        matched_shop = next((s for s in TARGET_SHOPS if s in alt_text), None)

        if not matched_shop: continue

        shop_real_name = img.get("alt")  # Např. "Albert Supermarket"
        parent = img.parent
        price = None
        validity = "Neuvedeno"

        # Prohledáváme rodičovské elementy pro cenu a datum
        for _ in range(4):
            if parent is None: break

            # Hledání ceny
            if not price:
                text = parent.get_text()
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*Kč", text)
                if match: price = float(match.group(1).replace(",", "."))

            # Hledání platnosti
            if validity == "Neuvedeno":
                val_tag = parent.find(class_=re.compile("validity|date"))
                if val_tag: validity = val_tag.get_text(strip=True)

            # Pokud máme cenu, uložíme a končíme hledání u tohoto obrázku
            if price:
                discount_id = f"{matched_shop}_{price}_{validity}"
                found_discounts.append({
                    "id": discount_id,
                    "shop": shop_real_name,
                    "price": price,
                    "validity": validity,
                    "color": get_store_color(shop_real_name)
                })
                break
            parent = parent.parent

    return found_discounts


async def check_discounts(bot_instance):
    """Hlavní funkce volaná z main.py."""
    channel_id = Config.MONSTER_CHANNEL_ID
    if not channel_id:
        print("CHYBA: Není nastaveno MONSTER_CHANNEL_ID v .env")
        return

    channel = bot_instance.get_channel(channel_id)
    if not channel:
        print(f"CHYBA: Kanál s ID {channel_id} nenalezen.")
        return

    products = load_json(PRODUCTS_FILE)
    cache = load_json(CACHE_FILE)

    new_cache = cache.copy()

    for product in products:
        discounts = scrape_url(product['url'])
        if not discounts: continue

        prod_id = product['id']
        if prod_id not in new_cache: new_cache[prod_id] = []

        for d in discounts:
            # Kontrola, zda už jsme slevu neposlali
            if d['id'] in cache.get(prod_id, []):
                continue

            # Získání tvého konkrétního odkazu
            my_link = get_my_store_link(d['shop'])

            embed = discord.Embed(
                title=f"Můj bože ono se to děje **{product['name']}** je ve slevě.",
                description=f"Produkt je ve slevě v obchodě **{d['shop']}**.",
                color=d['color'],
                url=product['url']  # Kliknutí na nadpis vede na Kupi.cz
            )

            # Nastavení obrázku produktu (velký obrázek)
            # Pokud chceš malý vpravo nahoře, použij embed.set_thumbnail(url=...)
            if "image" in product and product["image"]:
                embed.set_thumbnail(url=product["image"])

            embed.add_field(name="Cena", value=f"**{d['price']} Kč**", inline=True)
            embed.add_field(name="Platnost", value=d['validity'], inline=True)

            # Odkaz na tvou prodejnu
            embed.add_field(
                name="Kde to najdeš",
                value=f"[Otevřít mapu k tvé pobočce]({my_link})",
                inline=False
            )

            embed.set_footer(text="MonsterBot Check")

            await channel.send(embed=embed)

            # Přidání do cache
            new_cache[prod_id].append(d['id'])

    save_json(CACHE_FILE, new_cache)