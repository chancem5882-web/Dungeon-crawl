import re
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB = "database.db"

STATS = ["Strength", "Intelligence", "Dexterity", "Constitution", "Charisma"]

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            char_id TEXT,
            stat TEXT,
            base INTEGER,
            buff INTEGER,
            equipment INTEGER,
            PRIMARY KEY (char_id, stat)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS equipment_notes (
            char_id TEXT PRIMARY KEY,
            text TEXT
        )
    ''')

    conn.commit()
    conn.close()

# ---------- UTILS ----------
def calculate_modifier(value):
    return value // 5

def parse_equipment(text):
    bonuses = {stat: 0 for stat in STATS}

    # Matches things like "+3 STR", "+2 Strength"
    matches = re.findall(r'([+-]?\d+)\s*(STR|DEX|CON|INT|CHA|Strength|Dexterity|Constitution|Intelligence|Charisma)', text, re.IGNORECASE)

    for val, stat in matches:
        val = int(val)
        stat = stat.lower()

        if stat.startswith("str"):
            bonuses["Strength"] += val
        elif stat.startswith("dex"):
            bonuses["Dexterity"] += val
        elif stat.startswith("con"):
            bonuses["Constitution"] += val
        elif stat.startswith("int"):
            bonuses["Intelligence"] += val
        elif stat.startswith("cha"):
            bonuses["Charisma"] += val

    return bonuses

# ---------- ROUTES ----------
@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name FROM characters")
    chars = c.fetchall()
    conn.close()
    return render_template("index.html", characters=chars)

@app.route("/create", methods=["POST"])
def create():
    name = request.form.get("name", "Unnamed Crawler")
    char_id = str(uuid.uuid4())

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO characters VALUES (?, ?)", (char_id, name))

    for stat in STATS:
        c.execute("INSERT INTO stats VALUES (?, ?, ?, ?, ?)", (char_id, stat, 10, 0, 0))

    c.execute("INSERT INTO equipment_notes VALUES (?, ?)", (char_id, ""))

    conn.commit()
    conn.close()

    return redirect(url_for("character", char_id=char_id))

@app.route("/character/<char_id>", methods=["GET", "POST"])
def character(char_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":
        for stat in STATS:
            base = int(request.form.get(f"base_{stat}", 10))
            buff = int(request.form.get(f"buff_{stat}", 0))

            c.execute("""
                UPDATE stats
                SET base=?, buff=?
                WHERE char_id=? AND stat=?
            """, (base, buff, char_id, stat))

        # Equipment parsing
        equip_text = request.form.get("equipment_text", "")
        bonuses = parse_equipment(equip_text)

        for stat in STATS:
            c.execute("""
                UPDATE stats
                SET equipment=?
                WHERE char_id=? AND stat=?
            """, (bonuses[stat], char_id, stat))

        c.execute("""
            UPDATE equipment_notes SET text=? WHERE char_id=?
        """, (equip_text, char_id))

        conn.commit()

    # Load stats
    c.execute("SELECT stat, base, buff, equipment FROM stats WHERE char_id=?", (char_id,))
    rows = c.fetchall()

    stats = {}
    for stat, base, buff, equip in rows:
        total = base + buff + equip
        stats[stat] = {
            "base": base,
            "buff": buff,
            "equipment": equip,
            "total": total,
            "mod": calculate_modifier(total)
        }

    c.execute("SELECT text FROM equipment_notes WHERE char_id=?", (char_id,))
    equip_text = c.fetchone()[0]

    c.execute("SELECT name FROM characters WHERE id=?", (char_id,))
    name = c.fetchone()[0]

    conn.close()

    return render_template("character.html",
                           stats=stats,
                           char_id=char_id,
                           equip_text=equip_text,
                           name=name)

# ---------- INIT ----------
init_db()

if __name__ == "__main__":
    app.run(debug=True)
