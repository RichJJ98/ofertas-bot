from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import threading
import time
from datetime import datetime
from scraper import run_all_scrapers

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

DATA_FILE = os.path.join(BASE_DIR, "data", "offers.json")
CACHE = {"offers": [], "last_update": None, "is_running": False}

def load_offers():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_offers(offers):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

def refresh_offers():
    if CACHE["is_running"]:
        return
    CACHE["is_running"] = True
    try:
        offers = run_all_scrapers()
        save_offers(offers)
        CACHE["offers"] = offers
        CACHE["last_update"] = datetime.now().isoformat()
    finally:
        CACHE["is_running"] = False

def auto_refresh_loop(interval=1800):
    """Atualiza a cada 30 min por padrão"""
    while True:
        refresh_offers()
        time.sleep(interval)

@app.route("/api/offers")
def get_offers():
    if not CACHE["offers"]:
        CACHE["offers"] = load_offers()
    
    offers = CACHE["offers"]
    
    # Filtros
    category = request.args.get("category")
    source = request.args.get("source")
    min_discount = request.args.get("min_discount", type=int)
    max_price = request.args.get("max_price", type=float)
    search = request.args.get("q", "").lower()
    sort_by = request.args.get("sort", "discount")

    if category and category != "all":
        offers = [o for o in offers if o.get("category") == category]
    if source and source != "all":
        offers = [o for o in offers if o.get("source") == source]
    if min_discount:
        offers = [o for o in offers if (o.get("discount") or 0) >= min_discount]
    if max_price:
        offers = [o for o in offers if (o.get("price") or 0) <= max_price]
    if search:
        offers = [o for o in offers if search in o.get("title", "").lower()]

    # Ordenação
    if sort_by == "discount":
        offers = sorted(offers, key=lambda x: x.get("discount") or 0, reverse=True)
    elif sort_by == "price_asc":
        offers = sorted(offers, key=lambda x: x.get("price") or 0)
    elif sort_by == "price_desc":
        offers = sorted(offers, key=lambda x: x.get("price") or 0, reverse=True)
    elif sort_by == "newest":
        offers = sorted(offers, key=lambda x: x.get("timestamp", ""), reverse=True)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 24, type=int)
    total = len(offers)
    offers_page = offers[(page-1)*per_page : page*per_page]

    return jsonify({
        "offers": offers_page,
        "total": total,
        "page": page,
        "per_page": per_page,
        "last_update": CACHE.get("last_update"),
        "is_refreshing": CACHE["is_running"],
    })

@app.route("/api/stats")
def get_stats():
    if not CACHE["offers"]:
        CACHE["offers"] = load_offers()
    offers = CACHE["offers"]
    sources = {}
    categories = {"tech": 0, "games": 0}
    for o in offers:
        src = o.get("source", "Outro")
        sources[src] = sources.get(src, 0) + 1
        cat = o.get("category", "tech")
        categories[cat] = categories.get(cat, 0) + 1
    top_discounts = sorted([o for o in offers if o.get("discount")], key=lambda x: x["discount"], reverse=True)[:5]
    return jsonify({
        "total": len(offers),
        "sources": sources,
        "categories": categories,
        "top_discounts": top_discounts,
        "last_update": CACHE.get("last_update"),
    })

@app.route("/api/refresh", methods=["POST"])
def trigger_refresh():
    if CACHE["is_running"]:
        return jsonify({"status": "already_running", "message": "Atualização já em andamento"}), 202
    thread = threading.Thread(target=refresh_offers, daemon=True)
    thread.start()
    return jsonify({"status": "started", "message": "Atualização iniciada!"})

@app.route("/api/sources")
def get_sources():
    return jsonify({
        "sources": ["Steam", "Nuuvem", "Instant Gaming", "Green Man Gaming", "KaBuM!", "Terabyte Shop", "Pelando"]
    })

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

def start_server():
    CACHE["offers"] = load_offers()
    if not CACHE["offers"]:
        print("[SERVER] Nenhum dado local, coletando agora...")
        thread = threading.Thread(target=refresh_offers, daemon=True)
        thread.start()
    refresh_thread = threading.Thread(target=lambda: auto_refresh_loop(1800), daemon=True)
    refresh_thread.start()
    port = int(os.environ.get("PORT", 5000))
    print(f"[SERVER] Rodando na porta {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    start_server()
