(() => {
  "use strict";
  const $=id=>document.getElementById(id),W=WinterMap,art=WinterArt,pack=FreeWalkTakes,runs=[...pack.runs,...(window.CoordinatedTakes||[])];
  const label={free:"Public door map",doors:"Doors-only control",unmarked:"Unmarked door map",obstruction:"Blocked-pin calibration",coordinated:"Live reservations"};
  const skin={reporter:"Phil",producer:"Lou",camera:"Bea"},inkt={reporter:"#b96736",producer:"#426c96",camera:"#537353"};
  const f=n=>Number(n).toFixed(1),xy=p=>"("+f(p.x)+", "+f(p.y)+")",clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  let selected=0,slot=0,progress=0,role="reporter",wide=true,reserved=false,playing=false,last=0,signature="";
  let sampled=[],transform=null;const cv=$("town"),mark=$("marks"),ctx=mark.getContext("2d");
  function option(v,t){const o=document.createElement("option");o.value=String(v);o.textContent=t;return o;}
  for(const [i,r] of runs.entries())$("run").append(option(i,label[r.condition]+" · "+r.seed));
  function current(){return runs[selected];}
  function timed(){return reserved||current().condition==="coordinated";}
  function rowsForTurn(){
    const take=current(),raw=take.ticks[slot];if(!reserved)return raw;
    const overlay=FreeWalkReservations.runs[take.condition+"-"+take.seed][slot];
    return raw.map((e,i)=>({...e,...overlay[i]}));
  }
  function event(){const rows=rowsForTurn();return rows.find(e=>e.role===role)||rows[0];}
  function traveled(e,sharedDistance){
    if(!timed())return Math.min(e.length,sharedDistance);
    if(e.to<=e.from)return e.length;
    return clamp((progress-e.from)/(e.to-e.from),0,1)*e.length;
  }
  function select(i){
    if(!Number.isInteger(i)||i<0||i>=runs.length)throw new RangeError("Unknown take");
    selected=i;slot=0;progress=0;playing=false;signature="";
    $("policy").disabled=current().condition==="coordinated";if($("policy").disabled){reserved=false;$("policy").value="original";}
    const cast=current().ticks[0];if(!cast.some(e=>e.role===role))role=cast[0].role;
    $("run").value=String(i);$("actor").replaceChildren(...cast.map(e=>option(e.role,e.actor)));$("actor").value=role;
    $("time").max=String(current().ticks.length);render();return getState();
  }
  function seek(i,p=0){if(!Number.isInteger(i)||i<0||i>=current().ticks.length||!Number.isFinite(p))throw new RangeError("Unknown movement");
    slot=i;progress=clamp(p,0,1);playing=false;render();return getState();}
  function screen(p){const d=W.iso(p);return {x:transform.ox+d.x*transform.z,y:transform.oy+d.y*transform.z};}
  function line(path,color,dash,width){
    if(path.length<2)return;ctx.beginPath();let pen=false;
    for(let i=1;i<path.length;i++){
      const a=path[i-1],b=path[i],n=Math.max(1,Math.ceil(W.distance(a,b)/.17));
      for(let j=0;j<=n;j++){const p=W.mix(a,b,j/n);if(art.landmarkAt(W.iso(p),"town")){pen=false;continue;}
        const q=screen(p);if(pen)ctx.lineTo(q.x,q.y);else ctx.moveTo(q.x,q.y);pen=true;}
    }
    ctx.lineWidth=width;ctx.strokeStyle=color;ctx.setLineDash(dash);ctx.stroke();ctx.setLineDash([]);
  }
  function progressPath(e,walked){
    const out=[e.path[0]];let rest=walked;
    for(let i=1;i<e.path.length;i++){const length=W.distance(e.path[i-1],e.path[i]);if(rest<length){out.push(W.mix(e.path[i-1],e.path[i],length?rest/length:1));break;}
      out.push(e.path[i]);rest-=length;}
    return out;
  }
  function render(){
    const r=current(),rows=rowsForTurn(),e=event(),w=cv.clientWidth,h=cv.clientHeight,dpr=Math.min(window.devicePixelRatio||1,2);
    for(const el of [cv,mark])if(el.width!==Math.round(w*dpr)||el.height!==Math.round(h*dpr)){el.width=Math.round(w*dpr);el.height=Math.round(h*dpr);}
    const max=Math.max(.05,...rows.map(e=>e.length)),distance=progress*max;
    sampled=rows.map(v=>{const walked=traveled(v,distance),p=W.sample(v.path,v.length?walked/v.length:1);return {name:v.actor,role:v.role,skin:skin[v.role],scene:"town",pos:p,main:v.role===role,moving:v.length>.01&&walked<v.length&&(!timed()||progress>=v.from)};});
    const subject=sampled.find(v=>v.role===role)||sampled[0];
    const zoom=wide?Math.min(w/1510,h/800):clamp(Math.min(w/480,h/340),.78,1.70);
    transform=art.draw(cv,{scene:"town",slot:1,t:slot*4+progress*4,people:sampled},{width:w,height:h,dpr,overview:wide,focus:wide?{x:10.8,y:10.0}:subject.pos,zoom});
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    for(const row of rows){const active=row.role===role;ctx.globalAlpha=active?.85:.35;
      line(progressPath(row,traveled(row,distance)),inkt[row.role],active?[]:[3,5],active?2.7:1.8);}
    ctx.globalAlpha=.75;line(e.path,"#754f24",[2,5],1.4);ctx.globalAlpha=1;
    const target=screen(e.requested),end=screen(e.resolved);ctx.beginPath();ctx.moveTo(target.x-5,target.y-5);ctx.lineTo(target.x+5,target.y+5);ctx.moveTo(target.x-5,target.y+5);ctx.lineTo(target.x+5,target.y-5);ctx.strokeStyle="#973e2b";ctx.lineWidth=2.3;ctx.stroke();
    ctx.beginPath();ctx.ellipse(end.x,end.y,8,4,0,0,Math.PI*2);ctx.lineWidth=2.1;ctx.strokeStyle="#946b26";ctx.stroke();
    const key=[selected,slot,role,reserved].join("/");if(signature!==key){signature=key;
      $("slot").textContent="Walk "+(slot+1)+" / "+r.ticks.length;$("title").textContent=e.actor+"’s destination";
      $("provenance").textContent=reserved?"Counterfactual reservation · Original model targets":current().condition==="coordinated"?"Live model · Reserved positions fed back":"Recorded coordinate decisions";
      $("result").textContent=e.reason+(e.length<.01?" "+e.actor+" stays in place.":"");
      $("quote").textContent=e.say?"“"+e.say+"”":"";
      $("asked").textContent="Requested "+xy(e.requested);$("grid").textContent="Grid "+xy(e.quantized);$("ended").textContent="Resolved "+xy(e.resolved);
      $("distance").textContent=f(e.length)+" m walked";$("receipt").href=e.raw;$("receipt").title=e.id+" · "+e.raw_sha256;
    }
    $("wide").setAttribute("aria-pressed",String(wide));$("follow").setAttribute("aria-pressed",String(!wide));$("time").value=String(slot+progress);
    $("play").textContent=playing?"Pause":"Play";$("back").disabled=!slot;$("next").disabled=slot+1>=r.ticks.length;
  }
  function play(){if(slot===current().ticks.length-1&&progress>=1){slot=0;progress=0;}playing=!playing;render();}
  function getState(){return {source:reserved?"counterfactual_reserved_routes":"local_ollama_coordinate_pilot",condition:current().condition,seed:current().seed,model:pack.model,role,slot,progress,playing,wide,
    eventId:event().id,requested:event().requested,resolved:event().resolved,positions:Object.fromEntries(sampled.map(v=>[v.name,{x:v.pos.x,y:v.pos.y}])),raw:event().raw};}
  function tick(ts){const dt=last?Math.min(.18,(ts-last)/1000):0;last=ts;
    if(playing){progress+=dt/4;if(progress>=1){if(slot+1===current().ticks.length){progress=1;playing=false;}else{slot++;progress-=1;}}render();}
    requestAnimationFrame(tick);}
  $("policy").onchange=e=>{reserved=e.target.value==="reserved";render();};$("run").onchange=e=>select(Number(e.target.value));$("actor").onchange=e=>{role=e.target.value;render();};
  $("wide").onclick=()=>{wide=true;render();};$("follow").onclick=()=>{wide=false;render();};
  $("play").onclick=play;$("back").onclick=()=>seek(slot-1);$("next").onclick=()=>seek(slot+1);
  $("time").oninput=e=>{const n=Number(e.target.value),i=Math.min(current().ticks.length-1,Math.floor(n));seek(i,n-i);};
  new ResizeObserver(render).observe($("stage"));const params=new URLSearchParams(location.search);
  const choice=runs.findIndex(r=>r.condition===params.get("condition")&&r.seed===Number(params.get("seed")));select(Math.max(0,choice));if(params.get("policy")==="reserved"&&current().condition!=="coordinated"){$("policy").value="reserved";reserved=true;render();}
  window.FreeWalkPilot={getState,select,seek,renderNow:render};requestAnimationFrame(tick);
})();
