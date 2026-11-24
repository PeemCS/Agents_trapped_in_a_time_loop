"use strict";
(() => {
  const $=id=>document.getElementById(id), clocks=["6:00 am","9:30 am","1:00 pm","7:00 pm"];
  let ix=window.THINKING_ARCHIVE||{slots:[],refs:{},streams:{}},selected=null,stream=null,live=false,isBusy=false;
  let wanted=decodeURIComponent(location.hash.slice(1));
  let listKey="",attemptKey="",lockId=0;
  const label=(s)=>s.actor+" · "+(s.short|| (s.persona==="wake branch"?"wake branch":"D"+s.day+" "+clocks[s.tick]+" · "+s.persona));
  let optionKey="",searchKey="",searchMatches=null,searchVersion=0,searchTimer=null,lastSearchAt=0;
  function matchingStream(slot){
    return searchMatches&&slot.requests.find(r=>Object.hasOwn(searchMatches,r));
  }
  async function updateSearch(){
    lastSearchAt=performance.now();
    const version=++searchVersion, query=$("query").value.trim().toLowerCase(),field=$("field").value;
    if(query.length<2){
      searchMatches=null;searchKey="";$("hits").textContent="";
    }else{
      let found={};
      if(live){
        const u=new URLSearchParams({q:query,field});
        try{const response=await fetch("/api/search?"+u,{cache:"no-store"});if(!response.ok)return;found=await response.json();}catch(_){return;}
      }else{
        const recordings=window.THINKING_ARCHIVE?.streams||{};
        for(const [rid,recording] of Object.entries(recordings)){
          const text=recording[field]||"", offset=text.toLowerCase().indexOf(query);
          if(offset>=0)found[rid]=text.slice(Math.max(0,offset-32),offset+query.length+65).replace(/\s+/g," ");
        }
      }
      if(version!==searchVersion)return;
      searchMatches=found;searchKey=field+":"+query+":"+Object.keys(found).length;
      const chosen=ix.slots.find(item=>item.id===selected);
      if(chosen&&!Object.hasOwn(found,stream)){stream=matchingStream(chosen)||null;attemptKey="";}
    }
    renderIndex();await readCurrent();
  }
  function renderIndex(){
    const available=Array.from(new Set(ix.slots.map(s=>s.persona)));
    const menuKey=available.join("|");
    if(menuKey!==optionKey){
      const version=$("version"),previous=version.value;
      version.replaceChildren(...["",...available].map(n=>{const o=document.createElement("option");o.value=n;o.textContent=n||"All takes";return o;}));
      if(available.includes(previous))version.value=previous;optionKey=menuKey;
    }
    if(wanted&&ix.slots.some(s=>s.id===wanted)){selected=wanted;wanted="";stream=null;attemptKey="";$("query").value="";searchMatches=null;searchKey="";$("hits").textContent="";$("cast").value="";$("version").value="";}
    const list=ix.slots.filter(s=>(!$("cast").value||s.role===$("cast").value)&&(!$("version").value||s.persona===$("version").value)&&(!searchMatches||matchingStream(s)));
    if(searchMatches)$("hits").textContent=list.length+" matching decisions";
    if(!list.some(s=>s.id===selected)){selected=list[0]?.id||null;stream=null;attemptKey="";}
    const key=list.map(s=>s.id+"-"+s.stage+"-"+s.requests.length).join("|")+"::"+selected+"::"+searchKey;
    if(key!==listKey){
      $("slots").replaceChildren(...list.map(s=>{const b=document.createElement("button");b.type="button";b.textContent=label(s);const match=matchingStream(s);
        if(match){const snippet=document.createElement("small");snippet.textContent=searchMatches[match];b.append(snippet);}
        b.setAttribute("aria-pressed",String(s.id===selected));b.onclick=()=>{selected=s.id;history.replaceState(null,"","#"+s.id);stream=matchingStream(s)||null;attemptKey="";renderIndex();readCurrent();};return b;}));listKey=key;
    }
    const s=ix.slots.find(o=>o.id===selected);
    if(!s){$("raw").hidden=true;$("permalink").hidden=true;$("who").textContent="No decisions in this selection";for(const id of ["thought","line","action","effect","metadata","source-id","input","json","status","time"])$(id).textContent="";return;}
    $("raw").hidden=false;$("permalink").hidden=false;$("permalink").href="#"+s.id;
    $("time").textContent=(s.when||("Tuesday "+s.day+" · "+clocks[s.tick]))+" · "+s.persona;$("who").textContent=s.actor;$("status").textContent=s.stage;
    $("action").textContent=s.action?s.action.action.replaceAll("_"," "):"Awaiting the committed action";
    $("line").textContent=s.action?.words?"“"+s.action.words+"”":"";
    $("effect").textContent=s.consequence||"";
    $("source-id").textContent=s.event_id+(s.original_slot?" · source "+s.original_slot:"");
    const ak=s.id+"::"+s.requests.join("|");
    if(ak!==attemptKey){
      $("attempt").replaceChildren(...s.requests.map((v,i)=>{const o=document.createElement("option");o.value=v;o.textContent="Attempt "+(i+1);return o;}));
      stream=s.requests.includes(stream)?stream:(matchingStream(s)||s.requests.at(-1));$("attempt").value=stream||"";$("attempt").disabled=s.requests.length<2;attemptKey=ak;
    }
    $("mode").textContent=(live?"Live monitor":"Offline archive")+" · "+ix.slots.length+" actor decisions / branches";
  }
  async function readCurrent(){
    const rid=stream,seq=++lockId;
    const pre=$("thought");
    if(pre.dataset.rid!==rid){
      for(const id of ["thought","input","json","metadata"])$(id).textContent="";
      $("raw").removeAttribute("href");
      $("raw").hidden=true;
    }
    if(!rid)return;
    let o;
    try{o=live?await (await fetch("/api/stream?id="+encodeURIComponent(rid),{cache:"no-store"})).json():ix.streams?.[rid];}
    catch(_){return;}
    if(seq!==lockId||rid!==stream||!o)return;
    const nearEnd=pre.scrollHeight-pre.scrollTop-pre.clientHeight<36,changed=pre.dataset.rid!==rid;
    if(pre.textContent!==o.thinking||changed){pre.textContent=o.thinking||(o.stop?(o.input?.think===false?"Thinking mode was off for this draw.":"The model returned an empty thinking field."):"Waiting for the model’s first thinking token…");pre.dataset.rid=rid;if(changed)pre.scrollTop=0;else if(live&&nearEnd&&o.stop==null)pre.scrollTop=pre.scrollHeight;}
    $("json").textContent=o.content||"";$("input").textContent=JSON.stringify(o.input,null,2);
    const f=ix.refs[rid];$("raw").href=(live&&f.url)||f.file;$("raw").hidden=false;
    $("metadata").textContent=[o.thinking.length+" characters",o.tokens!=null?o.tokens+" generated tokens":null,o.wall!=null?Number(o.wall).toFixed(1)+" s":null,o.stop?"stop: "+o.stop:"stream open",o.error].filter(Boolean).join(" · ");
  }
  $("query").oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(updateSearch,160);};
  $("field").onchange=updateSearch;
  $("attempt").onchange=e=>{stream=e.target.value;readCurrent();};for(const id of ["cast","version"])$(id).onchange=()=>{renderIndex();readCurrent();};
  async function refresh(){
    if(isBusy)return;isBusy=true;
    try{
      if(location.protocol==="http:"||location.protocol==="https:"){
        try{const r=await fetch("/api/index",{cache:"no-store"});if(r.ok&&r.headers.get("content-type")?.includes("application/json")){const n=await r.json();if(n.slots&&n.refs){ix=n;live=true;}}}catch(_){}
      }
      if($("query").value.trim().length>1&&(!searchKey||performance.now()-lastSearchAt>6500))await updateSearch();
      renderIndex();if(live)$("weights-link").href="/persona/viewer.html";await readCurrent();
    }finally{isBusy=false;if(live)setTimeout(refresh,1100);}
  }
  addEventListener("hashchange",()=>{wanted=decodeURIComponent(location.hash.slice(1));renderIndex();readCurrent();});
  $("query").value=new URLSearchParams(location.search).get("q")?.slice(0,100)||"";
  renderIndex();refresh();
})();
