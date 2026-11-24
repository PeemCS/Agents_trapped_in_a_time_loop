"use strict";
(() => {
  const $=id=>document.getElementById(id),film=$("film"),choices=$("chooser"),select=$("shot"),data=window.SCREENINGS;
  const labels={inn:"Hearthside Hotel",Pittsburgh:"Pittsburgh terminal",square:"town square",diner:"diner",depot:"coach depot",studio:"radio studio"};
  const friendly=s=>s.replaceAll("_"," ");
  let current=0,shown=-1;
  function render(){
    const src=data[current], t=film.currentTime||0,idx=Math.max(0,src.shots.findLastIndex(s=>s.at<=t+.015));
    if(idx===shown)return;
    const s=src.shots[idx];shown=idx;select.value=String(idx);
    $("moment").textContent="Tuesday "+s.day+" · "+s.clock;$("focus").textContent=s.focus;
    $("fact").textContent=s.view==="unspoken"?"Qwen emitted this private note before committing the action.":s.view==="morning"?"The previous evening ends. The recorded next morning begins at the hotel.":s.effect;
    $("quote").textContent=s.note?"“"+s.note+"”":s.speech.map(line=>line.actor+" · “"+line.text+"”").join(" ");
    $("others").replaceChildren(...s.others.map(o=>{const div=document.createElement("div");div.textContent=o.actor+" · "+friendly(o.action);return div;}));
    $("event").textContent=s.id;
    const link=$("source-thinking");
    link.hidden=!s.thinkingSlot;
    if(s.thinkingSlot)link.href="../thinking/index.html#"+s.thinkingSlot;
  }
  function load(i){
    current=i;shown=-1;const src=data[i];
    film.pause();const companion=$("companion");companion.href=src.companion||"../editor/two-takes-demo.mp4";companion.textContent=src.companionLabel||"Compare the original takes ↗";film.src=src.film;film.poster=src.poster;film.load();
    select.replaceChildren(...src.shots.map((s,j)=>{const o=document.createElement("option");o.value=String(j);o.textContent=Math.floor(s.at/60)+":"+String(Math.floor(s.at%60)).padStart(2,"0")+" · "+s.focus+" · "+(labels[s.view==="morning"?s.origin:s.place]||s.place);return o;}));
    choices.querySelectorAll("button").forEach((b,n)=>b.setAttribute("aria-pressed",String(i===n)));
    $("film-label").textContent=src.model+" · take "+src.seed+" · single recorded world";render();
  }
  for(const [i,s] of data.entries()){const b=document.createElement("button");b.type="button";b.textContent=s.title;b.onclick=()=>{history.replaceState(null,"","#"+s.id);load(i);};choices.append(b);}
  select.onchange=()=>{film.currentTime=data[current].shots[Number(select.value)].at+.025;};
  film.addEventListener("timeupdate",render);film.addEventListener("seeked",render);film.addEventListener("loadedmetadata",render);
  const start=()=>load(Math.max(0,data.findIndex(s=>s.id===location.hash.slice(1))));
  addEventListener("hashchange",start);start();
})();
