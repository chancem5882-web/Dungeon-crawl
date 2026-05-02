function clean(n){
    return (n||"").toLowerCase().replace("skill","").trim();
}

function safeInt(v){
    let n=parseInt(v);
    return isNaN(n)?null:n;
}

function parse(text){
    let stat={},skill={},perc={};

    let lines=text.split("\n");

    lines.forEach(line=>{
        line=line.toLowerCase().trim();
        if(!line) return;

        try{
            let percentPatterns=[
                /([+-]?\d+)\s*%\s*([a-zA-Z ]+)/g,
                /([a-zA-Z ]+)\s*[:\-]?\s*([+-]?\d+)\s*%/g
            ];

            percentPatterns.forEach(p=>{
                let m;
                while((m=p.exec(line))!==null){
                    let a=m[1],b=m[2];

                    let val,name;

                    if(!isNaN(a)){val=safeInt(a);name=clean(b);}
                    else{val=safeInt(b);name=clean(a);}

                    if(val===null||!name) return;

                    perc[name]=(perc[name]||0)+val;
                }
            });

            line=line.replace(/([+-]?\d+\s*%\s*[a-zA-Z ]+)|([a-zA-Z ]+\s*[+-]?\d+\s*%)/g,'');

            let patterns=[
                /([+-]?\d+)\s*([a-zA-Z ]+)/g,
                /([a-zA-Z ]+)\s*[:\-]?\s*([+-]?\d+)/g
            ];

            patterns.forEach(p=>{
                let m;
                while((m=p.exec(line))!==null){
                    let a=m[1],b=m[2];

                    let val,name;

                    if(!isNaN(a)){val=safeInt(a);name=clean(b);}
                    else{val=safeInt(b);name=clean(a);}

                    if(val===null||!name) return;

                    let statsList=["strength","dexterity","constitution","intelligence","charisma"];
                    let found=false;

                    statsList.forEach(s=>{
                        if(name.startsWith(s.slice(0,3))){
                            stat[s]=(stat[s]||0)+val;
                            found=true;
                        }
                    });

                    if(!found){
                        skill[name]=(skill[name]||0)+val;
                    }
                }
            });

        }catch(e){}
    });

    return {stat,skill,perc};
}

function render(){
    let t=document.getElementById("equip").value;
    let d=parse(t);

    let h="<b style='color:#4da6ff'>Stats</b><br>";
    for(let k in d.stat) h+=k+": +"+d.stat[k]+"<br>";

    h+="<b style='color:#4dff88'>Skills</b><br>";
    for(let k in d.skill) h+=k+": +"+d.skill[k]+"<br>";

    h+="<b style='color:#c94dff'>Percent</b><br>";
    for(let k in d.perc) h+=k+": "+d.perc[k]+"%<br>";

    document.getElementById("preview").innerHTML=h;
}

document.getElementById("equip").addEventListener("input",render);
render();
