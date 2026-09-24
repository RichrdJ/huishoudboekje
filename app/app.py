import os
import secrets
from datetime import timedelta
import re
import sqlite3
import statistics
from collections import defaultdict
from functools import wraps
from urllib.parse import quote

from flask import Flask, g, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from categories import (CATEGORIES, DEFAULT_RULES, FOREIGN_CATEGORY, FOREIGN_COUNTRY_CODES,
                        UNCATEGORIZED)
from ing_parser import ParseError, parse_ing_csv

DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "huishoudboekje.db")
RULES_VERSION = "3"
PW_METHOD = "pbkdf2:sha256:600000"
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, static_folder=None)
app.config.update(MAX_CONTENT_LENGTH=20 * 1024 * 1024, PERMANENT_SESSION_LIFETIME=timedelta(days=30),
                  SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)


# ---------------------------------------------------------------- database

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            hash TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            name TEXT, account TEXT, counter_account TEXT, code TEXT,
            amount REAL NOT NULL,
            mutation_type TEXT, description TEXT, balance REAL,
            category TEXT NOT NULL DEFAULT 'Ongecategoriseerd',
            manual INTEGER NOT NULL DEFAULT 0,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY,
            pattern TEXT NOT NULL,
            category TEXT NOT NULL,
            direction TEXT NOT NULL DEFAULT '',
            user_defined INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    # Categorieën aanvullen en standaardregels bijwerken bij een nieuwe versie.
    # Eigen regels (user_defined=1) blijven altijd bewaard.
    conn.executemany(
        "INSERT OR IGNORE INTO categories(name, kind, position) VALUES (?,?,?)",
        [(n, k, i) for i, (n, k) in enumerate(CATEGORIES)])
    version = conn.execute("SELECT value FROM meta WHERE key='rules_version'").fetchone()
    if not version or version[0] != RULES_VERSION:
        conn.execute("DELETE FROM rules WHERE user_defined=0")
        conn.executemany(
            "INSERT INTO rules(pattern, category, direction, user_defined) VALUES (?,?,?,0)",
            DEFAULT_RULES)
        conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('rules_version', ?)",
                     (RULES_VERSION,))
    secret = get_setting(conn, "secret_key")
    if not secret:
        secret = secrets.token_hex(32)
        set_setting(conn, "secret_key", secret)
    app.secret_key = secret
    if not get_setting(conn, "password_hash"):
        set_setting(conn, "username", DEFAULT_USER)
        set_setting(conn, "password_hash", generate_password_hash(DEFAULT_PASSWORD, method=PW_METHOD))
        set_setting(conn, "must_change", "1")
    apply_partner_rules(conn)
    conn.commit()
    recategorize_all(conn)
    conn.close()


# ---------------------------------------------------------------- instellingen

def get_setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))


def normalize_iban(value):
    return re.sub(r"\s+", "", value or "").upper()


def partner_ibans(conn):
    return [x for x in get_setting(conn, "partner_ibans").split(",") if x]


def apply_partner_rules(conn):
    """Eigen rekeningen worden regels met de hoogste prioriteit (user_defined=2):
    stortingen tellen als inleg, terugboekingen verlagen de inleg."""
    conn.execute("DELETE FROM rules WHERE user_defined=2")
    conn.executemany(
        "INSERT INTO rules(pattern, category, direction, user_defined) VALUES (?, 'Inleg partners', '', 2)",
        [(iban.lower(),) for iban in partner_ibans(conn)])


# ---------------------------------------------------------------- auth

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "admin"


def requires_auth(fn):
    """Iedereen moet inloggen. Zolang het standaardwachtwoord nog actief is,
    is alleen het scherm om het te wijzigen bereikbaar."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        is_api = request.path.startswith("/api/")
        if not session.get("auth"):
            return (jsonify(error="Inloggen vereist."), 401) if is_api else redirect("login")
        if get_setting(db(), "must_change") == "1":
            return (jsonify(error="Wijzig eerst het standaardwachtwoord."), 403) if is_api \
                else redirect("login")
        return fn(*args, **kwargs)
    return wrapper


def check_credentials(conn, username, password):
    return (username.strip().lower() == get_setting(conn, "username").lower()
            and check_password_hash(get_setting(conn, "password_hash"), password))


def set_credentials(conn, username, password):
    username = username.strip()
    if not username:
        return "Kies een gebruikersnaam."
    if len(password) < 8:
        return "Kies een wachtwoord van minimaal 8 tekens."
    if password == DEFAULT_PASSWORD or password.lower() == username.lower():
        return "Kies een sterker wachtwoord."
    set_setting(conn, "username", username)
    set_setting(conn, "password_hash", generate_password_hash(password, method=PW_METHOD))
    set_setting(conn, "must_change", "0")
    conn.commit()
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    conn = db()
    must_change = get_setting(conn, "must_change") == "1"
    if request.method == "POST":
        if request.form.get("action") == "change":
            if not session.get("auth"):
                return redirect("login")
            if request.form.get("password") != request.form.get("password2"):
                return redirect("login?fout=" + quote("De wachtwoorden zijn niet gelijk."))
            err = set_credentials(conn, request.form.get("username", ""), request.form.get("password", ""))
            if err:
                return redirect("login?fout=" + quote(err))
            return redirect("./")
        if check_credentials(conn, request.form.get("username", ""), request.form.get("password", "")):
            session.clear()
            session.permanent = True
            session["auth"] = True
            return redirect("login" if must_change else "./")
        return redirect("login?fout=" + quote("Onjuiste gebruikersnaam of wachtwoord."))
    if session.get("auth") and not must_change:
        return redirect("./")
    return send_from_directory(STATIC_DIR, "login.html")


@app.route("/api/login-state")
def login_state():
    return jsonify(logged_in=bool(session.get("auth")),
                   must_change=get_setting(db(), "must_change") == "1")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(ok=True)


@app.route("/api/settings")
@requires_auth
def get_settings():
    conn = db()
    current = partner_ibans(conn)
    # Voorstellen: rekeningen die regelmatig geld storten via een eigen overboeking
    suggestions = []
    for r in conn.execute("""
            SELECT upper(counter_account) iban, COUNT(*) n, ROUND(SUM(amount),2) total,
                   MAX(name) name
            FROM transactions
            WHERE amount > 0 AND counter_account LIKE 'NL%'
              AND mutation_type IN ('Online bankieren', 'Overschrijving')
            GROUP BY upper(counter_account) HAVING COUNT(*) >= 3
            ORDER BY SUM(amount) DESC LIMIT 8"""):
        suggestions.append(dict(r))
    known = {s["iban"] for s in suggestions}
    for iban in current:
        if iban not in known:
            row = conn.execute("SELECT MAX(name) FROM transactions WHERE upper(counter_account)=?",
                               (iban,)).fetchone()
            suggestions.append({"iban": iban, "name": row[0] if row else None, "n": None, "total": None})
    return jsonify(partner_ibans=current, suggestions=suggestions,
                   username=get_setting(conn, "username"))


@app.route("/api/settings", methods=["POST"])
@requires_auth
def save_settings():
    conn = db()
    data = request.get_json(force=True)
    ibans = []
    for raw in data.get("partner_ibans", []):
        iban = normalize_iban(raw)
        if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", iban):
            return jsonify(error=f"“{raw}” is geen geldig rekeningnummer."), 400
        if iban not in ibans:
            ibans.append(iban)
    set_setting(conn, "partner_ibans", ",".join(ibans))
    apply_partner_rules(conn)
    conn.commit()
    n = recategorize_all(conn)
    return jsonify(ok=True, partner_ibans=ibans, recategorized=n)


@app.route("/api/settings/password", methods=["POST"])
@requires_auth
def save_password():
    conn = db()
    data = request.get_json(force=True)
    if not check_credentials(conn, get_setting(conn, "username"), data.get("current", "")):
        return jsonify(error="Het huidige wachtwoord klopt niet."), 400
    err = set_credentials(conn, data.get("username") or get_setting(conn, "username"), data.get("new", ""))
    if err:
        return jsonify(error=err), 400
    return jsonify(ok=True, username=get_setting(conn, "username"))


# ---------------------------------------------------------------- categorisatie

def load_rules(conn):
    rows = conn.execute("SELECT pattern, category, direction, user_defined FROM rules").fetchall()
    # Eigen regels eerst, daarna het langste (meest specifieke) patroon.
    return sorted(
        [(r["pattern"].lower(), r["category"], r["direction"], r["user_defined"]) for r in rows],
        key=lambda r: (-r[3], -len(r[0])))


def _is_foreign_card_payment(tx):
    name = (tx.get("name") or "").strip()
    return (tx.get("mutation_type") == "Betaalautomaat"
            and name[-3:].upper() in FOREIGN_COUNTRY_CODES
            and (len(name) == 3 or name[-4] == " "))


def categorize(tx, rules):
    haystack = " ".join(
        (tx.get("name") or "", tx.get("counter_account") or "", tx.get("description") or "")
    ).lower()
    haystack = " " + re.sub(r"\s+", " ", haystack) + " "
    is_debit = tx["amount"] < 0
    foreign = _is_foreign_card_payment(tx)
    for pattern, category, direction, user_defined in rules:
        # Buitenlandse pinbetalingen gaan voor op standaardregels, niet op eigen regels
        if foreign and not user_defined:
            return FOREIGN_CATEGORY
        if direction == "af" and not is_debit:
            continue
        if direction == "bij" and is_debit:
            continue
        if pattern in haystack:
            return category
    if foreign:
        return FOREIGN_CATEGORY
    if not is_debit:
        return "Overige inkomsten"
    if tx.get("mutation_type") in ("Online bankieren", "Overschrijving"):
        return "Betaalverzoeken & personen"
    return UNCATEGORIZED


def recategorize_all(conn):
    rules = load_rules(conn)
    rows = conn.execute(
        "SELECT id, name, counter_account, description, amount, mutation_type FROM transactions "
        "WHERE manual=0"
    ).fetchall()
    updates = [(categorize(dict(r), rules), r["id"]) for r in rows]
    conn.executemany("UPDATE transactions SET category=? WHERE id=?", updates)
    conn.commit()
    return len(updates)


def category_kinds(conn):
    return {r["name"]: r["kind"] for r in conn.execute("SELECT name, kind FROM categories")}


# ---------------------------------------------------------------- periodes

def period_filter(period):
    """period: 'YYYY-MM', 'YYYY' of 'all' -> (sql, params)"""
    if not period or period == "all":
        return "1=1", []
    if re.fullmatch(r"\d{4}-\d{2}", period):
        return "substr(date,1,7)=?", [period]
    if re.fullmatch(r"\d{4}", period):
        return "substr(date,1,4)=?", [period]
    return "1=1", []


def month_count(conn, period):
    where, params = period_filter(period)
    n = conn.execute(
        f"SELECT COUNT(DISTINCT substr(date,1,7)) FROM transactions WHERE {where}", params
    ).fetchone()[0]
    return max(n, 1)


def previous_months(conn, period, n=6):
    """Maanden vóór een gekozen maand, voor vergelijking met het gemiddelde."""
    if not period or not re.fullmatch(r"\d{4}-\d{2}", period):
        return []
    rows = conn.execute(
        "SELECT DISTINCT substr(date,1,7) m FROM transactions WHERE substr(date,1,7) < ? "
        "ORDER BY m DESC LIMIT ?", (period, n)).fetchall()
    return [r["m"] for r in rows]


# ---------------------------------------------------------------- routes

@app.route("/health")
def health():
    return jsonify(ok=True)


@app.route("/")
@requires_auth
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/upload", methods=["POST"])
@requires_auth
def upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify(error="Geen bestand ontvangen."), 400
    conn = db()
    rules = load_rules(conn)
    added = skipped = 0
    for f in files:
        try:
            txs = parse_ing_csv(f.read())
        except (ParseError, ValueError) as e:
            return jsonify(error=f"{f.filename}: {e}"), 400
        for tx in txs:
            tx["category"] = categorize(tx, rules)
            cur = conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (hash, date, name, account, counter_account, code, amount,
                    mutation_type, description, balance, category)
                   VALUES (:hash, :date, :name, :account, :counter_account, :code, :amount,
                           :mutation_type, :description, :balance, :category)""", tx)
            if cur.rowcount:
                added += 1
            else:
                skipped += 1
    conn.commit()
    return jsonify(added=added, skipped=skipped)


@app.route("/api/periods")
@requires_auth
def periods():
    conn = db()
    months = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date,1,7) FROM transactions ORDER BY 1 DESC")]
    years = sorted({m[:4] for m in months}, reverse=True)
    return jsonify(months=months, years=years)


PROTECTED_CATEGORIES = {UNCATEGORIZED}
KINDS = ("uitgave", "inkomen", "overboeking")


@app.route("/api/categories")
@requires_auth
def categories():
    rows = db().execute("""
        SELECT c.name, c.kind,
               (SELECT COUNT(*) FROM transactions t WHERE t.category=c.name) AS tx_count,
               (SELECT ROUND(COALESCE(SUM(amount),0),2) FROM transactions t WHERE t.category=c.name) AS total,
               (SELECT COUNT(*) FROM rules r WHERE r.category=c.name) AS rule_count
        FROM categories c ORDER BY c.position, c.name""").fetchall()
    return jsonify([dict(r, protected=r["name"] in PROTECTED_CATEGORIES) for r in rows])


@app.route("/api/categories/update", methods=["POST"])
@requires_auth
def update_category():
    """Hernoemen en/of soort wijzigen. Transacties en regels verhuizen mee."""
    conn = db()
    data = request.get_json(force=True)
    old = data.get("old")
    new = (data.get("name") or old or "").strip()
    kind = data.get("kind")
    if old not in category_kinds(conn):
        return jsonify(error="Categorie niet gevonden."), 404
    if old in PROTECTED_CATEGORIES and new != old:
        return jsonify(error="Deze categorie kan niet hernoemd worden."), 400
    if kind and kind not in KINDS:
        return jsonify(error="Ongeldige soort."), 400
    if new != old and new in category_kinds(conn):
        return jsonify(error=f"Categorie “{new}” bestaat al."), 400
    conn.execute("UPDATE categories SET name=?, kind=COALESCE(?, kind) WHERE name=?", (new, kind, old))
    if new != old:
        conn.execute("UPDATE transactions SET category=? WHERE category=?", (new, old))
        conn.execute("UPDATE rules SET category=?, user_defined=MAX(user_defined,1) WHERE category=?",
                     (new, old))
    conn.commit()
    return jsonify(ok=True)


@app.route("/api/categories/delete", methods=["POST"])
@requires_auth
def delete_category():
    """Verwijdert een categorie; transacties gaan naar move_to, regels vervallen."""
    conn = db()
    data = request.get_json(force=True)
    name, move_to = data.get("name"), data.get("move_to") or UNCATEGORIZED
    kinds = category_kinds(conn)
    if name not in kinds or name in PROTECTED_CATEGORIES:
        return jsonify(error="Deze categorie kan niet verwijderd worden."), 400
    if move_to not in kinds or move_to == name:
        return jsonify(error="Kies een andere categorie om de transacties naar te verplaatsen."), 400
    n = conn.execute("UPDATE transactions SET category=?, manual=1 WHERE category=?",
                     (move_to, name)).rowcount
    conn.execute("DELETE FROM rules WHERE category=?", (name,))
    conn.execute("DELETE FROM categories WHERE name=?", (name,))
    conn.commit()
    return jsonify(ok=True, moved=n)


@app.route("/api/categories", methods=["POST"])
@requires_auth
def add_category():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    kind = data.get("kind", "uitgave")
    if not name or kind not in KINDS:
        return jsonify(error="Ongeldige categorie."), 400
    conn = db()
    if name in category_kinds(conn):
        return jsonify(error=f"Categorie “{name}” bestaat al."), 400
    conn.execute("INSERT INTO categories(name, kind, position) VALUES (?,?,"
                 "(SELECT COALESCE(MAX(position),0)+1 FROM categories))", (name, kind))
    conn.commit()
    return jsonify(ok=True)


@app.route("/api/summary")
@requires_auth
def summary():
    conn = db()
    period = request.args.get("period", "all")
    kinds = category_kinds(conn)
    where, params = period_filter(period)

    by_cat = defaultdict(float)
    for r in conn.execute(
            f"SELECT category, SUM(amount) total, COUNT(*) n FROM transactions WHERE {where} "
            "GROUP BY category", params):
        by_cat[r["category"]] = r["total"]

    income = sum(v for c, v in by_cat.items() if kinds.get(c) == "inkomen")
    expenses = -sum(v for c, v in by_cat.items() if kinds.get(c, "uitgave") == "uitgave")
    saved = -sum(v for c, v in by_cat.items() if kinds.get(c) == "overboeking")

    # Vergelijking met gemiddelde van voorgaande maanden (alleen bij maandweergave)
    prev = previous_months(conn, period)
    prev_avg = defaultdict(float)
    if prev:
        ph = ",".join("?" * len(prev))
        for r in conn.execute(
                f"SELECT category, SUM(amount) total FROM transactions "
                f"WHERE substr(date,1,7) IN ({ph}) GROUP BY category", prev):
            prev_avg[r["category"]] = r["total"] / len(prev)
    prev_income = sum(v for c, v in prev_avg.items() if kinds.get(c) == "inkomen")
    prev_expenses = -sum(v for c, v in prev_avg.items() if kinds.get(c, "uitgave") == "uitgave")

    expense_cats = sorted(
        [{"category": c, "total": round(-v, 2),
          "avg_prev": round(-prev_avg.get(c, 0.0), 2) if prev else None}
         for c, v in by_cat.items() if kinds.get(c, "uitgave") == "uitgave" and v < 0],
        key=lambda x: -x["total"])
    income_cats = sorted(
        [{"category": c, "total": round(v, 2)}
         for c, v in by_cat.items() if kinds.get(c) == "inkomen" and v > 0],
        key=lambda x: -x["total"])

    top_merchants = [dict(r) for r in conn.execute(
        f"SELECT name, category, ROUND(-SUM(amount),2) total, COUNT(*) n FROM transactions "
        f"WHERE {where} AND amount < 0 GROUP BY name, category ORDER BY SUM(amount) LIMIT 10",
        params)]
    top_merchants = [m for m in top_merchants if kinds.get(m["category"], "uitgave") == "uitgave"]

    # Maandelijkse reeks (laatste 12 maanden binnen het bereik)
    monthly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0, "saved": 0.0})
    for r in conn.execute(
            "SELECT substr(date,1,7) m, category, SUM(amount) total FROM transactions "
            "GROUP BY m, category"):
        kind = kinds.get(r["category"], "uitgave")
        key = {"inkomen": "income", "uitgave": "expenses", "overboeking": "saved"}[kind]
        monthly[r["m"]][key] += r["total"] if kind == "inkomen" else -r["total"]
    months = sorted(monthly)
    if re.fullmatch(r"\d{4}", period or ""):
        months = [m for m in months if m.startswith(period)]
    elif re.fullmatch(r"\d{4}-\d{2}", period or ""):
        months = [m for m in months if m <= period]
    months = months[-12:]
    series = [{"month": m, **{k: round(v, 2) for k, v in monthly[m].items()}} for m in months]

    balance_row = conn.execute(
        f"SELECT balance FROM transactions WHERE {where} AND balance IS NOT NULL "
        "ORDER BY date DESC, id ASC LIMIT 1", params).fetchone()

    uncategorized = conn.execute(
        f"SELECT COUNT(*) FROM transactions WHERE {where} AND category=?",
        params + [UNCATEGORIZED]).fetchone()[0]

    return jsonify(
        period=period,
        months_in_period=month_count(conn, period),
        income=round(income, 2), expenses=round(expenses, 2), saved=round(saved, 2),
        net=round(income - expenses, 2),
        prev_income=round(prev_income, 2) if prev else None,
        prev_expenses=round(prev_expenses, 2) if prev else None,
        prev_months=len(prev),
        expense_categories=expense_cats,
        income_categories=income_cats,
        top_merchants=top_merchants,
        monthly=series,
        balance=balance_row["balance"] if balance_row else None,
        uncategorized=uncategorized,
    )


@app.route("/api/category-trend")
@requires_auth
def category_trend():
    category = request.args.get("category", "")
    rows = db().execute(
        "SELECT substr(date,1,7) m, ROUND(-SUM(amount),2) total FROM transactions "
        "WHERE category=? GROUP BY m ORDER BY m", (category,)).fetchall()
    return jsonify([{"month": r["m"], "total": r["total"]} for r in rows][-12:])


@app.route("/api/transactions")
@requires_auth
def transactions():
    conn = db()
    where, params = period_filter(request.args.get("period", "all"))
    category = request.args.get("category")
    q = (request.args.get("q") or "").strip().lower()
    if category:
        where += " AND category=?"
        params.append(category)
    if q:
        where += " AND (lower(name) LIKE ? OR lower(description) LIKE ? OR lower(counter_account) LIKE ?)"
        params += [f"%{q}%"] * 3
    rows = conn.execute(
        f"SELECT id, date, name, counter_account, amount, mutation_type, description, category, manual "
        f"FROM transactions WHERE {where} ORDER BY date DESC, id DESC LIMIT 2000", params)
    return jsonify([dict(r) for r in rows])


@app.route("/api/transactions/<int:tx_id>", methods=["PATCH"])
@requires_auth
def update_transaction(tx_id):
    conn = db()
    data = request.get_json(force=True)
    category = data.get("category")
    if category not in category_kinds(conn):
        return jsonify(error="Onbekende categorie."), 400
    tx = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
    if not tx:
        return jsonify(error="Transactie niet gevonden."), 404
    conn.execute("UPDATE transactions SET category=?, manual=1 WHERE id=?", (category, tx_id))
    changed = 1
    if data.get("make_rule") and tx["name"]:
        pattern = tx["name"].strip().lower()
        direction = "af" if tx["amount"] < 0 else "bij"
        conn.execute("DELETE FROM rules WHERE user_defined=1 AND pattern=? AND direction=?",
                     (pattern, direction))
        conn.execute(
            "INSERT INTO rules(pattern, category, direction, user_defined) VALUES (?,?,?,1)",
            (pattern, category, direction))
        conn.commit()
        recategorize_all(conn)
        changed = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE category=? AND lower(name)=?",
            (category, pattern)).fetchone()[0]
    conn.commit()
    return jsonify(ok=True, changed=changed)


@app.route("/api/transactions/bulk", methods=["POST"])
@requires_auth
def bulk_update_transactions():
    """Zet een selectie transacties handmatig in een categorie."""
    conn = db()
    data = request.get_json(force=True)
    ids = [int(i) for i in data.get("ids", [])]
    category = data.get("category")
    if category not in category_kinds(conn) or not ids:
        return jsonify(error="Kies transacties en een categorie."), 400
    ph = ",".join("?" * len(ids))
    n = conn.execute(f"UPDATE transactions SET category=?, manual=1 WHERE id IN ({ph})",
                     [category] + ids).rowcount
    conn.commit()
    return jsonify(ok=True, changed=n)


@app.route("/api/transactions/<int:tx_id>/reset", methods=["POST"])
@requires_auth
def reset_transaction(tx_id):
    conn = db()
    conn.execute("UPDATE transactions SET manual=0 WHERE id=?", (tx_id,))
    conn.commit()
    recategorize_all(conn)
    return jsonify(ok=True)


@app.route("/api/rules")
@requires_auth
def rules():
    rows = db().execute(
        "SELECT id, pattern, category, direction, user_defined FROM rules "
        "ORDER BY user_defined DESC, category, pattern").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/rules", methods=["POST"])
@requires_auth
def add_rule():
    conn = db()
    data = request.get_json(force=True)
    pattern = (data.get("pattern") or "").strip().lower()
    category = data.get("category")
    direction = data.get("direction", "")
    if not pattern or category not in category_kinds(conn) or direction not in ("", "af", "bij"):
        return jsonify(error="Ongeldige regel."), 400
    conn.execute("INSERT INTO rules(pattern, category, direction, user_defined) VALUES (?,?,?,1)",
                 (pattern, category, direction))
    conn.commit()
    n = recategorize_all(conn)
    return jsonify(ok=True, recategorized=n)


@app.route("/api/rules/<int:rule_id>", methods=["DELETE"])
@requires_auth
def delete_rule(rule_id):
    conn = db()
    conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
    conn.commit()
    recategorize_all(conn)
    return jsonify(ok=True)


@app.route("/api/recategorize", methods=["POST"])
@requires_auth
def recategorize():
    return jsonify(recategorized=recategorize_all(db()))


@app.route("/api/subscriptions")
@requires_auth
def subscriptions():
    """Herkent terugkerende vaste lasten: zelfde tegenpartij, (bijna) zelfde bedrag,
    in minstens 3 verschillende maanden."""
    conn = db()
    kinds = category_kinds(conn)
    all_months = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(date,1,7) FROM transactions ORDER BY 1")]
    last_month = all_months[-1] if all_months else None
    groups = defaultdict(list)
    for r in conn.execute(
            "SELECT date, name, amount, category FROM transactions WHERE amount < 0 ORDER BY date"):
        if kinds.get(r["category"], "uitgave") != "uitgave":
            continue
        key = re.sub(r"[^a-z]+", " ", (r["name"] or "").lower()).strip()
        groups[key].append(r)

    result = []
    for key, items in groups.items():
        by_month = defaultdict(float)
        for it in items:
            by_month[it["date"][:7]] += -it["amount"]
        if len(by_month) < 3:
            continue
        amounts = list(by_month.values())
        med = statistics.median(amounts)
        if med <= 0:
            continue
        spread = statistics.pstdev(amounts) / med
        occurrences_per_month = len(items) / len(by_month)
        # Vaste lasten: stabiel bedrag en ongeveer één afschrijving per maand
        if spread > 0.15 or occurrences_per_month > 1.5:
            continue
        months_sorted = sorted(by_month)
        result.append({
            "name": items[-1]["name"],
            "category": items[-1]["category"],
            "monthly": round(med, 2),
            "yearly": round(med * 12, 2),
            "months": len(by_month),
            "last_date": items[-1]["date"],
            "active": months_sorted[-1] >= (all_months[-2] if len(all_months) > 1 else last_month),
            "last_amount": round(-items[-1]["amount"], 2),
            "changed": abs(-items[-1]["amount"] - med) > 0.01 and len(items) > 1,
        })
    result.sort(key=lambda x: (not x["active"], -x["monthly"]))
    return jsonify(result)


@app.route("/api/reset", methods=["POST"])
@requires_auth
def reset_all():
    if (request.get_json(force=True) or {}).get("confirm") != "WISSEN":
        return jsonify(error="Bevestiging ontbreekt."), 400
    conn = db()
    conn.execute("DELETE FROM transactions")
    conn.commit()
    return jsonify(ok=True)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
