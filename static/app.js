import sqlite3
import uuid
import re
import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    jsonify,
    send_from_directory
)

from werkzeug.utils import secure_filename

app = Flask(__name__)

# ==================================================
# STORAGE
# ==================================================

def get_storage():

    persistent = "/var/data"
    fallback = "./data"

    if os.path.exists(persistent):
        base = persistent
    else:
        base = fallback

    os.makedirs(base, exist_ok=True)

    return {
        "base": base,
        "db": os.path.join(base, "db.db"),
        "uploads": os.path.join(base, "uploads")
    }

STORAGE = get_storage()

os.makedirs(STORAGE["uploads"], exist_ok=True)

# ==================================================
# DATABASE
# ==================================================

STATS = [
    "Strength",
    "Intelligence",
    "Dexterity",
    "Constitution",
    "Charisma"
]

def get_conn():

    conn = sqlite3.connect(
        STORAGE["db"],
        timeout=10
    )

    conn.execute(
        "PRAGMA journal_mode=WAL;"
    )

    return conn

def init():

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS characters(
        id TEXT PRIMARY KEY,
        name TEXT,
        image TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS stats(
        char_id TEXT,
        stat TEXT,
        base INT,
        buff INT,
        equip INT,
        PRIMARY KEY(char_id, stat)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS meta(
        char_id TEXT PRIMARY KEY,
        level INT,
        hp INT,
        max_hp INT,
        gold INT,
        views INT,
        followers INT,
        favorites INT,
        equipment TEXT,
        inventory TEXT,
        spells TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills(
        char_id TEXT,
        name TEXT,
        val INT,
        PRIMARY KEY(char_id,name)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS percentages(
        char_id TEXT,
        name TEXT,
        val INT,
        PRIMARY KEY(char_id,name)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS conditions(
        char_id TEXT,
        name TEXT,
        PRIMARY KEY(char_id,name)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS effects(
        id TEXT PRIMARY KEY,
        char_id TEXT,
        name TEXT,
        value INT,
        duration INT,
        duration_type TEXT,
        is_buff INT
    )
    """)

    conn.commit()
    conn.close()

# ==================================================
# PARSER
# ==================================================

def clean(t):
    return re.sub(
        r'\s+',
        ' ',
        (t or "").lower()
    ).strip()

def parse_equipment(text):

    stats = {s:0 for s in STATS}
    skills = {}
    perc = {}
    conditions = []

    for line in (text or "").split("\n"):

        # CONDITIONS
        for c in re.findall(r'\((.*?)\)', line):

            c = clean(c)

            if c and c not in conditions:
                conditions.append(c)

        # PERCENT
        for m in re.finditer(
            r'([+-]?\d+)\s*%\s*([a-zA-Z ]+)'
            r'|'
            r'([a-zA-Z ]+)\s*([+-]?\d+)\s*%',
            line
        ):

            a,b,c,d = m.groups()

            try:
                val = int(a or d)
            except:
                continue

            name = clean(b or c)

            perc[name] = perc.get(name,0) + val

        # STATS / SKILLS
        for m in re.finditer(
            r'([+-]?\d+)\s*([a-zA-Z ]+)'
            r'|'
            r'([a-zA-Z ]+)\s*([+-]?\d+)',
            line
        ):

            a,b,c,d = m.groups()

            try:
                val = int(a or d)
            except:
                continue

            name = clean(b or c)

            matched = False

            for s in STATS:

                if name.startswith(
                    s[:3].lower()
                ):

                    stats[s] += val
                    matched = True
                    break

            if not matched and name:
                skills[name] = skills.get(name,0) + val

    return stats, skills, perc, conditions

# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM characters"
    )

    chars = c.fetchall()

    conn.close()

    return render_template(
        "index.html",
        chars=chars
    )

# ==================================================
# CREATE CHARACTER
# ==================================================

@app.route("/create", methods=["POST"])
def create():

    cid = str(uuid.uuid4())

    name = request.form.get(
        "name",
        "Crawler"
    )

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "INSERT INTO characters VALUES(?,?,?)",
        (cid, name, "")
    )

    for s in STATS:

        c.execute(
            "INSERT INTO stats VALUES(?,?,?,?,?)",
            (cid,s,10,0,0)
        )

    c.execute("""
    INSERT INTO meta VALUES(
        ?,?,?,?,?,?,?,?,?,?,?
    )
    """,(
        cid,
        1,
        100,
        100,
        0,
        0,
        0,
        0,
        "",
        "",
        ""
    ))

    conn.commit()
    conn.close()

    return redirect(f"/c/{cid}")

# ==================================================
# IMAGE ROUTE
# ==================================================

@app.route("/image/<filename>")
def image(filename):

    return send_from_directory(
        STORAGE["uploads"],
        filename
    )

# ==================================================
# IMAGE UPLOAD
# ==================================================

@app.route("/upload/<cid>", methods=["POST"])
def upload(cid):

    if "image" not in request.files:
        return redirect(f"/c/{cid}")

    file = request.files["image"]

    if file.filename == "":
        return redirect(f"/c/{cid}")

    ext = os.path.splitext(
        secure_filename(file.filename)
    )[1]

    filename = f"{uuid.uuid4()}{ext}"

    save_path = os.path.join(
        STORAGE["uploads"],
        filename
    )

    file.save(save_path)

    image_path = f"/image/{filename}"

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    UPDATE characters
    SET image=?
    WHERE id=?
    """,(
        image_path,
        cid
    ))

    conn.commit()
    conn.close()

    return redirect(f"/c/{cid}")

# ==================================================
# AUTOSAVE
# ==================================================

@app.route("/autosave/<cid>", methods=["POST"])
def autosave(cid):

    data = request.json

    equipment = data.get(
        "equipment",
        ""
    )

    stat_bonus, skill_bonus, perc_bonus, conds = parse_equipment(
        equipment
    )

    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    UPDATE meta SET
        level=?,
        hp=?,
        max_hp=?,
        gold=?,
        views=?,
        followers=?,
        favorites=?,
        equipment=?,
        inventory=?,
        spells=?
    WHERE char_id=?
    """,(
        data.get("level",1),
        data.get("hp",100),
        data.get("max_hp",100),
        data.get("gold",0),
        data.get("views",0),
        data.get("followers",0),
        data.get("favorites",0),
        equipment,
        data.get("inventory",""),
        data.get("spells",""),
        cid
    ))

    for s in STATS:

        c.execute("""
        UPDATE stats
        SET base=?, buff=?, equip=?
        WHERE char_id=? AND stat=?
        """,(
            int(data.get(f"base_{s}",10)),
            int(data.get(f"buff_{s}",0)),
            stat_bonus[s],
            cid,
            s
        ))

    c.execute(
        "DELETE FROM skills WHERE char_id=?",
        (cid,)
    )

    for k,v in skill_bonus.items():

        c.execute(
            "INSERT INTO skills VALUES(?,?,?)",
            (cid,k,v)
        )

    c.execute(
        "DELETE FROM percentages WHERE char_id=?",
        (cid,)
    )

    for k,v in perc_bonus.items():

        c.execute(
            "INSERT INTO percentages VALUES(?,?,?)",
            (cid,k,v)
        )

    c.execute(
        "DELETE FROM conditions WHERE char_id=?",
        (cid,)
    )

    for cond in conds:

        c.execute(
            "INSERT INTO conditions VALUES(?,?)",
            (cid,cond)
        )

    conn.commit()
    conn.close()

    return jsonify({"ok":True})

# ==================================================
# CHARACTER PAGE
# ==================================================

@app.route("/c/<cid>")
def character(cid):

    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM characters WHERE id=?",
        (cid,)
    )

    character = c.fetchone()

    c.execute("""
    SELECT stat,base,buff,equip
    FROM stats
    WHERE char_id=?
    """,(cid,))

    stats = {}

    for s,b,bu,e in c.fetchall():

        total = b + bu + e

        stats[s] = {
            "base": b,
            "buff": bu,
            "equip": e,
            "total": total,
            "mod": total // 5
        }

    c.execute(
        "SELECT * FROM meta WHERE char_id=?",
        (cid,)
    )

    meta = c.fetchone()

    c.execute(
        "SELECT * FROM skills WHERE char_id=?",
        (cid,)
    )

    skills = c.fetchall()

    c.execute(
        "SELECT * FROM percentages WHERE char_id=?",
        (cid,)
    )

    percentages = c.fetchall()

    c.execute(
        "SELECT * FROM conditions WHERE char_id=?",
        (cid,)
    )

    conditions = c.fetchall()

    conn.close()

    return render_template(
        "character.html",
        character=character,
        stats=stats,
        meta=meta,
        skills=skills,
        percentages=percentages,
        conditions=conditions
    )

init()

if __name__ == "__main__":
    app.run()
