const cid = window.location.pathname.split("/").pop();

function collectData(){

    let data = {
        effects:[]
    };

    document.querySelectorAll("input, textarea").forEach(el=>{

        if(el.name){
            data[el.name] = el.value;
        }

    });

    document.querySelectorAll(".effect").forEach(e=>{

        data.effects.push({
            name:e.querySelector(".ename").value,
            value:parseInt(e.querySelector(".eval").value)||0,
            duration:parseInt(e.querySelector(".edur").value)||0,
            duration_type:e.querySelector(".etype").value,
            is_buff:e.querySelector(".ebuff").checked ? 1 : 0
        });

    });

    return data;
}

async function autosave(){

    const res = await fetch(`/autosave/${cid}`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify(collectData())
    });

    if(res.ok){

        document.getElementById("liveSave").style.opacity = 1;

        loadLiveData();

        setTimeout(()=>{
            document.getElementById("liveSave").style.opacity = 0;
        },1000);
    }
}

async function loadLiveData(){

    location.reload();
}

document.addEventListener("input",()=>{

    clearTimeout(window.saveTimer);

    window.saveTimer = setTimeout(()=>{
        autosave();
    },400);

});
