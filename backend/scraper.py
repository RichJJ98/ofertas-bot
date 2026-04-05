import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "application/json, text/html, */*",
}

ML_API  = "https://api.mercadolibre.com"
ML_SITE = "MLB"

# ──────────────────────────────────────────
# Nicknames oficiais no ML (mais estável que seller_id)
# Fonte: mercadolivre.com.br/loja/<nickname>
# ──────────────────────────────────────────
ML_STORES = {
    "KaBuM!":        "KABUM-COMERCIO-ELETRONICO",
    "Terabyte Shop": "TERABYTESHOP",
    "Pichau":        "PICHAU",
    "Amazon BR":     "AMAZON-IMPORTADOS",
}

# Fallback: queries de tech quando lojas específicas falharem
ML_TECH_QUERIES = [
    "placa de video rtx",
    "processador amd ryzen",
    "processador intel",
    "memoria ram ddr4 ddr5",
    "ssd nvme m2",
    "headset gamer",
    "monitor gamer",
    "fonte atx modular",
    "placa mae gaming",
    "cooler cpu water cooler",
    "notebook gamer",
    "teclado gamer mecanico",
    "mouse gamer",
]

ML_GAMES_QUERIES = [
    "jogo ps5 novo",
    "jogo xbox series",
    "jogo nintendo switch",
    "controle ps5 dualsense",
    "controle xbox series",
]


def _to_offer(item, source, category):
    try:
        price = float(item.get("price") or 0)
        orig  = float(item.get("original_price") or 0)
        orig  = orig if orig > price else None
        disc  = int(round((1 - price / orig) * 100)) if orig else None
        thumb = (item.get("thumbnail") or "").replace("http://", "https://")
        thumb = thumb.replace("-I.jpg", "-O.jpg")  # imagem maior
        if price <= 0:
            return None
        return {
            "title":          item.get("title", "").strip(),
            "price":          price,
            "original_price": orig,
            "discount":       disc,
            "url":            item.get("permalink", ""),
            "image":          thumb,
            "source":         source,
            "category":       category,
            "timestamp":      datetime.now().isoformat(),
        }
    except Exception:
        return None


def _ml_search(params, label="ML"):
    """Wrapper genérico para a API de busca do ML."""
    try:
        r = requests.get(
            f"{ML_API}/sites/{ML_SITE}/search",
            params=params,
            headers=HEADERS,
            timeout=14,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception as e:
        print(f"     [{label}] Erro na API: {e}")
        return []


def _resolve_seller_id(nickname):
    """Converte nickname para seller_id numérico via API do ML."""
    try:
        r = requests.get(
            f"{ML_API}/sites/{ML_SITE}/search",
            params={"nickname": nickname, "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            sid = results[0].get("seller", {}).get("id")
            if sid:
                print(f"     Resolvido: {nickname} → seller_id={sid}")
                return sid
    except Exception as e:
        print(f"     Falha ao resolver {nickname}: {e}")
    return None


def scrape_ml_store(store_name, nickname, category="tech", max_items=25):
    """Busca produtos em promoção de uma loja oficial do ML pelo nickname."""
    offers = []

    # Tenta resolver o seller_id pelo nickname
    seller_id = _resolve_seller_id(nickname)

    if seller_id:
        # Busca produtos da loja com filtro de desconto implícito
        results = _ml_search(
            {"seller_id": seller_id, "sort": "price_asc", "limit": 50},
            label=store_name,
        )
        for item in results:
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                o = _to_offer(item, source=store_name, category=category)
                if o:
                    offers.append(o)
            if len(offers) >= max_items:
                break
    else:
        # Fallback: busca pelo nickname como query
        results = _ml_search(
            {"nickname": nickname, "limit": 50},
            label=f"{store_name} (fallback nickname)",
        )
        for item in results:
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                o = _to_offer(item, source=store_name, category=category)
                if o:
                    offers.append(o)
            if len(offers) >= max_items:
                break

    print(f"     [{store_name}] {len(offers)} ofertas com desconto")
    return offers


def scrape_ml_tech_queries():
    """Busca geral de tech com desconto real no ML — fallback robusto."""
    offers = []
    for query in ML_TECH_QUERIES:
        results = _ml_search(
            {"q": query, "sort": "relevance", "limit": 8},
            label=f"ML Tech '{query}'",
        )
        for item in results:
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                disc = int(round((1 - float(p) / float(op)) * 100))
                if disc >= 10:  # Só descontos relevantes
                    o = _to_offer(item, source="Mercado Livre", category="tech")
                    if o:
                        offers.append(o)
        time.sleep(0.25)
    print(f"     [ML Tech Queries] {len(offers)} ofertas encontradas")
    return offers


def scrape_ml_games_queries():
    """Busca jogos físicos com desconto no ML."""
    offers = []
    for query in ML_GAMES_QUERIES:
        results = _ml_search(
            {"q": query, "sort": "relevance", "limit": 6},
            label=f"ML Games '{query}'",
        )
        for item in results:
            op = item.get("original_price")
            p  = item.get("price", 0)
            if op and float(op) > float(p):
                o = _to_offer(item, source="Mercado Livre", category="games")
                if o:
                    offers.append(o)
        time.sleep(0.25)
    print(f"     [ML Games Queries] {len(offers)} ofertas encontradas")
    return offers


# ──────────────────────────────────────────
# STEAM
# ──────────────────────────────────────────
def scrape_steam_sales():
    offers = []
    try:
        url = "https://store.steampowered.com/api/featuredcategories?cc=BR&l=portuguese"
        r = requests.get(url, headers=HEADERS, timeout=12)
        data = r.json()
        specials = data.get("specials", {}).get("items", [])
        for item in specials[:30]:
            orig  = (item.get("original_price") or 0) / 100
            final = (item.get("final_price") or 0) / 100
            disc  = item.get("discount_percent", 0)
            if final <= 0:
                continue
            offers.append({
                "title":          item.get("name", ""),
                "price":          final,
                "original_price": orig if orig != final else None,
                "discount":       disc if disc > 0 else None,
                "url":            f"https://store.steampowered.com/app/{item.get('id','')}",
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
            title_el = card.select_one("h3, h2, .product-card--title")
            price_el  = card.select_one(".product-card--price, .price-discount, .price")
            orig_el   = card.select_one(".product-card--original-price, .price-original")
            disc_el   = card.select_one(".discount-tag, .discount, .badge-discount")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el:
                continue
            def cn(t):
                if not t: return 0
                n = re.sub(r"[^\d,]", "", t).replace(",", ".")
                try: return float(n)
                except: return 0
            pv = cn(price_el.get_text() if price_el else "")
            ov = cn(orig_el.get_text() if orig_el else "") or None
            dn = re.sub(r"[^\d]", "", disc_el.get_text(strip=True) if disc_el else "")
            if pv <= 0: continue
            href = link_el["href"] if link_el else url
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          pv,
                "original_price": ov,
                "discount":       int(dn) if dn else None,
                "url":            href if href.startswith("http") else "https://www.nuuvem.com" + href,
                "image":          img_el.get("src", img_el.get("data-src","")) if img_el else "",
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
        cards = soup.select(".item.mainshadow, .game-card, .listing-item")
        for card in cards[:25]:
            title_el = card.select_one(".title, h3")
            price_el  = card.select_one(".price, .bestprice")
            disc_el   = card.select_one(".discount, .perc")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el: continue
            pn = re.sub(r"[^\d,\.]", "", price_el.get_text(strip=True) if price_el else "0")
            dn = re.sub(r"[^\d]", "", disc_el.get_text(strip=True) if disc_el else "")
            try:
                pv = float(pn.replace(",", ".")) if pn else 0
                dv = int(dn) if dn else None
            except: pv, dv = 0, None
            if pv <= 0: continue
            href = link_el["href"] if link_el else url
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          pv,
                "original_price": None,
                "discount":       dv,
                "url":            href if href.startswith("http") else "https://www.instant-gaming.com" + href,
                "image":          img_el.get("src", img_el.get("data-src","")) if img_el else "",
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
        cards = soup.select(".product-tile, .game-tile, article.game")
        for card in cards[:20]:
            title_el = card.select_one("h3, h2, .product-name")
            price_el  = card.select_one(".price, .sale-price")
            disc_el   = card.select_one(".discount, .saving")
            link_el   = card.select_one("a")
            img_el    = card.select_one("img")
            if not title_el: continue
            pn = re.sub(r"[^\d\.]", "", price_el.get_text(strip=True) if price_el else "0")
            dn = re.sub(r"[^\d]", "", disc_el.get_text(strip=True) if disc_el else "")
            try:
                pv = float(pn) if pn else 0
                dv = int(dn) if dn else None
            except: pv, dv = 0, None
            if pv <= 0: continue
            href = link_el["href"] if link_el else url
            offers.append({
                "title":          title_el.get_text(strip=True),
                "price":          pv,
                "original_price": None,
                "discount":       dv,
                "url":            href if href.startswith("http") else "https://www.greenmangaming.com" + href,
                "image":          img_el.get("src","") if img_el else "",
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

    # 1. Lojas de tech via ML (KaBuM, Terabyte, Pichau, Amazon)
    print("  -> Coletando lojas tech no ML...")
    for name, nick in ML_STORES.items():
        result = scrape_ml_store(name, nick, category="tech", max_items=25)
        all_offers.extend(result)
        time.sleep(0.5)

    # 2. Queries de tech no ML geral (fallback + complemento)
    print("  -> Coletando tech por queries no ML...")
    all_offers.extend(scrape_ml_tech_queries())

    # 3. Jogos físicos no ML
    print("  -> Coletando jogos físicos no ML...")
    all_offers.extend(scrape_ml_games_queries())

    # 4. Jogos digitais
    print("  -> Coletando Steam...")
    all_offers.extend(scrape_steam_sales())

    print("  -> Coletando Nuuvem...")
    all_offers.extend(scrape_nuuvem())

    print("  -> Coletando Instant Gaming...")
    all_offers.extend(scrape_instant_gaming())

    print("  -> Coletando Green Man Gaming...")
    all_offers.extend(scrape_green_man_gaming())

    # Deduplicação por URL
    seen = set()
    unique = []
    for o in all_offers:
        key = o.get("url", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(o)

    # Remove sem preço e sem título
    unique = [o for o in unique if o.get("price", 0) > 0 and o.get("title")]

    print(f"[BOT] Total: {len(unique)} ofertas únicas")
    return unique


if __name__ == "__main__":
    import os
    offers = run_all_scrapers()
    out = os.path.join(os.path.dirname(__file__), "../data/offers.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    print(f"[BOT] Salvo em data/offers.json")
