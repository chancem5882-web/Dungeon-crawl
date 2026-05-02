import sqlite3
import uuid
import re
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB = "database.db"

STATS = ["Strength", "Intelligence", "Dexterity", "Constitution", "Charisma"]

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        char_id TEXT,
        stat TEXT,
        base INTEGER,
        buff INTEGER,
        equipment INTEGER,
        PRIMARY KEY (char_id, stat)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        char_id TEXT PRIMARY KEY,
        level INTEGER,
        hp INTEGER,
        max_hp INTEGER,
        inventory TEXT,
        spells TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        char_id TEXT,
        name TEXT,
        value INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS percentages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        char_id TEXT,
        effect TEXT,
        value REAL
    )
    """)

    conn.commit()
    conn.close()

# ---------------- CORE ----------------
def mod(val):
    return val // 5

# ---------------- PARSER ----------------
def parse_equipment(text):
    stat_bonus = {s: 0 for s in STATS}
    skill_bonus = []
    percent_bonus = []

    # +3 STR, +2 Dexterity
    stat_matches = re.findall(r'([+-]\d+)\s*(STR|DEX|CON|INT|CHA|Strength|Dexterity|Constitution|Intelligence|Charisma)', text, re.I)

    for val, stat in stat_matches:
        val = int(val)
        s = stat.lower()
        if "str" in s: stat_bonus["Strength"] += val
        elif "dex" in s: stat_bonus["Dexterity"] += val
        elif "con" in s: stat_bonus["Constitution"] += val
        elif "int" in s: stat_bonus["Intelligence"] += val
        elif "cha" in s: stat_bonus["Charisma"] += val

    # +5% something
    percent_matches = re.findall(r'([+-]?\d+)%\s*([\w\s]+)', text)

    for val, effect in percent_matches:
        percent_bonus.append((effect.strip(), float(val)))

    # skill bonuses
skill_matches = re.findall(
    r'\+(\d+)\s*(?:skill\s*:?\s*|to\s+)?([a-zA-Z][a-zA-Z\s]+)',
    text,
    re.IGNORECASE
)

for val, skill in skill_matches:
    skill = skill.strip().lower()

    # Skip if it's actually a stat (prevents overlap)
    if skill in ["strength", "dexterity", "constitution", "intelligence", "charisma"]:
        continue

    try:
        skill_bonus.append((skill, int(val)))
    except:
        continue  # fail-safe, no crash

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, name FROM characters")
    chars = c.fetchall()
    conn.close()
    return render_template("index.html", chars=chars)

@app.route("/create", methods=["POST"])
def create():
    name = request.form["name"]
    cid = str(uuid.uuid4())

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO characters VALUES (?,?)", (cid, name))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES (?,?,?,?,?)", (cid, s, 10, 0, 0))

    c.execute("INSERT INTO meta VALUES (?,?,?,?,?,?)",
              (cid, 1, 100, 100, "", ""))

    conn.commit()
    conn.close()

    return redirect(url_for("character", char_id=cid))

@app.route("/character/<char_id>", methods=["GET", "POST"])
def character(char_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if request.method == "POST":

        # stats
        for s in STATS:
            base = int(request.form.get(f"base_{s}", 10))
            buff = int(request.form.get(f"buff_{s}", 0))

            c.execute("""
                UPDATE stats SET base=?, buff=? 
                WHERE char_id=? AND stat=?
            """, (base, buff, char_id, s))

        # meta
        level = int(request.form["level"])
        hp = int(request.form["hp"])
        max_hp = int(request.form["max_hp"])
        inventory = request.form["inventory"]
        spells = request.form["spells"]

        c.execute("""
        UPDATE meta SET level=?, hp=?, max_hp=?, inventory=?, spells=?
        WHERE char_id=?
        """, (level, hp, max_hp, inventory, spells, char_id))

        # EQUIPMENT PARSING
        equip_text = request.form["equipment"]

        stat_bonus, skill_bonus, percent_bonus = parse_equipment(equip_text)

        # apply stat bonuses
        for s in STATS:
            c.execute("""
            UPDATE stats SET equipment=? 
            WHERE char_id=? AND stat=?
            """, (stat_bonus[s], char_id, s))

        # skills reset + insert
        c.execute("DELETE FROM skills WHERE char_id=?", (char_id,))
        for name, val in skill_bonus:
            c.execute("""
            INSERT INTO skills (char_id,name,value)
            VALUES (?,?,?)
            """, (char_id, name, val))

        # percentages reset + insert
        c.execute("DELETE FROM percentages WHERE char_id=?", (char_id,))
        for eff, val in percent_bonus:
            c.execute("""
            INSERT INTO percentages (char_id,effect,value)
            VALUES (?,?,?)
            """, (char_id, eff, val))

        conn.commit()

    # LOAD
    c.execute("SELECT name FROM characters WHERE id=?", (char_id,))
    name = c.fetchone()[0]

    c.execute("SELECT stat, base, buff, equipment FROM stats WHERE char_id=?", (char_id,))
    stats = c.fetchall()

    stat_data = {}
    for s, b, bf, eq in stats:
        total = b + bf + eq
        stat_data[s] = {
            "total": total,
            "mod": mod(total)
        }

    c.execute("SELECT level,hp,max_hp,inventory,spells FROM meta WHERE char_id=?", (char_id,))
    level, hp, max_hp, inv, spells = c.fetchone()

    c.execute("SELECT name,value FROM skills WHERE char_id=?", (char_id,))
    skills = c.fetchall()

    c.execute("SELECT effect,value FROM percentages WHERE char_id=?", (char_id,))
    percents = c.fetchall()

    conn.close()

    return render_template(
        "character.html",
        char_id=char_id,
        name=name,
        stats=stat_data,
        level=level,
        hp=hp,
        max_hp=max_hp,
        inventory=inv,
        spells=spells,
        skills=skills,
        percents=percents
    )

init_db()

if __name__ == "__main__":
    app.run(debug=True)
