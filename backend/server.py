from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import threading
import time
from datetime import datetime
from scraper import run_all_scrapers

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR   = os.path.join(BASE_DIR, "frontend")
DATA_FILE      = os.path.join(BASE_DIR, "data", "offers.json")
FAVORITES_FILE = os.path.join(BASE_DIR, "data", "favorites.json")
ALERTS_FILE    = os.path.join(BASE_DIR, "data", "alerts.json")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

CACHE = {"offers": [], "last_update": None, "is_running": False}

# ── helpers ──────────────────────────────────────────────

def _read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_offers():
    return _read_json(DATA_FILE, [])

def save_offers(offers):
    _write_json(DATA_FILE, offers)

# ── scraping ──────────────────────────────────────────────

def refresh_offers():
    if CACHE["is_running"]:
        return
    CACHE["is_running"] = True
    try:
        offers = run_all_scrapers()
        save_offers(offers)
        CACHE["offers"] = offers
        CACHE["last_update"] = datetime.now().isoformat()
        check_alerts(offers)
    finally:
        CACHE["is_running"] = False

def auto_refresh_loop(interval=1800):
    while True:
        refresh_offers()
        time.sleep(interval)

# ── alert checker ─────────────────────────────────────────

def check_alerts(offers):
    alerts = _read_json(ALERTS_FILE, [])
    triggered = []
    remaining = []
    for alert in alerts:
        keyword = alert.get("keyword", "").lower()
        max_price = alert.get("max_price")
        min_disc  = alert.get("min_discount", 0)
        matches = [
            o for o in offers
            if keyword in o.get("title", "").lower()
            and (max_price is None or (o.get("price") or 9999) <= max_price)
            and (o.get("discount") or 0) >= min_disc
        ]
        if matches:
            alert["last_triggered"] = datetime.now().isoformat()
            alert["last_match"] = matches[0]
            triggered.append(alert)
            if not alert.get("keep_after_trigger", True):
                continue
        remaining.append(alert)
    _write_json(ALERTS_FILE, remaining)
    if triggered:
        notif_file = os.path.join(BASE_DIR, "data", "notifications.json")
        existing = _read_json(notif_file, [])
        for a in triggered:
            existing.insert(0, {
                "id": f"{a.get('id','?')}-{int(time.time())}",
                "alert_id": a.get("id"),
                "keyword": a.get("keyword"),
                "match": a.get("last_match"),
                "triggered_at": a.get("last_triggered"),
                "read": False,
            })
        _write_json(notif_file, existing[:100])

# ── offers routes ─────────────────────────────────────────

@app.route("/api/offers")
def get_offers():
    if not CACHE["offers"]:
        CACHE["offers"] = load_offers()
    offers = list(CACHE["offers"])

    category     = request.args.get("category")
    source       = request.args.get("source")
    min_discount = request.args.get("min_discount", type=int)
    max_price    = request.args.get("max_price", type=float)
    search       = request.args.get("q", "").lower()
    sort_by      = request.args.get("sort", "discount")

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

    if sort_by == "discount":
        offers = sorted(offers, key=lambda x: x.get("discount") or 0, reverse=True)
    elif sort_by == "price_asc":
        offers = sorted(offers, key=lambda x: x.get("price") or 0)
    elif sort_by == "price_desc":
        offers = sorted(offers, key=lambda x: x.get("price") or 0, reverse=True)
    elif sort_by == "newest":
        offers = sorted(offers, key=lambda x: x.get("timestamp", ""), reverse=True)

    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 24, type=int)
    total    = len(offers)
    return jsonify({
        "offers": offers[(page-1)*per_page : page*per_page],
        "total": total, "page": page, "per_page": per_page,
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
        sources[o.get("source","Outro")] = sources.get(o.get("source","Outro"), 0) + 1
        categories[o.get("category","tech")] = categories.get(o.get("category","tech"), 0) + 1
    top = sorted([o for o in offers if o.get("discount")], key=lambda x: x["discount"], reverse=True)[:5]
    return jsonify({
        "total": len(offers), "sources": sources,
        "categories": categories, "top_discounts": top,
        "last_update": CACHE.get("last_update"),
    })

@app.route("/api/refresh", methods=["POST"])
def trigger_refresh():
    if CACHE["is_running"]:
        return jsonify({"status": "already_running", "message": "Atualização já em andamento"}), 202
    threading.Thread(target=refresh_offers, daemon=True).start()
    return jsonify({"status": "started", "message": "Atualização iniciada!"})

@app.route("/api/sources")
def get_sources():
    return jsonify({"sources": ["Steam","Nuuvem","Instant Gaming","Green Man Gaming","Mercado Livre","KaBuM!","Terabyte Shop","Pichau","Amazon BR"]})

# ── favorites routes ──────────────────────────────────────

@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    favs = _read_json(FAVORITES_FILE, [])
    return jsonify({"favorites": favs, "total": len(favs)})

@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    data = request.get_json()
    if not data or not data.get("url"):
        return jsonify({"error": "url obrigatória"}), 400
    favs = _read_json(FAVORITES_FILE, [])
    if any(f["url"] == data["url"] for f in favs):
        return jsonify({"status": "already_exists", "message": "Já está nos favoritos"})
    favs.insert(0, {
        "id": f"fav-{int(time.time()*1000)}",
        "title": data.get("title",""),
        "price": data.get("price"),
        "original_price": data.get("original_price"),
        "discount": data.get("discount"),
        "url": data["url"],
        "image": data.get("image",""),
        "source": data.get("source",""),
        "category": data.get("category",""),
        "saved_at": datetime.now().isoformat(),
    })
    _write_json(FAVORITES_FILE, favs)
    return jsonify({"status": "ok", "message": "Adicionado aos favoritos!", "total": len(favs)})

@app.route("/api/favorites/<fav_id>", methods=["DELETE"])
def remove_favorite(fav_id):
    favs = _read_json(FAVORITES_FILE, [])
    new_favs = [f for f in favs if f.get("id") != fav_id and f.get("url") != fav_id]
    _write_json(FAVORITES_FILE, new_favs)
    return jsonify({"status": "ok", "message": "Removido dos favoritos", "total": len(new_favs)})

# ── alerts routes ─────────────────────────────────────────

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    alerts = _read_json(ALERTS_FILE, [])
    return jsonify({"alerts": alerts, "total": len(alerts)})

@app.route("/api/alerts", methods=["POST"])
def create_alert():
    data = request.get_json()
    if not data or not data.get("keyword"):
        return jsonify({"error": "keyword obrigatória"}), 400
    alerts = _read_json(ALERTS_FILE, [])
    alert = {
        "id": f"alert-{int(time.time()*1000)}",
        "keyword": data["keyword"].strip(),
        "max_price": data.get("max_price"),
        "min_discount": data.get("min_discount", 0),
        "keep_after_trigger": data.get("keep_after_trigger", True),
        "created_at": datetime.now().isoformat(),
        "last_triggered": None,
    }
    alerts.insert(0, alert)
    _write_json(ALERTS_FILE, alerts)
    return jsonify({"status": "ok", "message": f"Alerta criado para '{alert['keyword']}'!", "alert": alert})

@app.route("/api/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    alerts = _read_json(ALERTS_FILE, [])
    alerts = [a for a in alerts if a.get("id") != alert_id]
    _write_json(ALERTS_FILE, alerts)
    return jsonify({"status": "ok", "message": "Alerta removido"})

# ── notifications ─────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    notifs = _read_json(os.path.join(BASE_DIR, "data", "notifications.json"), [])
    unread = sum(1 for n in notifs if not n.get("read"))
    return jsonify({"notifications": notifs[:20], "unread": unread})

@app.route("/api/notifications/read", methods=["POST"])
def mark_read():
    notif_file = os.path.join(BASE_DIR, "data", "notifications.json")
    notifs = _read_json(notif_file, [])
    for n in notifs:
        n["read"] = True
    _write_json(notif_file, notifs)
    return jsonify({"status": "ok"})

# ── frontend ──────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

# ── startup ───────────────────────────────────────────────

def start_server():
    CACHE["offers"] = load_offers()
    if not CACHE["offers"]:
        print("[SERVER] Sem dados locais, coletando agora...")
        threading.Thread(target=refresh_offers, daemon=True).start()
    threading.Thread(target=lambda: auto_refresh_loop(1800), daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    print(f"[SERVER] Rodando em http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    start_server()
