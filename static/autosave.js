let timer;

function collect(){
return {
level:document.querySelector("[name=level]").value,
hp:document.querySelector("[name=hp]").value,
max_hp:document.querySelector("[name=max_hp]").value,
gold:document.querySelector("[name=gold]").value,
views:document.querySelector("[name=views]").value,
followers:document.querySelector("[name=followers]").value,
favorites:document.querySelector("[name=favorites]").value,
equipment:document.querySelector("[name=equipment]").value,
spells:document.querySelector("[name=spells]").value,
inventory:document.querySelector("[name=inventory]").value
};
}

function autosave(cid){
clearTimeout(timer);
timer=setTimeout(()=>{
fetch(`/autosave/${cid}`,{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(collect())
});
},500);
}

document.querySelectorAll("input,textarea").forEach(el=>{
el.addEventListener("input",()=>autosave(window.CID));
});
