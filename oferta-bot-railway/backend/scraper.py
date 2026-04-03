import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape_pelando_tech():
    """Scrapa ofertas de tecnologia do Pelando"""
    offers = []
    urls = [
        "https://www.pelando.com.br/category/eletronicos",
        "https://www.pelando.com.br/category/games",
        "https://www.pelando.com.br/category/informatica",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            # Pelando usa JSON-LD / estrutura de dados embutida
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "Product":
                                offers.append({
                                    "title": item.get("name", ""),
                                    "price": item.get("offers", {}).get("price", 0),
                                    "original_price": None,
                                    "discount": None,
                                    "url": item.get("url", url),
                                    "image": item.get("image", ""),
                                    "source": "Pelando",
                                    "category": "tech",
                                    "timestamp": datetime.now().isoformat(),
                                })
                except Exception:
                    pass
            # fallback: cards HTML
            cards = soup.select("article, [data-testid='deal-card'], .deal-card")
            for card in cards[:10]:
                title_el = card.select_one("h2, h3, [data-testid='deal-title'], .deal-title")
                price_el = card.select_one("[data-testid='deal-price'], .price, .deal-price")
                link_el = card.select_one("a")
                img_el = card.select_one("img")
                if title_el:
                    price_text = price_el.get_text(strip=True) if price_el else "0"
                    price_num = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
                    try:
                        price_val = float(price_num) if price_num else 0
                    except Exception:
                        price_val = 0
                    offers.append({
                        "title": title_el.get_text(strip=True),
                        "price": price_val,
                        "original_price": None,
                        "discount": None,
                        "url": "https://www.pelando.com.br" + link_el["href"] if link_el and link_el.get("href", "").startswith("/") else (link_el["href"] if link_el else url),
                        "image": img_el.get("src", "") if img_el else "",
                        "source": "Pelando",
                        "category": "tech",
                        "timestamp": datetime.now().isoformat(),
                    })
            time.sleep(1)
        except Exception as e:
            print(f"[PELANDO] Erro: {e}")
    return offers


def scrape_nuuvem():
    """Scrapa promoções da Nuuvem"""
    offers = []
    try:
        url = "https://www.nuuvem.com/br-en/catalog/prices/between/drm/steam,gog,other,rockstar,battlenet,epicgames,origin,uplay,windows-store/sort/discount/direction/desc/view/grid"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".product-card, .game-card, article")
        for card in cards[:20]:
            title_el = card.select_one("h3, h2, .product-card--title, .game-title")
            price_el = card.select_one(".product-card--price, .price-discount, .price")
            orig_el = card.select_one(".product-card--original-price, .price-original, .original-price")
            disc_el = card.select_one(".discount-tag, .discount, .badge-discount")
            link_el = card.select_one("a")
            img_el = card.select_one("img")
            if title_el:
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_num = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
                orig_text = orig_el.get_text(strip=True) if orig_el else ""
                orig_num = re.sub(r"[^\d,]", "", orig_text).replace(",", ".")
                disc_text = disc_el.get_text(strip=True) if disc_el else ""
                try:
                    price_val = float(price_num) if price_num else 0
                    orig_val = float(orig_num) if orig_num else None
                    disc_val = re.sub(r"[^\d]", "", disc_text)
                    disc_val = int(disc_val) if disc_val else None
                except Exception:
                    price_val, orig_val, disc_val = 0, None, None
                href = link_el["href"] if link_el else url
                full_url = href if href.startswith("http") else "https://www.nuuvem.com" + href
                offers.append({
                    "title": title_el.get_text(strip=True),
                    "price": price_val,
                    "original_price": orig_val,
                    "discount": disc_val,
                    "url": full_url,
                    "image": img_el.get("src", img_el.get("data-src", "")) if img_el else "",
                    "source": "Nuuvem",
                    "category": "games",
                    "timestamp": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[NUUVEM] Erro: {e}")
    return offers


def scrape_steam_sales():
    """Scrapa promoções da Steam via API pública"""
    offers = []
    try:
        url = "https://store.steampowered.com/api/featuredcategories?cc=BR&l=portuguese"
        r = requests.get(url, headers=HEADERS, timeout=12)
        data = r.json()
        specials = data.get("specials", {}).get("items", [])
        for item in specials[:20]:
            orig = item.get("original_price", 0) / 100 if item.get("original_price") else 0
            final = item.get("final_price", 0) / 100 if item.get("final_price") else 0
            disc = item.get("discount_percent", 0)
            app_id = item.get("id", "")
            offers.append({
                "title": item.get("name", ""),
                "price": final,
                "original_price": orig if orig != final else None,
                "discount": disc if disc > 0 else None,
                "url": f"https://store.steampowered.com/app/{app_id}",
                "image": item.get("header_image", ""),
                "source": "Steam",
                "category": "games",
                "timestamp": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[STEAM] Erro: {e}")
    return offers


def scrape_instant_gaming():
    """Scrapa promoções do Instant Gaming"""
    offers = []
    try:
        url = "https://www.instant-gaming.com/en/?type[]=steam&type[]=origin&type[]=gog&type[]=uplay&currency=BRL&sort_by=discount"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".item.mainshadow, .game-card")
        for card in cards[:20]:
            title_el = card.select_one(".title, .game-title, h3")
            price_el = card.select_one(".price, .current-price, .bestprice")
            disc_el = card.select_one(".discount, .promo, .perc")
            link_el = card.select_one("a")
            img_el = card.select_one("img")
            if title_el:
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_num = re.sub(r"[^\d,\.]", "", price_text)
                disc_text = disc_el.get_text(strip=True) if disc_el else ""
                disc_num = re.sub(r"[^\d]", "", disc_text)
                try:
                    price_val = float(price_num.replace(",", ".")) if price_num else 0
                    disc_val = int(disc_num) if disc_num else None
                except Exception:
                    price_val, disc_val = 0, None
                href = link_el["href"] if link_el else url
                full_url = href if href.startswith("http") else "https://www.instant-gaming.com" + href
                offers.append({
                    "title": title_el.get_text(strip=True),
                    "price": price_val,
                    "original_price": None,
                    "discount": disc_val,
                    "url": full_url,
                    "image": img_el.get("src", img_el.get("data-src", "")) if img_el else "",
                    "source": "Instant Gaming",
                    "category": "games",
                    "timestamp": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[INSTANT GAMING] Erro: {e}")
    return offers


def scrape_green_man_gaming():
    """Scrapa promoções do Green Man Gaming"""
    offers = []
    try:
        url = "https://www.greenmangaming.com/sale/"
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".product-tile, .game-tile, article.game")
        for card in cards[:20]:
            title_el = card.select_one("h3, h2, .product-name, .game-name")
            price_el = card.select_one(".price, .sale-price, .current-price")
            disc_el = card.select_one(".discount, .saving, .off-amount")
            link_el = card.select_one("a")
            img_el = card.select_one("img")
            if title_el:
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_num = re.sub(r"[^\d\.]", "", price_text)
                disc_text = disc_el.get_text(strip=True) if disc_el else ""
                disc_num = re.sub(r"[^\d]", "", disc_text)
                try:
                    price_val = float(price_num) if price_num else 0
                    disc_val = int(disc_num) if disc_num else None
                except Exception:
                    price_val, disc_val = 0, None
                href = link_el["href"] if link_el else url
                full_url = href if href.startswith("http") else "https://www.greenmangaming.com" + href
                offers.append({
                    "title": title_el.get_text(strip=True),
                    "price": price_val,
                    "original_price": None,
                    "discount": disc_val,
                    "url": full_url,
                    "image": img_el.get("src", "") if img_el else "",
                    "source": "Green Man Gaming",
                    "category": "games",
                    "timestamp": datetime.now().isoformat(),
                })
    except Exception as e:
        print(f"[GREEN MAN GAMING] Erro: {e}")
    return offers


def scrape_kabum():
    """Scrapa promoções de hardware/tech do KaBuM!"""
    offers = []
    try:
        urls = [
            ("https://www.kabum.com.br/hardware/placa-de-video-vga", "Placa de Vídeo"),
            ("https://www.kabum.com.br/hardware/processadores", "Processadores"),
            ("https://www.kabum.com.br/hardware/memorias-ram", "Memória RAM"),
            ("https://www.kabum.com.br/hardware/ssd-2-5", "SSD"),
            ("https://www.kabum.com.br/games/headsets-gamer", "Headset"),
        ]
        for url, cat in urls:
            r = requests.get(url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            # KaBuM usa script com __NEXT_DATA__
            next_data = soup.find("script", id="__NEXT_DATA__")
            if next_data:
                try:
                    ndata = json.loads(next_data.string)
                    products = (
                        ndata.get("props", {})
                        .get("pageProps", {})
                        .get("data", {})
                        .get("catalogV2", {})
                        .get("products", [])
                    )
                    for p in products[:5]:
                        price_info = p.get("priceDetails", {})
                        current = price_info.get("finalPrice", 0)
                        original = price_info.get("oldPrice", None)
                        disc = price_info.get("discount", None)
                        offers.append({
                            "title": p.get("title", ""),
                            "price": float(current) if current else 0,
                            "original_price": float(original) if original else None,
                            "discount": int(disc) if disc else None,
                            "url": f"https://www.kabum.com.br/produto/{p.get('code', '')}",
                            "image": p.get("images", [{}])[0].get("path", "") if p.get("images") else "",
                            "source": "KaBuM!",
                            "category": "tech",
                            "timestamp": datetime.now().isoformat(),
                        })
                except Exception:
                    pass
            # fallback HTML
            cards = soup.select("[data-testid='product-card'], .productCard, article")
            for card in cards[:5]:
                title_el = card.select_one("h2, span.nameCard, .product-title")
                price_el = card.select_one(".priceCard, .price, [data-testid='price']")
                link_el = card.select_one("a")
                img_el = card.select_one("img")
                if title_el:
                    price_text = price_el.get_text(strip=True) if price_el else "0"
                    price_num = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
                    try:
                        price_val = float(price_num) if price_num else 0
                    except Exception:
                        price_val = 0
                    href = link_el["href"] if link_el else url
                    full_url = href if href.startswith("http") else "https://www.kabum.com.br" + href
                    offers.append({
                        "title": title_el.get_text(strip=True),
                        "price": price_val,
                        "original_price": None,
                        "discount": None,
                        "url": full_url,
                        "image": img_el.get("src", "") if img_el else "",
                        "source": "KaBuM!",
                        "category": "tech",
                        "timestamp": datetime.now().isoformat(),
                    })
            time.sleep(1.5)
    except Exception as e:
        print(f"[KABUM] Erro: {e}")
    return offers


def scrape_terabyteshop():
    """Scrapa promoções da Terabyte Shop"""
    offers = []
    try:
        urls = [
            "https://www.terabyteshop.com.br/promocoes",
            "https://www.terabyteshop.com.br/hardware/placas-de-video",
        ]
        for url in urls:
            r = requests.get(url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.select(".pbox, .product-item, article.product")
            for card in cards[:10]:
                title_el = card.select_one("h3, h2, .prod-name, .product-name")
                price_el = card.select_one(".prod-new-price, .price, .current-price")
                old_el = card.select_one(".prod-old-price, .old-price, .original-price")
                link_el = card.select_one("a")
                img_el = card.select_one("img")
                if title_el:
                    price_text = price_el.get_text(strip=True) if price_el else "0"
                    price_num = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
                    orig_text = old_el.get_text(strip=True) if old_el else ""
                    orig_num = re.sub(r"[^\d,]", "", orig_text).replace(",", ".")
                    try:
                        price_val = float(price_num) if price_num else 0
                        orig_val = float(orig_num) if orig_num else None
                        disc_val = int((1 - price_val/orig_val)*100) if orig_val and orig_val > price_val else None
                    except Exception:
                        price_val, orig_val, disc_val = 0, None, None
                    href = link_el["href"] if link_el else url
                    full_url = href if href.startswith("http") else "https://www.terabyteshop.com.br" + href
                    offers.append({
                        "title": title_el.get_text(strip=True),
                        "price": price_val,
                        "original_price": orig_val,
                        "discount": disc_val,
                        "url": full_url,
                        "image": img_el.get("src", "") if img_el else "",
                        "source": "Terabyte Shop",
                        "category": "tech",
                        "timestamp": datetime.now().isoformat(),
                    })
            time.sleep(1)
    except Exception as e:
        print(f"[TERABYTE] Erro: {e}")
    return offers


def run_all_scrapers():
    print("[BOT] Iniciando coleta de ofertas...")
    all_offers = []
    scrapers = [
        ("Steam", scrape_steam_sales),
        ("Nuuvem", scrape_nuuvem),
        ("Instant Gaming", scrape_instant_gaming),
        ("Green Man Gaming", scrape_green_man_gaming),
        ("KaBuM!", scrape_kabum),
        ("Terabyte Shop", scrape_terabyteshop),
        ("Pelando", scrape_pelando_tech),
    ]
    for name, fn in scrapers:
        print(f"  -> Coletando {name}...")
        try:
            result = fn()
            all_offers.extend(result)
            print(f"     {len(result)} ofertas encontradas")
        except Exception as e:
            print(f"     ERRO: {e}")
    # Remove duplicatas por título + fonte
    seen = set()
    unique = []
    for o in all_offers:
        key = (o["source"], o["title"][:50].lower())
        if key not in seen:
            seen.add(key)
            unique.append(o)
    # Filtra preços zerados (provavelmente falhou)
    unique = [o for o in unique if o["price"] > 0 or o["discount"]]
    print(f"[BOT] Total: {len(unique)} ofertas únicas coletadas")
    return unique


if __name__ == "__main__":
    offers = run_all_scrapers()
    with open("../data/offers.json", "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    print("[BOT] Salvo em data/offers.json")
