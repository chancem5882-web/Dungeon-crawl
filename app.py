import sqlite3, uuid, re, os
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)

STATS = ["Strength","Intelligence","Dexterity","Constitution","Charisma"]

# ---------- STORAGE ----------
def get_storage():
    if os.path.exists("/var/data"):
        path="/var/data"
        mode="PERSISTENT"
    else:
        path="./data"
        mode="EPHEMERAL"

    os.makedirs(path, exist_ok=True)

    return {"path":path,"mode":mode,"db":os.path.join(path,"db.db")}

STORAGE = get_storage()

def get_conn():
    conn=sqlite3.connect(STORAGE["db"],timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ---------- INIT ----------
def init():
    conn=get_conn()
    c=conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY,name TEXT)")

    c.execute("CREATE TABLE IF NOT EXISTS stats(char_id TEXT,stat TEXT,base INT,buff INT,equip INT,PRIMARY KEY(char_id,stat))")

    c.execute("""CREATE TABLE IF NOT EXISTS meta(
        char_id TEXT PRIMARY KEY,
        level INT,hp INT,max_hp INT,gold INT,
        views INT,followers INT,favorites INT,
        equipment TEXT,spells TEXT,inventory TEXT)""")

    c.execute("CREATE TABLE IF NOT EXISTS skills(char_id TEXT,name TEXT,base INT,equip INT,PRIMARY KEY(char_id,name))")
    c.execute("CREATE TABLE IF NOT EXISTS perc(char_id TEXT,name TEXT,val INT,PRIMARY KEY(char_id,name))")

    # 💀 Buff/Debuff system
    c.execute("""
    CREATE TABLE IF NOT EXISTS effects(
        id TEXT PRIMARY KEY,
        char_id TEXT,
        name TEXT,
        value INT,
        type TEXT,
        duration INT,
        unit TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------- PARSER ----------
def clean(n):
    return re.sub(r'\s+',' ',(n or "").lower().replace("skill","")).strip()

def safe_int(v):
    try:return int(v)
    except:return None

def parse(text):
    stats={s:0 for s in STATS}
    skills={}
    perc={}
    errors=[]

    for i,line in enumerate((text or "").split("\n")):
        raw=line
        line=line.strip().lower()
        if not line: continue
        parsed=False

        try:
            for m in re.finditer(r'([+-]?\d+)\s*%\s*([a-zA-Z ]+)|([a-zA-Z ]+)\s*([+-]?\d+)\s*%',line):
                a,b,c,d=m.groups()
                val=safe_int(a or d)
                name=clean(b or c)
                if val and name:
                    perc[name]=perc.get(name,0)+val
                    parsed=True

            line=re.sub(r'([+-]?\d+\s*%\s*[a-zA-Z ]+)|([a-zA-Z ]+\s*[+-]?\d+\s*%)','',line)

            for m in re.finditer(r'([+-]?\d+)\s*([a-zA-Z ]+)|([a-zA-Z ]+)\s*([+-]?\d+)',line):
                a,b,c,d=m.groups()
                val=safe_int(a or d)
                name=clean(b or c)
                if val is None or not name: continue

                matched=False
                for s in STATS:
                    if name.startswith(s[:3].lower()):
                        stats[s]+=val
                        matched=True
                        break

                if not matched:
                    skills[name]=skills.get(name,0)+val

                parsed=True
        except:
            errors.append(f"Line {i+1}: '{raw}' error")

        if not parsed:
            errors.append(f"Line {i+1}: '{raw}' not understood")

    return stats,skills,perc,errors

# ---------- ROUTES ----------
@app.route("/")
def home():
    conn=get_conn()
    c=conn.cursor()
    c.execute("SELECT * FROM characters")
    chars=c.fetchall()
    conn.close()
    return render_template("index.html",chars=chars,storage=STORAGE)

@app.route("/create",methods=["POST"])
def create():
    cid=str(uuid.uuid4())
    name=request.form.get("name","Crawler")

    conn=get_conn()
    c=conn.cursor()

    c.execute("INSERT INTO characters VALUES(?,?)",(cid,name))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES(?,?,?,?,?)",(cid,s,10,0,0))

    c.execute("INSERT INTO meta VALUES(?,?,?,?,?,?,?,?,?,?,?)",
              (cid,1,100,100,0,0,0,0,"","",""))

    conn.commit()
    conn.close()
    return redirect(f"/c/{cid}")

# 💾 AUTOSAVE API
@app.route("/autosave/<cid>",methods=["POST"])
def autosave(cid):
    data=request.json
    conn=get_conn()
    c=conn.cursor()

    # basic meta save
    c.execute("""
    UPDATE meta SET level=?,hp=?,max_hp=?,gold=?,views=?,followers=?,favorites=?,
    equipment=?,spells=?,inventory=? WHERE char_id=?""",
    (data["level"],data["hp"],data["max_hp"],data["gold"],
     data["views"],data["followers"],data["favorites"],
     data["equipment"],data["spells"],data["inventory"],cid))

    conn.commit()
    conn.close()
    return jsonify({"status":"ok"})

# Buff/Debuff endpoints
@app.route("/add_effect/<cid>",methods=["POST"])
def add_effect(cid):
    data=request.json
    conn=get_conn()
    c=conn.cursor()

    eid=str(uuid.uuid4())

    c.execute("INSERT INTO effects VALUES(?,?,?,?,?,?,?)",
              (eid,cid,data["name"],data["value"],data["type"],
               data["duration"],data["unit"]))

    conn.commit()
    conn.close()
    return jsonify({"status":"ok"})

@app.route("/tick_effect/<eid>",methods=["POST"])
def tick_effect(eid):
    conn=get_conn()
    c=conn.cursor()

    c.execute("UPDATE effects SET duration = duration - 1 WHERE id=?",(eid,))
    c.execute("DELETE FROM effects WHERE id=? AND duration <= 0",(eid,))

    conn.commit()
    conn.close()
    return jsonify({"status":"ok"})

@app.route("/c/<cid>")
def char(cid):
    conn=get_conn()
    c=conn.cursor()

    c.execute("SELECT stat,base,buff,equip FROM stats WHERE char_id=?",(cid,))
    stats={}
    for s,b,bu,e in c.fetchall():
        t=b+bu+e
        stats[s]={"base":b,"buff":bu,"total":t,"mod":t//5}

    c.execute("SELECT * FROM meta WHERE char_id=?",(cid,))
    meta=c.fetchone()

    c.execute("SELECT name,val FROM perc WHERE char_id=?",(cid,))
    percs=c.fetchall()

    c.execute("SELECT * FROM effects WHERE char_id=?",(cid,))
    effects=c.fetchall()

    conn.close()

    return render_template("character.html",
        cid=cid,stats=stats,meta=meta,
        percs=percs,effects=effects,
        storage=STORAGE)

init()

if __name__=="__main__":
    app.run()
