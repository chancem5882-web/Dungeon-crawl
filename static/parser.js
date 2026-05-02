function clean(n){return n.toLowerCase().replace("skill","").trim();}

function parse(text){
let stat={},skill={},perc={};

let patterns=[
/([a-zA-Z ]+)\s*([+-]?\d+)%/g,
/([+-]?\d+)%\s*([a-zA-Z ]+)/g,
/([a-zA-Z ]+)\s*([+-]?\d+)/g,
/([+-]?\d+)\s*([a-zA-Z ]+)/g
];

patterns.forEach(p=>{
let m;
while((m=p.exec(text))!==null){
let a=m[1],b=m[2];

if(p.toString().includes("%")){
let val=parseInt(b);
let name=clean(a);
perc[name]=(perc[name]||0)+val;
}else{
let val,name;

if(!isNaN(a)){val=parseInt(a);name=clean(b);}
else{val=parseInt(b);name=clean(a);}

let stats=["strength","dexterity","constitution","intelligence","charisma"];
let found=false;

stats.forEach(s=>{
if(name.startsWith(s.slice(0,3))){
stat[s]=(stat[s]||0)+val;
found=true;
}});

if(!found) skill[name]=(skill[name]||0)+val;
}
}
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
