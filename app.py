import sqlite3, uuid, re
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
DB="db.db"

STATS=["Strength","Intelligence","Dexterity","Constitution","Charisma"]

# ---------- DB ----------
def init():
    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY,name TEXT)")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stats(
    char_id TEXT,stat TEXT,base INT,buff INT,equip INT,
    PRIMARY KEY(char_id,stat))""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS meta(
    char_id TEXT PRIMARY KEY,
    level INT,hp INT,max_hp INT,
    views INT,followers INT,favorites INT,
    equipment TEXT,spells TEXT,inventory TEXT)""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills(
    char_id TEXT,name TEXT,base INT,equip INT,
    PRIMARY KEY(char_id,name))""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS perc(
    char_id TEXT,name TEXT,val INT,
    PRIMARY KEY(char_id,name))""")

    conn.commit(); conn.close()

# ---------- UTILS ----------
def mod(v): return v//5

def clean(n):
    return n.lower().replace("skill","").strip()

def smart_parse(text):
    stats={s:0 for s in STATS}
    skills={}
    perc={}

    patterns=[
        r'([a-zA-Z ]+)\s*([+-]?\d+)%',
        r'([+-]?\d+)%\s*([a-zA-Z ]+)',
        r'([a-zA-Z ]+)\s*([+-]?\d+)',
        r'([+-]?\d+)\s*([a-zA-Z ]+)'
    ]

    for p in patterns:
        for m in re.findall(p,text):
            a,b=m

            if "%" in p:
                if "%" in a:
                    val=int(a.replace("%",""))
                    name=clean(b)
                else:
                    val=int(b)
                    name=clean(a)

                perc[name]=perc.get(name,0)+val

            else:
                if a.strip().lstrip("+-").isdigit():
                    val=int(a)
                    name=clean(b)
                else:
                    val=int(b)
                    name=clean(a)

                found=False
                for s in STATS:
                    if name.startswith(s[:3].lower()):
                        stats[s]+=val
                        found=True
                        break

                if not found:
                    skills[name]=skills.get(name,0)+val

    return stats,skills,perc

# ---------- ROUTES ----------
@app.route("/")
def home():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT * FROM characters")
    chars=c.fetchall()
    conn.close()
    return render_template("index.html",chars=chars)

@app.route("/create",methods=["POST"])
def create():
    cid=str(uuid.uuid4())
    name=request.form.get("name","Crawler")

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("INSERT INTO characters VALUES(?,?)",(cid,name))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES(?,?,?,?,?)",(cid,s,10,0,0))

    c.execute("INSERT INTO meta VALUES(?,?,?,?,?,?,?,?,?,?)",
              (cid,1,100,100,0,0,0,"","",""))

    conn.commit(); conn.close()
    return redirect(f"/c/{cid}")

@app.route("/c/<cid>",methods=["GET","POST"])
def char(cid):
    conn=sqlite3.connect(DB)
    c=conn.cursor()

    if request.method=="POST":

        # stats
        for s in STATS:
            base=int(request.form.get(f"base_{s}",10) or 10)
            buff=int(request.form.get(f"buff_{s}",0) or 0)
            c.execute("UPDATE stats SET base=?,buff=? WHERE char_id=? AND stat=?",
                      (base,buff,cid,s))

        equip_text=request.form.get("equipment","")
        stat_b,skill_b,perc_b=smart_parse(equip_text)

        for s in STATS:
            c.execute("UPDATE stats SET equip=? WHERE char_id=? AND stat=?",
                      (stat_b[s],cid,s))

        # skills
        c.execute("DELETE FROM skills WHERE char_id=?",(cid,))
        names=request.form.getlist("skill_name")
        vals=request.form.getlist("skill_val")

        for n,v in zip(names,vals):
            n=clean(n)
            if not n: continue
            try: base=int(v)
            except: base=0

            equip=skill_b.get(n,0)
            c.execute("INSERT OR REPLACE INTO skills VALUES(?,?,?,?)",
                      (cid,n,base,equip))

        # add equip-only skills
        for k,v in skill_b.items():
            c.execute("INSERT OR IGNORE INTO skills VALUES(?,?,?,?)",
                      (cid,k,0,v))

        # percentages
        c.execute("DELETE FROM perc WHERE char_id=?",(cid,))
        for k,v in perc_b.items():
            c.execute("INSERT INTO perc VALUES(?,?,?)",(cid,k,v))

        # meta
        c.execute("""
        UPDATE meta SET level=?,hp=?,max_hp=?,views=?,followers=?,favorites=?,
        equipment=?,spells=?,inventory=? WHERE char_id=?""",
        (request.form["level"],request.form["hp"],request.form["max_hp"],
         request.form["views"],request.form["followers"],request.form["favorites"],
         equip_text,request.form["spells"],request.form["inventory"],cid))

        conn.commit()

    # LOAD
    c.execute("SELECT stat,base,buff,equip FROM stats WHERE char_id=?",(cid,))
    stats={}
    for s,b,bu,e in c.fetchall():
        t=b+bu+e
        stats[s]={"base":b,"buff":bu,"total":t,"mod":mod(t)}

    c.execute("SELECT * FROM meta WHERE char_id=?",(cid,))
    meta=c.fetchone()

    c.execute("SELECT name,base,equip FROM skills WHERE char_id=?",(cid,))
    skills=c.fetchall()

    c.execute("SELECT name,val FROM perc WHERE char_id=?",(cid,))
    percs=c.fetchall()

    conn.close()

    return render_template("character.html",
        cid=cid,stats=stats,meta=meta,skills=skills,percs=percs)

init()

if __name__=="__main__":
    app.run()
