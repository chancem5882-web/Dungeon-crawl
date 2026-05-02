import sqlite3, uuid, re
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB = "db.db"

STATS = ["Strength","Intelligence","Dexterity","Constitution","Charisma"]

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS characters (id TEXT PRIMARY KEY, name TEXT)")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        char_id TEXT, stat TEXT,
        base INT, buff INT, equip INT,
        PRIMARY KEY(char_id, stat)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        char_id TEXT PRIMARY KEY,
        level INT, hp INT, max_hp INT,
        views INT, followers INT, favorites INT,
        equipment TEXT, spells TEXT, inventory TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        char_id TEXT, name TEXT, base INT, equip INT,
        PRIMARY KEY(char_id, name)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS percentages (
        char_id TEXT, name TEXT, value INT,
        PRIMARY KEY(char_id, name)
    )
    """)

    conn.commit()
    conn.close()

# ---------- MODIFIER ----------
def mod(v): return v // 5

# ---------- PARSER ----------
def parse(text):
    stat_bonus = {s:0 for s in STATS}
    skill_bonus = {}
    percent_bonus = {}

    matches = re.findall(r'([+-]?\d+)\s*(%?)([a-zA-Z ]+)', text)

    for val, is_percent, name in matches:
        val = int(val)
        name = name.strip().lower()

        if is_percent:
            percent_bonus[name] = percent_bonus.get(name,0)+val
        else:
            # stats
            for s in STATS:
                if name.startswith(s[:3].lower()):
                    stat_bonus[s]+=val
                    break
            else:
                # skill
                skill_bonus[name] = skill_bonus.get(name,0)+val

    return stat_bonus, skill_bonus, percent_bonus

# ---------- HOME ----------
@app.route("/")
def index():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT * FROM characters")
    chars=c.fetchall()
    conn.close()
    return render_template("index.html",chars=chars)

# ---------- CREATE ----------
@app.route("/create",methods=["POST"])
def create():
    cid=str(uuid.uuid4())
    name=request.form.get("name","Crawler")

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("INSERT INTO characters VALUES (?,?)",(cid,name))

    for s in STATS:
        c.execute("INSERT INTO stats VALUES (?,?,?,?,?)",(cid,s,10,0,0))

    c.execute("INSERT INTO meta VALUES (?,?,?,?,?,?,?,?,?,?)",
              (cid,1,100,100,0,0,0,"","",""))

    conn.commit()
    conn.close()

    return redirect(f"/c/{cid}")

# ---------- CHARACTER ----------
@app.route("/c/<cid>",methods=["GET","POST"])
def char(cid):
    conn=sqlite3.connect(DB)
    c=conn.cursor()

    if request.method=="POST":
        # stats
        for s in STATS:
            base=int(request.form.get(f"base_{s}",10))
            buff=int(request.form.get(f"buff_{s}",0))
            c.execute("UPDATE stats SET base=?,buff=? WHERE char_id=? AND stat=?",
                      (base,buff,cid,s))

        equip_text=request.form.get("equipment","")
        stats_b, skills_b, perc_b = parse(equip_text)

        for s in STATS:
            c.execute("UPDATE stats SET equip=? WHERE char_id=? AND stat=?",
                      (stats_b[s],cid,s))

        # skills
        c.execute("DELETE FROM skills WHERE char_id=?",(cid,))
        names=request.form.getlist("skill_name")
        vals=request.form.getlist("skill_val")

        for n,v in zip(names,vals):
            if n:
                base=int(v)
                equip=skills_b.get(n.lower(),0)
                c.execute("INSERT INTO skills VALUES (?,?,?,?)",
                          (cid,n,base,equip))

        # percentages
        c.execute("DELETE FROM percentages WHERE char_id=?",(cid,))
        for k,v in perc_b.items():
            c.execute("INSERT INTO percentages VALUES (?,?,?)",(cid,k,v))

        # meta
        c.execute("""
        UPDATE meta SET level=?,hp=?,max_hp=?,views=?,followers=?,favorites=?,
        equipment=?,spells=?,inventory=?
        WHERE char_id=?
        """,(
            request.form["level"],
            request.form["hp"],
            request.form["max_hp"],
            request.form["views"],
            request.form["followers"],
            request.form["favorites"],
            equip_text,
            request.form["spells"],
            request.form["inventory"],
            cid
        ))

        conn.commit()

    # LOAD
    c.execute("SELECT stat,base,buff,equip FROM stats WHERE char_id=?",(cid,))
    rows=c.fetchall()
    stats={}
    for s,b,bu,e in rows:
        total=b+bu+e
        stats[s]={"base":b,"buff":bu,"equip":e,"total":total,"mod":mod(total)}

    c.execute("SELECT * FROM meta WHERE char_id=?",(cid,))
    meta=c.fetchone()

    c.execute("SELECT name,base,equip FROM skills WHERE char_id=?",(cid,))
    skills=c.fetchall()

    c.execute("SELECT name,value FROM percentages WHERE char_id=?",(cid,))
    percs=c.fetchall()

    conn.close()

    return render_template("character.html",
        cid=cid,stats=stats,meta=meta,
        skills=skills,percs=percs)

init_db()

if __name__=="__main__":
    app.run()
