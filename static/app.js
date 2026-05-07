const cid = window.location.pathname.split("/").pop();

function collectData(){

    let data = {};

    document.querySelectorAll(
        "input, textarea"
    ).forEach(el=>{

        if(el.name){
            data[el.name] = el.value;
        }

    });

    return data;
}

async function autosave(){

    await fetch(`/autosave/${cid}`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify(
            collectData()
        )
    });

}

document.addEventListener("input",()=>{

    clearTimeout(window.saveTimer);

    window.saveTimer = setTimeout(()=>{
        autosave();
    },400);

});
