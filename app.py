import sqlite3, uuid, re, os
from flask import Flask, render_template, request, redirect, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

STATS = ["Strength","Intelligence","Dexterity","Constitution","Charisma"]

# ================= STORAGE =================
def get_storage():
    persistent="/var/data"
    fallback="./data"

    if os.path.exists(persistent):
        mode="PERSISTENT"
        path=persistent
    else:
        mode="EPHEMERAL"
        path=fallback

    os.makedirs(path, exist_ok=True)

    return {
        "mode": mode,
        "db": os.path.join(path,"db.db")
    }

STORAGE=get_storage()

def get_conn():
    conn=sqlite3.connect(STORAGE["db"], timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ================= INIT =================
def init():
    conn=get_conn()
    c=conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY,name TEXT,image TEXT)")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stats(
    char_id TEXT,
    stat TEXT,
    base INT,
    buff INT,
    equip INT,
    PRIMARY KEY(char_id,stat))
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
    spells TEXT,
    inventory TEXT)
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills(
    char_id TEXT,
    name TEXT,
    val INT,
    PRIMARY KEY(char_id,name))
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS perc(
    char_id TEXT,
    name TEXT,
    val INT,
    PRIMARY KEY(char_id,name))
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS conditions(
    char_id TEXT,
    name TEXT,
    PRIMARY KEY(char_id,name))
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS effects(
    id TEXT PRIMARY KEY,
    char_id TEXT,
    name TEXT,
    value INT,
    duration INT,
    type TEXT,
    is_buff INT)
    """)

    conn.commit()
    conn.close()

# ================= PARSER =================
def clean(n):
    return re.sub(r'\s+',' ',(n or "").lower()).strip()

def safe_int(v):
    try:return int(v)
    except:return None

def parse_inventory(text):

    stats={s:0 for s in STATS}
    skills={}
    perc={}
    conditions=[]

    for line in (text or "").split("\n"):

        # CONDITIONS
        for c in re.findall(r'\((.*?)\)',line):
            c=clean(c)
            if c and c not in conditions:
                conditions.append(c)

        # PERCENTAGES
        for m in re.finditer(r'([+-]?\d+)\s*%\s*([a-zA-Z ]+)|([a-zA-Z ]+)\s*([+-]?\d+)\s*%',line):

            a,b,c,d=m.groups()

            val=safe_int(a or d)
            name=clean(b or c)

            if val is not None and name:
                perc[name]=perc.get(name,0)+val

        # STATS / SKILLS
        for m in re.finditer(r'([+-]?\d+)\s*([a-zA-Z ]+)|([a-zA-Z ]+)\s*([+-]?\d+)',line):

            a,b,c,d=m.groups()

            val=safe_int(a or d)
            name=clean(b or c)

            if val is None or not name:
                continue

            matched=False

            for s in STATS:
                if name.startswith(s[:3].lower()):
                    stats[s]+=val
                    matched=True
                    break

            if not matched:
                skills[name]=skills.get(name,0)+val

    return stats,skills,perc,conditions

# ================= ROUTES =================
@app.route("/")
def home():

    conn=get_conn()
    c=conn.cursor()

    c.execute("SELECT * FROM characters")
    chars=c.fetchall()

    conn.close()

    return render_template(
        "index.html",
        chars=chars,
        storage=STORAGE
    )

@app.route("/create",methods=["POST"])
def create():

    cid=str(uuid.uuid4())
    name=request.form.get("name","Crawler")

    conn=get_conn()
    c=conn.cursor()

    c.execute("INSERT INTO characters VALUES(?,?,?)",(cid,name,""))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES(?,?,?,?,?)",(cid,s,10,0,0))

    c.execute("""
    INSERT INTO meta VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """,(cid,1,100,100,0,0,0,0,"","",""))

    conn.commit()
    conn.close()

    return redirect(f"/c/{cid}")

# ================= IMAGE UPLOAD =================
@app.route("/upload/<cid>",methods=["POST"])
def upload(cid):

    file=request.files["image"]

    if file:
        filename=secure_filename(file.filename)
        path=os.path.join(UPLOAD_FOLDER,filename)
        file.save(path)

        conn=get_conn()
        c=conn.cursor()

        c.execute("UPDATE characters SET image=? WHERE id=?",(path,cid))

        conn.commit()
        conn.close()

    return redirect(f"/c/{cid}")

# ================= AUTOSAVE =================
@app.route("/autosave/<cid>",methods=["POST"])
def autosave(cid):

    data=request.json

    conn=get_conn()
    c=conn.cursor()

    inventory=data.get("inventory","")

    stat_b,skill_b,perc_b,conds=parse_inventory(inventory)

    # META
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
    spells=?,
    inventory=?
    WHERE char_id=?
    """,(
        data.get("level",1),
        data.get("hp",100),
        data.get("max_hp",100),
        data.get("gold",0),
        data.get("views",0),
        data.get("followers",0),
        data.get("favorites",0),
        data.get("equipment",""),
        data.get("spells",""),
        inventory,
        cid
    ))

    # STATS
    for s in STATS:
        c.execute("""
        UPDATE stats
        SET base=?,buff=?,equip=?
        WHERE char_id=? AND stat=?
        """,(
            data.get(f"base_{s}",10),
            data.get(f"buff_{s}",0),
            stat_b[s],
            cid,s
        ))

    # SKILLS
    c.execute("DELETE FROM skills WHERE char_id=?",(cid,))
    for k,v in skill_b.items():
        c.execute("INSERT INTO skills VALUES(?,?,?)",(cid,k,v))

    # PERCENT
    c.execute("DELETE FROM perc WHERE char_id=?",(cid,))
    for k,v in perc_b.items():
        c.execute("INSERT INTO perc VALUES(?,?,?)",(cid,k,v))

    # CONDITIONS
    c.execute("DELETE FROM conditions WHERE char_id=?",(cid,))
    for cond in conds:
        c.execute("INSERT INTO conditions VALUES(?,?)",(cid,cond))

    # EFFECTS
    c.execute("DELETE FROM effects WHERE char_id=?",(cid,))
    for e in data.get("effects",[]):

        c.execute("""
        INSERT INTO effects VALUES(?,?,?,?,?,?,?)
        """,(
            str(uuid.uuid4()),
            cid,
            e["name"],
            e["value"],
            e["duration"],
            e["type"],
            e["is_buff"]
        ))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

@app.route("/c/<cid>")
def char(cid):

    conn=get_conn()
    c=conn.cursor()

    c.execute("SELECT * FROM characters WHERE id=?",(cid,))
    character=c.fetchone()

    c.execute("SELECT stat,base,buff,equip FROM stats WHERE char_id=?",(cid,))
    stats={}

    for s,b,bu,e in c.fetchall():
        t=b+bu+e
        stats[s]={
            "base":b,
            "buff":bu,
            "equip":e,
            "total":t,
            "mod":t//5
        }

    c.execute("SELECT * FROM meta WHERE char_id=?",(cid,))
    meta=c.fetchone()

    c.execute("SELECT * FROM skills WHERE char_id=?",(cid,))
    skills=c.fetchall()

    c.execute("SELECT * FROM perc WHERE char_id=?",(cid,))
    percs=c.fetchall()

    c.execute("SELECT * FROM conditions WHERE char_id=?",(cid,))
    conds=c.fetchall()

    c.execute("SELECT name,value,duration,type,is_buff FROM effects WHERE char_id=?",(cid,))
    effects=c.fetchall()

    conn.close()

    return render_template(
        "character.html",
        character=character,
        stats=stats,
        meta=meta,
        skills=skills,
        percs=percs,
        conds=conds,
        effects=effects,
        storage=STORAGE
    )

init()

if __name__=="__main__":
    app.run()
