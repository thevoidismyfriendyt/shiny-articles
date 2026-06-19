import json
import os
import re
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, send_from_directory
from readability import Document

app = Flask(__name__)

CONFIG_FILE    = os.path.join(os.path.dirname(__file__), "config.json")
NASA_CACHE_FILE = os.path.join(os.path.dirname(__file__), "nasa_cache.json")
META_FILE      = os.path.join(os.path.dirname(__file__), "articles_meta.json")
VIEWS_FILE     = os.path.join(os.path.dirname(__file__), "view_counts.json")
NASA_CACHE_TTL_HOURS = 24

AOD_SOURCES = "bbc-news,reuters,associated-press,the-wall-street-journal,the-new-york-times,bloomberg,the-washington-post"

INTERESTS = [
    "Technology", "Science", "Space", "Artificial Intelligence", "Climate",
    "Health", "Medicine", "Politics", "Business", "Finance", "Cryptocurrency",
    "Sports", "Gaming", "Movies", "Music", "Art", "Travel", "Food",
    "History", "Philosophy", "Psychology", "Education", "Environment",
    "Cybersecurity", "Robotics", "Startups", "World News", "Planes",
]

INTEREST_TERMS = {
    "Planes":                  ["aviation", "aircraft", "airline", "airplane", "airspace", "pilot", "airport", "flight"],
    "Artificial Intelligence": ["artificial intelligence", "machine learning", "deep learning", "neural network", "AI model", "large language model"],
    "Cryptocurrency":          ["cryptocurrency", "bitcoin", "ethereum", "blockchain", "crypto", "web3"],
    "Climate":                 ["climate change", "global warming", "climate", "emissions", "carbon", "greenhouse"],
    "Cybersecurity":           ["cybersecurity", "cyber attack", "hacking", "malware", "ransomware", "data breach", "vulnerability"],
    "World News":              ["world news", "international", "global"],
    "Space":                   ["space", "NASA", "SpaceX", "rocket", "satellite", "astronaut", "orbit", "moon", "mars"],
    "Robotics":                ["robotics", "robot", "autonomous", "drone"],
}

AD_RE = re.compile(
    r'\b(buy|shop|sale|deal|deals|discount|coupon|promo|promocode|offer|offers|sponsored|advertisement|advertise)\b'
    r'|\b(best price|lowest price|free shipping|order now|limited time|% off|save \$|save up to)\b'
    r'|\b(review:?|best \w+ (of|for)|top \d+ \w+|ranked|ranking|buying guide|vs\.)\b'
    r'|\$\d+',
    re.IGNORECASE,
)


# ── Generic file helpers ────────────────────────────────────────────────────

def _load(path, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ── Config ──────────────────────────────────────────────────────────────────

def load_config():
    cfg = _load(CONFIG_FILE)
    if "api_key" in cfg and cfg["api_key"] and "api_keys" not in cfg:
        cfg["api_keys"] = [cfg["api_key"]]
        del cfg["api_key"]
    cfg.setdefault("api_keys", [])
    cfg.setdefault("selected_interests", [])
    cfg.setdefault("saved_articles", [])
    return cfg


def save_config(data):
    _save(CONFIG_FILE, data)


def mask_key(key):
    if len(key) <= 8:
        return "****"
    return key[:4] + "..." + key[-4:]


# ── NewsAPI rotation ────────────────────────────────────────────────────────

RATE_LIMITED_CODES = {"rateLimited", "maximumResultsReached"}


def newsapi_get(endpoint, params, cfg):
    keys = cfg.get("api_keys", [])
    if not keys:
        return None, "no_api_key"
    start = cfg.get("last_key_idx", 0) % len(keys)
    for i in range(len(keys)):
        idx = (start + i) % len(keys)
        try:
            resp = requests.get(
                f"https://newsapi.org/v2/{endpoint}",
                params={**params, "apiKey": keys[idx]},
                timeout=10,
            )
            data = resp.json()
        except Exception:
            continue
        if data.get("status") == "ok":
            cfg["last_key_idx"] = idx
            save_config(cfg)
            return data, None
        if data.get("code") in RATE_LIMITED_CODES:
            continue
        return data, data.get("message", "API error")
    return None, "All API keys are rate-limited or unavailable"


# ── Filtering helpers ───────────────────────────────────────────────────────

def is_ad(title, desc):
    return bool(AD_RE.search(f"{title} {desc}"))


def is_english(title, desc):
    text = f"{title} {desc}"
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    return sum(1 for c in letters if ord(c) > 127) / len(letters) < 0.25


def get_search_terms(interest):
    return INTEREST_TERMS.get(interest, [interest.lower()])


def matches_interests(title, desc, interests):
    text = f"{title} {desc}".lower()
    return any(term.lower() in text for i in interests for term in get_search_terms(i))


def build_query(interests):
    terms, seen = [], set()
    for i in interests:
        for t in get_search_terms(i):
            if t not in seen:
                seen.add(t)
                terms.append(t)
    parts, length = [], 0
    for term in terms:
        quoted = f'"{term}"'
        addition = len(quoted) + (4 if parts else 0)
        if length + addition > 490:
            break
        parts.append(quoted)
        length += addition
    return " OR ".join(parts)


def current_period_start():
    now = datetime.now()
    cutoff = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if now < cutoff:
        cutoff -= timedelta(days=1)
    return cutoff.isoformat()


# ── Routes: config & keys ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", interests=INTERESTS)


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), filename)


@app.route("/api/config", methods=["GET"])
def get_config():
    cfg = load_config()
    keys = cfg.get("api_keys", [])
    return jsonify({
        "has_api_key": bool(keys),
        "selected_interests": cfg.get("selected_interests", []),
        "api_keys": [mask_key(k) for k in keys],
        "api_keys_count": len(keys),
        "has_nasa_key": bool(cfg.get("nasa_api_key")),
        "nasa_key_masked": mask_key(cfg["nasa_api_key"]) if cfg.get("nasa_api_key") else None,
    })


@app.route("/api/config", methods=["POST"])
def set_config():
    data = request.get_json()
    cfg = load_config()
    if "selected_interests" in data:
        cfg["selected_interests"] = data["selected_interests"]
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/keys", methods=["POST"])
def set_keys():
    data = request.get_json()
    keys = [k.strip() for k in data.get("keys", []) if k and k.strip()]
    cfg = load_config()
    cfg["api_keys"] = keys
    cfg["last_key_idx"] = 0
    save_config(cfg)
    return jsonify({"ok": True, "count": len(keys)})


@app.route("/api/keys/add", methods=["POST"])
def add_keys():
    data = request.get_json()
    new_keys = [k.strip() for k in data.get("keys", []) if k and k.strip()]
    cfg = load_config()
    existing = cfg.get("api_keys", [])
    for k in new_keys:
        if k not in existing:
            existing.append(k)
    cfg["api_keys"] = existing
    save_config(cfg)
    return jsonify({"ok": True, "count": len(existing)})


@app.route("/api/keys/<int:idx>", methods=["DELETE"])
def delete_key(idx):
    cfg = load_config()
    keys = cfg.get("api_keys", [])
    if 0 <= idx < len(keys):
        keys.pop(idx)
        cfg["api_keys"] = keys
        cfg["last_key_idx"] = 0
        save_config(cfg)
        return jsonify({"ok": True})
    return jsonify({"error": "invalid index"}), 400


# ── Routes: articles ────────────────────────────────────────────────────────

@app.route("/api/articles")
def get_articles():
    cfg = load_config()
    interests = cfg.get("selected_interests", [])
    if not interests:
        return jsonify({"error": "no_interests"}), 400

    data, err = newsapi_get("everything", {
        "q": build_query(interests),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 100,
    }, cfg)

    if err == "no_api_key":
        return jsonify({"error": "no_api_key"}), 400
    if err:
        return jsonify({"error": err}), 400

    articles = []
    for a in data.get("articles", []):
        title = a.get("title") or ""
        desc  = a.get("description") or ""
        url   = a.get("url") or ""
        if not title or not url or "[Removed]" in title:
            continue
        if not is_english(title, desc):
            continue
        if is_ad(title, desc):
            continue
        if not matches_interests(title, desc, interests):
            continue
        tags = [i for i in interests if matches_interests(title, desc, [i])]
        articles.append({
            "title": title, "description": desc, "url": url,
            "image": a.get("urlToImage"),
            "source": a.get("source", {}).get("name"),
            "publishedAt": a.get("publishedAt"),
            "tags": tags,
        })

    return jsonify({"articles": articles})


@app.route("/api/article-of-day")
def get_article_of_day():
    cfg = load_config()
    if not cfg.get("api_keys"):
        return jsonify({"error": "no_api_key"}), 400
    if cfg.get("aod_period") == current_period_start() and cfg.get("aod_article"):
        return jsonify({"article": cfg["aod_article"], "cached": True})

    data, err = newsapi_get("top-headlines", {"sources": AOD_SOURCES, "pageSize": 10}, cfg)
    if err:
        return jsonify({"error": err}), 400

    articles = [a for a in data.get("articles", [])
                if a.get("title") and a.get("url") and "[Removed]" not in (a.get("title") or "")]
    if not articles:
        return jsonify({"error": "No articles found"}), 404

    a = articles[0]
    article = {
        "title": a.get("title"), "description": a.get("description"),
        "content": a.get("content"), "url": a.get("url"),
        "image": a.get("urlToImage"),
        "source": a.get("source", {}).get("name"),
        "publishedAt": a.get("publishedAt"),
    }
    cfg["aod_article"] = article
    cfg["aod_period"] = current_period_start()
    save_config(cfg)
    return jsonify({"article": article, "cached": False})


@app.route("/api/read")
def read_article():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        resp = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ShinyArticles/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        })
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Could not fetch article: {e}"}), 502
    try:
        doc = Document(resp.text)
        return jsonify({"title": doc.title(), "content": doc.summary(html_partial=True)})
    except Exception as e:
        return jsonify({"error": f"Could not parse article: {e}"}), 500


# ── Routes: view tracking & trending ───────────────────────────────────────

@app.route("/api/view", methods=["POST"])
def track_view():
    data    = request.get_json()
    url     = (data or {}).get("url")
    article = (data or {}).get("article")
    if not url:
        return jsonify({"ok": True})
    counts = _load(VIEWS_FILE)
    entry  = counts.get(url, {"count": 0})
    entry["count"] += 1
    if article:
        entry["article"] = article
    counts[url] = entry
    _save(VIEWS_FILE, counts)
    return jsonify({"ok": True})


@app.route("/api/trending")
def get_trending():
    counts = _load(VIEWS_FILE)
    ranked = sorted(counts.items(), key=lambda x: x[1].get("count", 0), reverse=True)
    trending = []
    for _, v in ranked[:10]:
        if v.get("article"):
            a = dict(v["article"])
            a["view_count"] = v["count"]
            trending.append(a)
    return jsonify({"trending": trending})


# ── Routes: article metadata (reactions, notes, folder, archive, progress) ─

@app.route("/api/meta", methods=["GET"])
def get_meta():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"meta": {}})
    meta = _load(META_FILE)
    return jsonify({"meta": meta.get(url, {})})


@app.route("/api/meta/bulk", methods=["POST"])
def get_meta_bulk():
    """Return metadata for multiple URLs at once."""
    urls = (request.get_json() or {}).get("urls", [])
    meta = _load(META_FILE)
    return jsonify({u: meta.get(u, {}) for u in urls})


@app.route("/api/meta", methods=["POST"])
def update_meta():
    data = request.get_json()
    url  = (data or {}).get("url")
    if not url:
        return jsonify({"error": "no url"}), 400
    meta = _load(META_FILE)
    entry = meta.get(url, {})
    for field in ("reactions", "notes", "folder", "archived", "read_progress"):
        if field in data:
            entry[field] = data[field]
    meta[url] = entry
    _save(META_FILE, meta)
    return jsonify({"ok": True})


# ── Routes: saved articles ──────────────────────────────────────────────────

@app.route("/api/saved", methods=["GET"])
def get_saved():
    cfg   = load_config()
    saved = cfg.get("saved_articles", [])
    meta  = _load(META_FILE)
    # Attach per-article metadata inline
    for a in saved:
        a["_meta"] = meta.get(a.get("url", ""), {})
    return jsonify({"saved": saved})


@app.route("/api/saved", methods=["POST"])
def save_article():
    article = request.get_json()
    if not article or not article.get("url"):
        return jsonify({"error": "invalid"}), 400
    cfg   = load_config()
    saved = cfg.get("saved_articles", [])
    if not any(a["url"] == article["url"] for a in saved):
        saved.insert(0, article)
    cfg["saved_articles"] = saved
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/saved", methods=["DELETE"])
def unsave_article():
    url = (request.get_json() or {}).get("url")
    if not url:
        return jsonify({"error": "invalid"}), 400
    cfg = load_config()
    cfg["saved_articles"] = [a for a in cfg.get("saved_articles", []) if a["url"] != url]
    save_config(cfg)
    return jsonify({"ok": True})


# ── Routes: NASA ────────────────────────────────────────────────────────────

@app.route("/api/nasa-key", methods=["POST"])
def set_nasa_key():
    key = ((request.get_json() or {}).get("key") or "").strip()
    cfg = load_config()
    cfg["nasa_api_key"] = key
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/nasa-key", methods=["DELETE"])
def delete_nasa_key():
    cfg = load_config()
    cfg.pop("nasa_api_key", None)
    save_config(cfg)
    return jsonify({"ok": True})


def load_nasa_cache():
    return _load(NASA_CACHE_FILE)


def save_nasa_cache(data):
    _save(NASA_CACHE_FILE, data)


@app.route("/api/nasa-pictures")
def get_nasa_pictures():
    cfg   = load_config()
    key   = cfg.get("nasa_api_key") or "DEMO_KEY"
    cache = load_nasa_cache()

    cached_at = cache.get("cached_at")
    if cached_at and cache.get("pictures"):
        age = (datetime.now() - datetime.fromisoformat(cached_at)).total_seconds() / 3600
        if age < NASA_CACHE_TTL_HOURS:
            return jsonify({"pictures": cache["pictures"], "cached": True})

    end   = datetime.now()
    start = end - timedelta(days=30)
    try:
        resp = requests.get("https://api.nasa.gov/planetary/apod", params={
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date":   end.strftime("%Y-%m-%d"),
            "thumbs": "true", "api_key": key,
        }, timeout=15)
        data = resp.json()
    except Exception as e:
        if cache.get("pictures"):
            return jsonify({"pictures": cache["pictures"], "cached": True, "stale": True})
        return jsonify({"error": str(e)}), 500

    if isinstance(data, dict) and data.get("error"):
        if cache.get("pictures"):
            return jsonify({"pictures": cache["pictures"], "cached": True, "stale": True})
        err = data["error"]
        msg = err.get("message", err) if isinstance(err, dict) else str(err)
        return jsonify({"error": msg}), 400

    pictures = []
    for item in reversed(data if isinstance(data, list) else []):
        pictures.append({
            "title": item.get("title"), "date": item.get("date"),
            "explanation": item.get("explanation"), "url": item.get("url"),
            "hdurl": item.get("hdurl"), "media_type": item.get("media_type"),
            "thumbnail_url": item.get("thumbnail_url"), "copyright": item.get("copyright"),
        })

    save_nasa_cache({"pictures": pictures, "cached_at": datetime.now().isoformat()})
    return jsonify({"pictures": pictures, "cached": False})


if __name__ == "__main__":
    app.run(debug=False, host="::", port=3000)
