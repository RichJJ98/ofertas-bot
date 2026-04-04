import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "application/json, text/html, */*",
}

# ──────────────────────────────────────────
# MERCADO LIVRE — API pública oficial
# Docs: https://developers.mercadolibre.com.br
# ──────────────────────────────────────────

ML_SITE = "MLB"  # Brasil
ML_API  = "https://api.mercadolibre.com"

# IDs oficiais das lojas no ML (seller_id)
ML_SELLERS = {
    "KaBuM!":        "281051892",
    "Terabyte Shop": "239729076",
    "Pichau":        "340934064",
    "Amazon BR":     "36440183",
}

# Queries de busca por categoria
ML_TECH_QUERIES = [
    "placa de video",
    "processador",
    "memoria ram",
    "ssd nvme",
    "headset gamer",
    "monitor gamer",
    "fonte atx",
    "placa mae",
    "gabinete gamer",
    "cooler cpu",
    "teclado gamer",
    "mouse gamer",
    "notebook gamer",
]

ML_GAMES_QUERIES = [
    "jogo ps5",
    "jogo xbox",
    "jogo nintendo switch",
    "controle ps5",
    "controle xbox",
]


def _ml_item_to_offer(item, source="Mercado Livre", category="tech"):
    """Converte um item da API ML para o formato padrão do bot."""
    try:
        price      = float(item.get("price") or 0)
        orig       = float(item.get("original_price") or 0)
        orig       = orig if orig > price else None
        discount   = int(round((1 - price / orig) * 100)) if orig and orig > 0 else None
        thumbnail  = item.get("thumbnail", "").replace("http://", "https://")
        # Thumbnail ML vem em baixa resolução — upgradeia para tamanho maior
        thumbnail  = thumbnail.replace("-I.jpg", "-O.jpg") if thumbnail else ""
        return {
            "title":          item.get("title", ""),
            "price":          price,
            "original_price": orig,
            "discount":       discount,
            "url":            item.get("permalink", ""),
            "image":          thumbnail,
            "source":         source,
            "category":       category,
            "timestamp":      datetime.now().isoformat(),
        }
    except Exception:
        return None


def scrape_ml_seller(seller_name, seller_id, category="tech", max_items=30):
    """Busca produtos em promoção de uma loja específica do ML."""
    offers = []
    try:
        # Busca itens do vendedor com desconto (original_price preenchido = em promoção)
        url = (
            f"{ML_API}/sites/{ML_SITE}/search"
            f"?seller_id={seller_id}"
            f"&sort=price_asc"
            f"&limit=50"
        )
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        for item in results:
            # Só inclui se tiver desconto real
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                offer = _ml_item_to_offer(item, source=seller_name, category=category)
                if offer and offer["title"] and offer["price"] > 0:
                    offers.append(offer)
            if len(offers) >= max_items:
                break
        print(f"     [{seller_name}] {len(offers)} ofertas com desconto")
    except Exception as e:
        print(f"     [{seller_name}] Erro: {e}")
    return offers


def scrape_ml_tech_deals():
    """Busca as melhores ofertas de tech no ML geral + lojas específicas."""
    offers = []

    # 1. Lojas específicas (KaBuM, Terabyte, Pichau, Amazon)
    for name, sid in ML_SELLERS.items():
        cat = "tech"
        result = scrape_ml_seller(name, sid, category=cat, max_items=20)
        offers.extend(result)
        time.sleep(0.5)

    # 2. Busca geral por queries de tech com filtro de desconto
    for query in ML_TECH_QUERIES[:6]:  # Limita pra não bater rate limit
        try:
            url = (
                f"{ML_API}/sites/{ML_SITE}/search"
                f"?q={requests.utils.quote(query)}"
                f"&sort=relevance"
                f"&limit=10"
            )
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                op = item.get("original_price")
                p  = item.get("price", 0)
                if op and float(op) > float(p):
                    offer = _ml_item_to_offer(item, source="Mercado Livre", category="tech")
                    if offer and offer["title"] and offer["price"] > 0:
                        offers.append(offer)
            time.sleep(0.3)
        except Exception as e:
            print(f"     [ML Tech '{query}'] Erro: {e}")

    return offers


def scrape_ml_games():
    """Busca jogos físicos em promoção no ML."""
    offers = []
    for query in ML_GAMES_QUERIES:
        try:
            url = (
                f"{ML_API}/sites/{ML_SITE}/search"
                f"?q={requests.utils.quote(query)}"
                f"&sort=relevance"
                f"&limit=10"
            )
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                op = item.get("original_price")
                p  = item.get("price", 0)
                if op and float(op) > float(p):
                    offer = _ml_item_to_offer(item, source="Mercado Livre", category="games")
                    if offer and offer["title"] and offer["price"] > 0:
                        offers.append(offer)
            time.sleep(0.3)
        except Exception as e:
            print(f"     [ML Games '{query}'] Erro: {e}")
    return offers


def scrape_ml_featured_deals():
    """Pega as ofertas em destaque do ML Brasil (página de promoções)."""
    offers = []
    try:
        # Endpoint de ofertas relâmpago / destaques
        url = f"{ML_API}/sites/{ML_SITE}/search?q=tech&sort=discount_asc&limit=50"
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        data = r.json()
        for item in data.get("results", []):
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                disc = int(round((1 - float(p) / float(op)) * 100))
                if disc >= 15:  # Só descontos relevantes
                    offer = _ml_item_to_offer(item, source="Mercado Livre", category="tech")
                    if offer:
                        offers.append(offer)
    except Exception as e:
        print(f"     [ML Featured] Erro: {e}")
    return offers


# ──────────────────────────────────────────
# STEAM — API pública oficial
# ──────────────────────────────────────────

def scrape_steam_sales():
    offers = []
    try:
        url = "https://store.steampowered.com/api/featuredcategories?cc=BR&l=portuguese"
        r = requests.get(url, headers=HEADERS, timeout=12)
        data = r.json()
        specials = data.get("specials", {}).get("items", [])
        for item in specials[:30]:
            orig  = item.get("original_price", 0) / 100 if item.get("original_price") else 0
            final = item.get("final_price", 0) / 100 if item.get("final_price") else 0
            disc  = item.get("discount_percent", 0)
            if final <= 0:
                continue
            offers.append({
                "title":          item.get("name", ""),
                "price":          final,
                "original_price": orig if orig != final else None,
                "discount":       disc if disc > 0 else None,
                "url":            f"https://store.steampowered.com/app/{item.get('id', '')}",
                "image":          item.get("header_image", ""),
                "source":         "Steam",
                "category":       "games",
                "timestamp":      datetime.now().isoformat(),
            })
        print(f"     [Steam] {len(offers)} ofertas")
    except Exception as e:
        print(f"     [Steam] Erro: {e}")
    return offers


# ──────────────────────────────────────────
# NUUVEM
# ──────────────────────────────────────────

def scrape_nuuvem():
    offers = []
    try:
        url = "https://www.nuuvem.com/br-en/catalog/prices/between/drm/steam,gog,other,rockstar,battlenet,epicgames,origin,uplay/sort/discount/direction/desc/view/grid"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".product-card--grid, .product-card, article")
        for card in cards[:25]:
            title_el = card.select_one("h3, h2, .product-card--title, .game-title")
            price_el  = card.select_one(".product-card--price, .price-discount, .price")
            orig_el   = card.select_one(".product-card--original-price, .price-original")
            disc_el   = card.select_one(".discount-tag, .discount, .badge-discount")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el:
                continue
            import re
            def clean_num(t):
                if not t: return 0
                n = re.sub(r"[^\d,]", "", t).replace(",", ".")
                try: return float(n)
                except: return 0
            price_val = clean_num(price_el.get_text() if price_el else "")
            orig_val  = clean_num(orig_el.get_text() if orig_el else "") or None
            disc_text = disc_el.get_text(strip=True) if disc_el else ""
            disc_num  = re.sub(r"[^\d]", "", disc_text)
            disc_val  = int(disc_num) if disc_num else None
            if price_val <= 0:
                continue
            href = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else "https://www.nuuvem.com" + href
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          price_val,
                "original_price": orig_val,
                "discount":       disc_val,
                "url":            full_url,
                "image":          img_el.get("src", img_el.get("data-src", "")) if img_el else "",
                "source":         "Nuuvem",
                "category":       "games",
                "timestamp":      datetime.now().isoformat(),
            })
        print(f"     [Nuuvem] {len(offers)} ofertas")
    except Exception as e:
        print(f"     [Nuuvem] Erro: {e}")
    return offers


# ──────────────────────────────────────────
# INSTANT GAMING
# ──────────────────────────────────────────

def scrape_instant_gaming():
    offers = []
    try:
        url = "https://www.instant-gaming.com/en/?type[]=steam&type[]=gog&currency=BRL&sort_by=discount"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        import re
        cards = soup.select(".item.mainshadow, .game-card, .listing-item")
        for card in cards[:25]:
            title_el = card.select_one(".title, .game-title, h3")
            price_el  = card.select_one(".price, .current-price, .bestprice")
            disc_el   = card.select_one(".discount, .promo, .perc")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el:
                continue
            price_text = price_el.get_text(strip=True) if price_el else "0"
            price_num  = re.sub(r"[^\d,\.]", "", price_text)
            disc_text  = disc_el.get_text(strip=True) if disc_el else ""
            disc_num   = re.sub(r"[^\d]", "", disc_text)
            try:
                price_val = float(price_num.replace(",", ".")) if price_num else 0
                disc_val  = int(disc_num) if disc_num else None
            except Exception:
                price_val, disc_val = 0, None
            if price_val <= 0:
                continue
            href = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else "https://www.instant-gaming.com" + href
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          price_val,
                "original_price": None,
                "discount":       disc_val,
                "url":            full_url,
                "image":          img_el.get("src", img_el.get("data-src", "")) if img_el else "",
                "source":         "Instant Gaming",
                "category":       "games",
                "timestamp":      datetime.now().isoformat(),
            })
        print(f"     [Instant Gaming] {len(offers)} ofertas")
    except Exception as e:
        print(f"     [Instant Gaming] Erro: {e}")
    return offers


# ──────────────────────────────────────────
# GREEN MAN GAMING
# ──────────────────────────────────────────

def scrape_green_man_gaming():
    offers = []
    try:
        url = "https://www.greenmangaming.com/sale/"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        import re
        cards = soup.select(".product-tile, .game-tile, article.game")
        for card in cards[:20]:
            title_el = card.select_one("h3, h2, .product-name, .game-name")
            price_el  = card.select_one(".price, .sale-price, .current-price")
            disc_el   = card.select_one(".discount, .saving, .off-amount")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el:
                continue
            price_text = price_el.get_text(strip=True) if price_el else "0"
            price_num  = re.sub(r"[^\d\.]", "", price_text)
            disc_text  = disc_el.get_text(strip=True) if disc_el else ""
            disc_num   = re.sub(r"[^\d]", "", disc_text)
            try:
                price_val = float(price_num) if price_num else 0
                disc_val  = int(disc_num) if disc_num else None
            except Exception:
                price_val, disc_val = 0, None
            if price_val <= 0:
                continue
            href = link_el["href"] if link_el else url
            full_url = href if href.startswith("http") else "https://www.greenmangaming.com" + href
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          price_val,
                "original_price": None,
                "discount":       disc_val,
                "url":            full_url,
                "image":          img_el.get("src", "") if img_el else "",
                "source":         "Green Man Gaming",
                "category":       "games",
                "timestamp":      datetime.now().isoformat(),
            })
        print(f"     [Green Man Gaming] {len(offers)} ofertas")
    except Exception as e:
        print(f"     [Green Man Gaming] Erro: {e}")
    return offers


# ──────────────────────────────────────────
# RUNNER PRINCIPAL
# ──────────────────────────────────────────

def run_all_scrapers():
    print("[BOT] Iniciando coleta de ofertas...")
    all_offers = []

    scrapers = [
        # Tech via ML (KaBuM, Terabyte, Pichau, Amazon, ML geral)
        ("ML — KaBuM / Terabyte / Tech",  scrape_ml_tech_deals),
        ("ML — Jogos físicos",             scrape_ml_games),
        # Jogos digitais
        ("Steam",                          scrape_steam_sales),
        ("Nuuvem",                         scrape_nuuvem),
        ("Instant Gaming",                 scrape_instant_gaming),
        ("Green Man Gaming",               scrape_green_man_gaming),
    ]

    for name, fn in scrapers:
        print(f"  -> Coletando {name}...")
        try:
            result = fn()
            all_offers.extend(result)
        except Exception as e:
            print(f"     ERRO geral: {e}")

    # Deduplicação por URL
    seen = set()
    unique = []
    for o in all_offers:
        key = o.get("url", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(o)

    # Remove entradas sem preço e sem desconto
    unique = [o for o in unique if o.get("price", 0) > 0 or o.get("discount")]

    print(f"[BOT] Total: {len(unique)} ofertas únicas coletadas")
    return unique


if __name__ == "__main__":
    import os
    offers = run_all_scrapers()
    out = os.path.join(os.path.dirname(__file__), "../data/offers.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    print(f"[BOT] Salvo em data/offers.json")
