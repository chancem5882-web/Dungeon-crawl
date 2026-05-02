import sqlite3, uuid, re, os
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

STATS = ["Strength","Intelligence","Dexterity","Constitution","Charisma"]

# 💾 INTELLIGENT STORAGE SYSTEM
def get_storage():
    persistent_path = "/var/data"
    local_path = "./data"

    if os.path.exists(persistent_path):
        mode = "PERSISTENT"
        path = persistent_path
    else:
        mode = "EPHEMERAL"
        path = local_path

    os.makedirs(path, exist_ok=True)

    return {
        "mode": mode,
        "path": path,
        "db": os.path.join(path, "db.db")
    }

STORAGE = get_storage()

def get_conn():
    conn = sqlite3.connect(STORAGE["db"], timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ---------- INIT ----------
def init():
    conn = get_conn()
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY,name TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS stats(char_id TEXT,stat TEXT,base INT,buff INT,equip INT,PRIMARY KEY(char_id,stat))")
    c.execute("""CREATE TABLE IF NOT EXISTS meta(
        char_id TEXT PRIMARY KEY,
        level INT,hp INT,max_hp INT,
        views INT,followers INT,favorites INT,
        equipment TEXT,spells TEXT,inventory TEXT)""")
    c.execute("CREATE TABLE IF NOT EXISTS skills(char_id TEXT,name TEXT,base INT,equip INT,PRIMARY KEY(char_id,name))")
    c.execute("CREATE TABLE IF NOT EXISTS perc(char_id TEXT,name TEXT,val INT,PRIMARY KEY(char_id,name))")

    conn.commit()
    conn.close()

# ---------- PARSER ----------
def clean(n):
    return re.sub(r'\s+',' ',(n or "").lower().replace("skill","")).strip()

def safe_int(v):
    try: return int(v)
    except: return None

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

    return render_template("index.html",
        chars=chars,
        storage=STORAGE)

@app.route("/create",methods=["POST"])
def create():
    cid=str(uuid.uuid4())
    name=request.form.get("name","Crawler")

    conn=get_conn()
    c=conn.cursor()

    c.execute("INSERT INTO characters VALUES(?,?)",(cid,name))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES(?,?,?,?,?)",(cid,s,10,0,0))

    c.execute("INSERT INTO meta VALUES(?,?,?,?,?,?,?,?,?,?)",
              (cid,1,100,100,0,0,0,"","",""))

    conn.commit()
    conn.close()

    return redirect(f"/c/{cid}")

@app.route("/c/<cid>",methods=["GET","POST"])
def char(cid):
    conn=get_conn()
    c=conn.cursor()

    errors=[]

    if request.method=="POST":

        level=int(request.form.get("level",1) or 1)
        hp=int(request.form.get("hp",100) or 100)
        max_hp=int(request.form.get("max_hp",100) or 100)
        views=int(request.form.get("views",0) or 0)
        followers=int(request.form.get("followers",0) or 0)
        favorites=int(request.form.get("favorites",0) or 0)

        for s in STATS:
            base=int(request.form.get(f"base_{s}",10) or 10)
            buff=int(request.form.get(f"buff_{s}",0) or 0)
            c.execute("UPDATE stats SET base=?,buff=? WHERE char_id=? AND stat=?",(base,buff,cid,s))

        equip_text=request.form.get("equipment","")
        stat_b,skill_b,perc_b,errors=parse(equip_text)

        for s in STATS:
            c.execute("UPDATE stats SET equip=? WHERE char_id=? AND stat=?",(stat_b[s],cid,s))

        c.execute("DELETE FROM skills WHERE char_id=?",(cid,))
        for k,v in skill_b.items():
            c.execute("INSERT INTO skills VALUES(?,?,?,?)",(cid,k,0,v))

        c.execute("DELETE FROM perc WHERE char_id=?",(cid,))
        for k,v in perc_b.items():
            c.execute("INSERT INTO perc VALUES(?,?,?)",(cid,k,v))

        c.execute("""
        UPDATE meta SET level=?,hp=?,max_hp=?,views=?,followers=?,favorites=?,
        equipment=?,spells=?,inventory=? WHERE char_id=?""",
        (level,hp,max_hp,views,followers,favorites,
         equip_text,
         request.form.get("spells",""),
         request.form.get("inventory",""),
         cid))

        conn.commit()

    # load
    c.execute("SELECT stat,base,buff,equip FROM stats WHERE char_id=?",(cid,))
    stats={}
    for s,b,bu,e in c.fetchall():
        t=b+bu+e
        stats[s]={"base":b,"buff":bu,"total":t,"mod":t//5}

    c.execute("SELECT * FROM meta WHERE char_id=?",(cid,))
    meta=c.fetchone()

    c.execute("SELECT name,base,equip FROM skills WHERE char_id=?",(cid,))
    skills=c.fetchall()

    c.execute("SELECT name,val FROM perc WHERE char_id=?",(cid,))
    percs=c.fetchall()

    conn.close()

    return render_template("character.html",
        cid=cid,stats=stats,meta=meta,
        skills=skills,percs=percs,
        errors=errors,
        storage=STORAGE)

init()

if __name__=="__main__":
    app.run()
