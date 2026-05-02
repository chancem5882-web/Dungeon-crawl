function clean(n){return (n||"").toLowerCase().replace("skill","").trim();}

function parse(text){
let stat={},skill={},perc={};

text.split("\n").forEach(line=>{
line=line.toLowerCase().trim();
if(!line)return;

try{
let m=line.match(/([+-]?\d+)\s*%\s*(.*)|(.*)\s*([+-]?\d+)\s*%/);
if(m){
let val=parseInt(m[1]||m[4]);
let name=clean(m[2]||m[3]);
if(!isNaN(val)&&name)perc[name]=(perc[name]||0)+val;
}

line=line.replace(/([+-]?\d+\s*%\s*[a-zA-Z ]+)|([a-zA-Z ]+\s*[+-]?\d+\s*%)/g,'');

let n=line.match(/([+-]?\d+)\s*(.*)|(.*)\s*([+-]?\d+)/);
if(n){
let val=parseInt(n[1]||n[4]);
let name=clean(n[2]||n[3]);
if(isNaN(val)||!name)return;

let stats=["strength","dexterity","constitution","intelligence","charisma"];
let found=false;

stats.forEach(s=>{
if(name.startsWith(s.slice(0,3))){
stat[s]=(stat[s]||0)+val;
found=true;
}});

if(!found)skill[name]=(skill[name]||0)+val;
}
}catch(e){}
});

return {stat,skill,perc};
}

function render(){
let t=document.getElementById("equip").value;
let d=parse(t);

let h="<div class='preview-stats'><b>Stats</b><br>";
for(let k in d.stat)h+=k+": "+d.stat[k]+"<br>";

h+="</div><div class='preview-skills'><b>Skills</b><br>";
for(let k in d.skill)h+=k+": "+d.skill[k]+"<br>";

h+="</div><div class='preview-perc'><b>Percent</b><br>";
for(let k in d.perc)h+=k+": "+d.perc[k]+"%<br>";

h+="</div>";

document.getElementById("preview").innerHTML=h;
}

document.getElementById("equip").addEventListener("input",render);
render();
