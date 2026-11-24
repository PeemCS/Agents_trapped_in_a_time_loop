"use strict";
(() => {
  const $ = id => document.getElementById(id), W=window.WinterMap,R=window.WinterReplay;
  const shots=window.TOWN_TRACES.map(R.normalize),defaultTake=Math.max(0,shots.findIndex(s=>s.header==="Phil"));
  const setOffset=key=>window.TUESDAY_STAGE.sets[key].offset[0];
  const stage=$("scene"),canvas=$("view"),clockText=s=>s.toUpperCase(),two=n=>String(n).padStart(2,"0");
  const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
  let art=null,errorReason="";
  try{if(new URLSearchParams(location.search).get("renderer")==="fallback")throw Error("Fallback preview requested.");art=TownStageArt.build(canvas);}
  catch(e){errorReason=e.message||"WebGL unavailable.";}
  function fallback(reason){
    errorReason=reason;$("fallback").hidden=false;canvas.hidden=true;
    $("walk-dock").hidden=$("replay-dock").hidden=document.querySelector(".strip").hidden=true;
    document.querySelector(".scene-head").hidden=document.querySelector(".camera-controls").hidden=$("touch").hidden=true;
    window.TuesdayStage3D={getState:()=>({renderer:"fallback",reason:errorReason}),renderNow:()=>({renderer:"fallback"})};
  }
  if(!art){fallback(errorReason);return;}
  const T=window.THREE,keys=new Set(),assetTickets=new Map(),assetPending=new Set();
  let mode="walk",selected=defaultTake,trace=shots[selected],index=0,progress=0,playing=false,cameraActor="reporter";
  let cinematic=false,drawCaptions=true,dressed=true,cameraType="follow",yaw=.54,pitch=.215,zoom=1,frameState=null,lastUI="",lastMenu="",clock=0,old=performance.now();
  const manual={day:1,slot:0,scene:"town",pos:R.anchor("inn"),lastPlace:"inn",route:null,special:null,moving:false,
    marked:false,called:false,dishes:2,calendar:false,cast:[],feedback:"WASD to walk · drag to look"};
  const schedules=[["inn","square","studio","diner"],["square","studio","depot","diner"]];
  function residentDestinations(immediate){
    manual.cast=schedules.map((schedule,i)=>{
      const place=schedule[manual.slot],dest=R.anchor(place,i+1),prior=manual.cast[i];
      const start=immediate||!prior?dest:prior.pos,path=TownStagePlacement.route(start,dest,"town",dressed);
      return {name:i?"Larry":"Rita",role:i?"camera":"producer",pos:{...start},scene:"town",place,
        origin:immediate||!prior?place:prior.place,at:immediate||!prior?place:prior.at,
        moving:false,path,dist:W.pathLength(path),travel:0,visible:true,action:""};
    });
  }
  function awake(){
    manual.day++;manual.slot=0;manual.scene="town";manual.pos=R.anchor("inn");manual.lastPlace="inn";
    manual.route=null;manual.moving=false;manual.marked=false;manual.called=false;manual.dishes=2;
    residentDestinations(true);manual.feedback="6:00 AM. The hotel radio plays again.";lastUI="";
  }
  function advance(){
    if(mode!=="walk"||manual.special)return;
    if(manual.slot===3){manual.special={kind:"dawn",elapsed:0,duration:1.45,reset:false};manual.route=null;return;}
    manual.slot++;residentDestinations(false);manual.feedback="Time advances to "+clockText(R.clocks[manual.slot])+".";lastUI="";
  }
  function walkTo(id,point=null){
    if(mode!=="walk"||manual.special)return false;
    if(id&&(!W.places[id]||W.places[id].scene!==manual.scene))return false;
    const bounds=W.extent[manual.scene],p=point?{x:clamp(point.x,bounds.x1,bounds.x2),y:clamp(point.y,bounds.y1,bounds.y2)}:R.anchor(id);
    const way=TownStagePlacement.route(manual.pos,p,manual.scene,dressed),distance=W.pathLength(way);
    if(distance<.035)return false;
    manual.route={way,distance,travel:0,id};manual.feedback=id?"Walking to "+W.places[id].label+".":"Walking to the selected point.";
    lastUI="";return true;
  }
  function currentPlace(){
    const hit=W.nearestPlace(manual.pos,manual.scene);
    return hit.distance<1.35?hit.id:null;
  }
  function localAction(){
    const here=currentPlace();
    if(manual.special)return ["In transit","",true];
    if(here==="inn")return [manual.marked?"Read the calendar":"Mark the windowsill","hotel",false];
    if(here==="diner")return [manual.dishes>0?"Clear one dish rack":"Look at the counter","diner",false];
    if(here==="square")return ["Watch the bandstand","square",false];
    if(here==="studio")return ["File the forecast","studio",false];
    if(here==="depot")return manual.slot<2?["Wait for the 1 PM coach","wait",false]:manual.slot===2?["Board the coach","board",false]:["Read the timetable","timetable",false];
    if(here==="Pittsburgh")return manual.called?["Stay until morning","dawn",false]:["Use the payphone","call",false];
    return ["Walk to a landmark","",true];
  }
  function interact(){
    if(mode!=="walk"||manual.special)return;
    const [,action,disabled]=localAction();if(disabled)return;
    if(action==="wait"){while(manual.slot<2)advance();manual.feedback="The 1 PM coach has pulled in.";}
    else if(action==="board"){manual.route=null;manual.special={kind:"coach",elapsed:0,duration:6.9};manual.feedback="Phil boards the intercity coach.";}
    else if(action==="dawn"){manual.route=null;manual.special={kind:"dawn",elapsed:0,duration:1.45,reset:false};manual.feedback="Phil spends the evening in Pittsburgh.";}
    else if(action==="hotel"){manual.feedback=manual.marked?"February 2. The pencil cross is still on the sill.":"Phil leaves a pencil cross on the sill.";manual.marked=true;}
    else if(action==="call"){manual.called=true;manual.feedback="Phil makes a call from the Pittsburgh terminal.";}
    else if(action==="diner"){manual.dishes=Math.max(0,manual.dishes-1);manual.feedback=manual.dishes?"One dish rack remains.":"The racks are clear.";}
    else if(action==="square")manual.feedback="Phil watches the festival bandstand.";
    else if(action==="studio")manual.feedback="The station records Phil's forecast.";
    else if(action==="timetable")manual.feedback="The Pittsburgh coach departs at 1:00 PM.";
    lastUI="";
  }
  function moveManual(dt){
    if(manual.special){
      const s=manual.special;s.elapsed+=dt;const f=clamp(s.elapsed/s.duration,0,1);
      if(s.kind==="dawn"&&!s.reset&&f>.48){awake();s.reset=true;}
      if(f>=1){
        if(s.kind==="coach"){manual.scene="city";manual.pos=R.anchor("Pittsburgh");manual.lastPlace="Pittsburgh";manual.feedback="Phil steps onto the Pittsburgh platform.";}
        manual.special=null;lastUI="";
      }return;
    }
    for(const p of manual.cast){
      p.moving=p.travel<p.dist-.004;
      if(p.moving){p.travel=Math.min(p.dist,p.travel+1.8*dt);p.pos=W.sample(p.path,p.dist?p.travel/p.dist:1);p.at=p.travel>=p.dist?p.place:p.origin;}
    }
    const hor=Number(keys.has("right"))-Number(keys.has("left")),ver=Number(keys.has("up"))-Number(keys.has("down"));
    manual.moving=false;
    if(hor||ver){
      manual.route=null;
      const norm=Math.hypot(hor,ver),dx=(Math.cos(yaw)*hor-Math.sin(yaw)*ver)*dt*2.85/norm,dz=(-Math.sin(yaw)*hor-Math.cos(yaw)*ver)*dt*2.85/norm;
      const x=manual.pos.x,z=manual.pos.y;
      const candidates=[{x:x+dx,y:z+dz},{x:x+dx,y:z},{x,y:z+dz}];
      const p=candidates.find(v=>TownStagePlacement.walkable(v,manual.scene,dressed));
      if(p){manual.pos={...p,dx:p.x-x,dy:p.y-z};manual.moving=!!(Math.abs(p.x-x)+Math.abs(p.y-z));}
    }else if(manual.route){
      const a=manual.route;a.travel=Math.min(a.distance,a.travel+2.9*dt);manual.pos=W.sample(a.way,a.travel/a.distance);manual.moving=a.travel<a.distance;
      if(!manual.moving){manual.route=null;manual.feedback=a.id?"Phil reaches "+W.places[a.id].label+".":"Phil stops.";lastUI="";}
    }
    const here=currentPlace();if(here)manual.lastPlace=here;
  }
  function manualWorld(){
    let pos=manual.pos,scene=manual.scene,moving=manual.moving,hidden=false,transition=0,banner="",phase="free walk";
    let bus=scene==="city"?{scene,pos:R.cityRide.at(-1)}:manual.slot===2?{scene,pos:R.townRide[0]}:null;
    const s=manual.special;
    if(s){
      const f=clamp(s.elapsed/s.duration,0,1);
      if(s.kind==="coach"){
        const p=R.move({origin:"depot",place:"Pittsburgh"},.32+.68*f);
        pos=p.pos;scene=p.scene;moving=p.moving;hidden=p.hidden;phase=p.phase;bus=p.bus;
      }else{phase="dawn";transition=f<.48?f/.48:1-(f-.48)/.52;if(f>.52)banner="The alarm rings again.";}
    }
    const at=scene==="city"?"Pittsburgh":manual.lastPlace;
    return {scene,day:manual.day,clock:R.clocks[manual.slot],slot:manual.slot,transition,banner,phase,bus,t:clock,
      facts:{marked:manual.marked,called_sister:manual.called,dishes:manual.dishes},people:[{name:"Phil",role:"reporter",pos,scene,at,place:at,action:"",main:true,visible:!hidden,moving},...manual.cast]};
  }
  function setMode(next){
    mode=next;playing=false;keys.clear();cameraActor="reporter";lastUI="";lastMenu="";
    document.body.classList.toggle("replaying",next==="replay");
    $("walk").setAttribute("aria-pressed",String(next==="walk"));$("recorded").setAttribute("aria-pressed",String(next==="replay"));
    $("walk-dock").hidden=next!=="walk";$("replay-dock").hidden=next!=="replay";
    $("error").hidden=true;snap();
  }
  function makeOption(value,text){const o=document.createElement("option");o.value=String(value);o.textContent=text;return o;}
  function refreshRecordings(){
    $("take").replaceChildren(...shots.map((s,i)=>makeOption(i,(s.isFixture?"Fixture · ":"")+(s.label||s.header+" · "+(s.model||"imported run")))));$("take").append(makeOption("rialto-alt","Eight bars · Rialto 721-hypothesis ↗"));$("take").value=String(selected);
  }
  function selectTake(i){
    selected=i;trace=shots[i];index=0;progress=0;$("take").value=String(i);setMode("replay");
    $("timeline").max=String(trace.events.length);render();return getState();
  }
  function loadTrace(raw){
    const normalized=R.normalize(raw);shots.push(normalized);refreshRecordings();return selectTake(shots.length-1);
  }
  function seek(i,p=0){
    if(!Number.isInteger(i)||i<0||i>=trace.events.length||!Number.isFinite(p))throw new RangeError("Invalid decision or progress.");
    if(mode!=="replay")setMode("replay");index=i;progress=clamp(p,0,1);playing=false;lastUI="";snap();render();return getState();
  }
  function playback(){
    if(mode!=="replay")setMode("replay");
    if(index===trace.events.length-1&&progress>=1){index=0;progress=0;}
    playing=!playing;lastUI="";render();
  }
  let cameraTarget=null,eyeSmoothed=null,activeSet=null;
  function snap(){cameraTarget=null;eyeSmoothed=null;activeSet=null;}
  function setCamera(type){
    if(!["follow","orbit","aerial"].includes(type))throw new Error("Unknown camera angle.");
    cameraType=type;zoom=1;
    yaw=type==="follow"?.54:type==="orbit"?.88:.55;
    pitch=type==="follow"?.215:type==="orbit"?.49:1.01;
    for(const b of document.querySelectorAll("[data-camera]"))b.setAttribute("aria-pressed",String(b.dataset.camera===type));
    snap();render();return getState();
  }
  const aim=new T.Vector3(),eye=new T.Vector3(),dir=new T.Vector3(),ray=new T.Ray(),tmp=new T.Vector3();
  const probe=new T.Vector3();
  function unobstructed(look,angle,tilt,radius,key,subjectWidth=.0){
    const target=new T.Vector3(look.x+Math.sin(angle)*Math.cos(tilt)*radius,look.y+Math.sin(tilt)*radius,
      look.z+Math.cos(angle)*Math.cos(tilt)*radius);
    let clear=radius;
    const offsets=subjectWidth?[0,-subjectWidth,subjectWidth]:[0];
    for(const offset of offsets){
      probe.set(look.x+Math.cos(angle)*offset,look.y,look.z-Math.sin(angle)*offset);
      dir.subVectors(target,probe).normalize();ray.set(probe,dir);
      for(const box of art.occlusionBoxes[key]){
        const hit=ray.intersectBox(box,tmp);
        if(hit){const d=tmp.distanceTo(probe);if(d>.28&&d<clear)clear=Math.max(.82,d-.18);}
      }
    }
    return clear;
  }
  const lensPlan=new Map();
  function vehicleLens(p,radius){
    const route=p.scene==="city"?[R.cityRide[0],R.cityRide.at(-1)]:R.townRide;
    let bestDist=Infinity,which=0;
    for(let i=1;i<route.length;i++){
      const a=route[i-1],b=route[i],dx=b.x-a.x,dz=b.y-a.y,len2=dx*dx+dz*dz;
      const t=clamp(((p.pos.x-a.x)*dx+(p.pos.y-a.y)*dz)/len2,0,1);
      const d=Math.hypot(p.pos.x-a.x-t*dx,p.pos.y-a.y-t*dz);
      if(d<bestDist){bestDist=d;which=i-1;}
    }
    const key=[p.scene,which,dressed,yaw.toFixed(3),pitch.toFixed(3),radius.toFixed(2)].join("/");
    if(lensPlan.has(key))return lensPlan.get(key);
    const a=route[which],b=route[which+1],dx=b.x-a.x,dz=b.y-a.y,tangent=Math.atan2(dx,dz);
    const base=p.scene==="city"?-1:1,offset=setOffset(p.scene);
    const angles=[1.15,-1.15,1.67,-1.67,.79,-.79,2.14,-2.14];
    let best=-Infinity,result=null;
    // Select one lens for the entire straight leg. Checking all samples once
    // avoids oscillating between opposing camera angles as the coach passes trees.
    for(const [i,bearing] of angles.entries())for(const [j,rise] of [.15,.38,.62,.86].entries()){
      const angle=tangent+base*bearing+yaw-.54,tilt=clamp(pitch+rise,.20,1.34);
      let complete=0,hits=0;
      for(let n=0;n<9;n++){
        const f=(n+.17)/8.34,x=a.x+dx*f+offset,z=a.y+dz*f,cy=.47;
        eye.set(x+Math.sin(angle)*Math.cos(tilt)*radius,cy+Math.sin(tilt)*radius,z+Math.cos(angle)*Math.cos(tilt)*radius);
        let clear=0;
        for(const side of [-.70,0,.70]){
          probe.set(x+Math.sin(tangent)*side,cy+.16,z+Math.cos(tangent)*side);
          dir.subVectors(probe,eye);const length=dir.length();dir.normalize();ray.set(eye,dir);
          const blocked=art.occlusionBoxes[p.scene].some(box=>{
            if(box.containsPoint(eye))return true;
            const hit=ray.intersectBox(box,tmp);return hit&&tmp.distanceTo(eye)<length-.16;
          });
          if(!blocked)clear++;
        }
        hits+=clear;if(clear===3)complete++;
      }
      const score=complete*12+hits*2-i*.28-j*.8;
      if(score>best){best=score;result={angle,tilt};}
    }
    if(lensPlan.size>=64)lensPlan.delete(lensPlan.keys().next().value);
    lensPlan.set(key,result);return result;
  }
  function cameraView(p,dt=0){
    const off=setOffset(p.scene),aerial=cameraType==="aerial",orbit=cameraType==="orbit",compact=canvas.clientWidth<600;
    const riding=p.visible===false,phone=p.scene==="city"&&/^(call_sister|call_home|call_live_report)$/.test(p.action||"");
    const switcher=p.role==="producer"&&/^(patch_reporter_line|patch_camera_line|host_bulletin|play_filed_forecast)$/.test(p.action||"");
    const targetH=aerial?.25:riding?.47:phone||switcher?.84:.79;
    aim.set(p.pos.x+off,targetH,p.pos.y);
    if(aerial){aim.x=off+10.2+.20*(p.pos.x-10.2);aim.z=10+.20*(p.pos.y-10);}
    let angle=yaw,tilt=pitch;
    const radius=(aerial?(compact?27:20):orbit?8.3:riding?5.7:phone?3.65:switcher?3.9:compact?5.7:5.45)*zoom;
    if(!aerial&&!orbit&&switcher)angle+=.57;
    if(!aerial&&!orbit&&phone){angle+=.84;aim.x+=.09;aim.z-=.06;}
    if(!aerial&&!orbit&&riding){
      const lens=vehicleLens(p,radius);angle=lens.angle;tilt=lens.tilt;
    }
    // A tracking shot has to fit the whole vehicle. Select a clear angle above
    // rather than shrinking its camera distance when a spruce clips a corner.
    const safe=aerial||riding?radius:unobstructed(aim,angle,tilt,radius,p.scene);
    eye.set(aim.x+Math.sin(angle)*Math.cos(tilt)*safe,aim.y+Math.sin(tilt)*safe,aim.z+Math.cos(angle)*Math.cos(tilt)*safe);
    if(mode==="replay"||!eyeSmoothed||activeSet!==p.scene||dt===0){eyeSmoothed=eye.clone();cameraTarget=aim.clone();}
    else{const f=1-Math.exp(-dt*12);eyeSmoothed.lerp(eye,f);cameraTarget.lerp(aim,f);}
    activeSet=p.scene;
    return {eye:eyeSmoothed.toArray(),target:cameraTarget,targetHeight:targetH,fov:aerial?44:compact?49:40};
  }
  const labelNodes=[];
  function labels(w,subject){
    while(labelNodes.length<w.people.length){const e=document.createElement("div");e.className="subject-tag";$("names").append(e);labelNodes.push(e);}
    const placed=[];
    for(const [i,p] of w.people.entries()){
      const e=labelNodes[i],q=art.screen(p);
      e.hidden=p.scene!==subject.scene||p.visible===false||!q.visible||q.y<8||q.y>canvas.clientHeight-5;
      if(e.hidden)continue;
      let y=q.y;
      if(placed.some(o=>Math.abs(o.x-q.x)<51&&Math.abs(o.y-y)<19))y-=20;
      e.textContent=p.name;e.classList.toggle("main",p===subject);e.style.left=q.x+"px";e.style.top=y+"px";placed.push({x:q.x,y});
    }
    for(let i=w.people.length;i<labelNodes.length;i++)labelNodes[i].hidden=true;
  }
  function controls(w,subject){
    const inWalk=mode==="walk",place=inWalk?currentPlace():subject.at,act=inWalk?localAction():[];
    const event=w.shown,actorEvent=event&&(event.actor===subject.name?event:event.cast?.find(e=>e.actor===subject.name));
    const bulletin=w.facts?.bulletin?.channel||"";
    const boundAsset=art.assetFor(subject),loadingAsset=assetPending.has(art.identity(subject));
    const key=[mode,selected,index,bulletin,boundAsset?.name||"",loadingAsset,w.day,w.slot,w.phase,w.scene,subject.name,subject.at,playing,manual.feedback,act[0],w.banner,progress===1].join("|");
    if(key!==lastUI){
      lastUI=key;
      $("asset").disabled=loadingAsset;$("asset").textContent=loadingAsset?"Loading mesh…":boundAsset?"Reset mesh":"Actor GLB";
      $("asset").title=boundAsset?"Restore "+subject.name+"’s stage rig":"Replace "+subject.name+" with a local GLB";
      const townName=inWalk?"Mill Creek":trace.municipality;
      $("municipality").textContent=subject.scene==="city"?"Pittsburgh, PA":townName+(townName.includes(",")?"":", PA");
      $("world-clock").textContent="DAY "+two(w.day)+" · "+clockText(w.clock);
      if(inWalk){
        $("source-note").textContent="Direct control · Phil, reporter";
        $("location").textContent=manual.special?w.phase:place?W.places[place].label:"On foot";
        $("feedback").textContent=manual.feedback;$("interact").textContent=act[0];$("interact").disabled=act[2];
        $("advance").disabled=!!manual.special;$("advance").textContent=manual.slot===3?"Next morning":"Advance to "+clockText(R.clocks[manual.slot+1]);
        $("go").disabled=!!manual.special||manual.scene==="city";
      }else{
        $("source-note").textContent=(trace.isFixture?"Injected fixture":"Model decisions · "+(trace.model||"imported take"))+(trace.seed!=null?" · seed "+trace.seed:"");
        $("slot").textContent="Decision "+(index+1)+" of "+trace.events.length;
        $("action").textContent=actorEvent?actorEvent.action.replaceAll("_"," "):"Scheduled location";
        $("event-id").textContent=(actorEvent?.id||W.places[subject.at]?.label||"")+(bulletin?" · "+(TownStageDressing.channelNames[bulletin]||bulletin):"");
        $("play").textContent=playing?"Pause":"Play";$("play").setAttribute("aria-label",playing?"Pause recording":"Play recording");
      }
    }
    const menuKey=inWalk?"walk/"+manual.scene:"replay/"+selected+w.people.map(p=>p.name).join("/");
    if(lastMenu!==menuKey){
      lastMenu=menuKey;
      if(inWalk){$("dest").replaceChildren(...Object.entries(W.places).filter(([,v])=>v.scene===manual.scene).map(([id,v])=>makeOption(id,v.label)));$("dest").value=manual.scene==="city"?"Pittsburgh":"square";}
      else{$("cast").replaceChildren(...w.people.map(p=>makeOption(p.name,p.name+" · "+p.role)));$("cast").value=subject.name;}
    }
    if(!inWalk){$("timeline").value=String(index+progress);$("cast").value=subject.name;}
    const line=actorEvent?.words||actorEvent?.effect;
    $("subtitle").hidden=!drawCaptions||inWalk||!!w.banner||!!w.caption||!line;
    if(!$("subtitle").hidden){
      $("subtitle").firstElementChild.textContent=actorEvent.actor;
      $("subtitle").lastElementChild.textContent=actorEvent.words?"“"+line+"”":line;
    }
    $("fade").style.opacity=String(w.transition||0);$("alarm").hidden=!w.banner||!w.daybreak&&mode==="replay";
    if(!$("alarm").hidden)$("alarm").textContent=w.banner;
  }
  function render(dt=0){
    if(errorReason)return;
    const w=mode==="walk"?manualWorld():R.at(trace,index,progress);
    const subject=w.people.find(p=>p.role===cameraActor||p.name===cameraActor)||w.people[0];
    if(subject.bus)w.bus=subject.bus;
    const camera=cameraView(subject,dt),stats=art.render(w,subject,camera);
    labels(w,subject);controls(w,subject);
    const channel=w.facts?.bulletin?.channel,monitor=stats.switcherScreen;
    $("monitor").hidden=!channel||!monitor?.visible||subject.role!=="producer";
    if(!$("monitor").hidden){
      $("output-label").textContent="ON AIR · "+(TownStageDressing.channelNames[channel]||channel);
      $("monitor").style.left=clamp(monitor.x+5,5,stats.width-139)+"px";
      $("monitor").style.top=clamp(monitor.y,42,stats.height-33)+"px";
    }
    frameState={w,subject,camera,stats};
  }
  function getState(){
    if(!frameState)return {renderer:"starting"};
    const {w,subject,camera,stats}=frameState;
    return {renderer:"WebGL",mode,actor:w.people[0].name,subject:subject.name,scene:subject.scene,phase:w.phase,day:w.day,clock:w.clock,
      playing,index:mode==="replay"?index:null,progress:mode==="replay"?progress:null,total:mode==="replay"?trace.events.length:null,
      source:mode==="walk"?"manual":trace.source,municipality:mode==="walk"?"Mill Creek":trace.municipality,
      cinematic,dressed,camera:{type:cameraType,yaw,pitch,zoom,bearing:Math.atan2(camera.eye[0]-camera.target.x,camera.eye[2]-camera.target.z),fov:camera.fov,eye:camera.eye,target:camera.target.toArray()},stats,
      actualStageSHA256:window.TUESDAY_STAGE.usda_sha256,
      subjects:w.people.map(p=>({name:p.name,role:p.role,scene:p.scene,at:p.at,moving:!!p.moving,visible:p.visible!==false,
        x:p.pos.x+setOffset(p.scene),z:p.pos.y})),facts:w.facts||{},
      bus:w.bus?{scene:w.bus.scene,x:w.bus.pos.x+setOffset(w.bus.scene),z:w.bus.pos.y}:null,
      eventId:mode==="replay"?w.shown.id:null};
  }
  function loop(now){
    if(errorReason)return;
    if(now-old>=1000/32){
      const dt=clamp((now-old)/1000,0,.09);old=now;clock+=dt;
      if(mode==="walk")moveManual(dt);
      else if(playing){
        const e=trace.events[index];progress+=dt/(e.origin!=="Pittsburgh"&&e.place==="Pittsburgh"?6.9:4.5);
        if(progress>=1){if(index<trace.events.length-1){index++;progress=0;}else{progress=1;playing=false;lastUI="";}}
      }
      if(mode==="walk"||playing||frameState?.w.event?.id!==trace.events[index]?.id||!lastUI)render(dt);
    }
    requestAnimationFrame(loop);
  }
  $("walk").onclick=()=>{setMode("walk");render();};$("recorded").onclick=()=>selectTake(selected);
  $("take").onchange=e=>{
    if(e.target.value==="rialto-alt"){location.assign("rialto/index.html");return;}
    selectTake(Number(e.target.value));
  };
  $("cast").onchange=e=>{cameraActor=e.target.value;lastUI="";snap();render();};
  $("play").onclick=playback;$("timeline").oninput=e=>{const f=Number(e.target.value),i=Math.min(trace.events.length-1,Math.floor(f));seek(i,f-i);};
  $("go").onclick=()=>walkTo($("dest").value);$("interact").onclick=interact;$("advance").onclick=advance;
  for(const b of document.querySelectorAll("[data-camera]"))b.onclick=()=>setCamera(b.dataset.camera);
  function setCinematic(value,{captions=true}={}){
    cinematic=!!value;drawCaptions=!!captions;document.body.classList.toggle("cinematic",cinematic);
    snap();render();return getState();
  }
  function setDressing(value){dressed=!!value;art.setDressing(dressed);
    if(mode==="walk"&&!manual.special&&!TownStagePlacement.walkable(manual.pos,manual.scene,dressed)){
      manual.pos=TownStagePlacement.near(manual.pos,manual.scene,dressed);manual.route=null;
    }
    $("look").textContent=dressed?"Dressed set":"USD blocking";$("look").setAttribute("aria-pressed",String(dressed));render();return getState();}
  $("look").onclick=()=>setDressing(!dressed);
  function castTarget(actor){
    const p=actor?frameState.w.people.find(x=>x.role===actor||x.name===actor):frameState.subject;
    if(!p)throw new RangeError("That actor is absent from the current slot.");
    return {name:p.name,role:p.role};
  }
  async function replaceActor(file,{actor=null,height=1.30,yaw=0}={}){
    const p=castTarget(actor),key=art.identity(p),ticket=(assetTickets.get(key)||0)+1;
    assetTickets.set(key,ticket);assetPending.add(key);lastUI="";render();
    try{
      const asset=await TownStageAssets.parse(file,{height,yaw});
      if(assetTickets.get(key)!==ticket){asset.dispose();return getState();}
      art.bindAsset(p,asset);
    }finally{
      if(assetTickets.get(key)===ticket)assetPending.delete(key);
      lastUI="";render();
    }
    return getState();
  }
  function resetActor(actor=null){
    const p=castTarget(actor),key=art.identity(p);
    assetTickets.set(key,(assetTickets.get(key)||0)+1);assetPending.delete(key);art.bindAsset(p,null);$("error").hidden=true;lastUI="";render();return getState();
  }
  $("asset").onclick=()=>{if(art.assetFor(frameState.subject))resetActor();else $("asset-file").click();};
  $("asset-file").onchange=async e=>{
    const asset=e.target.files?.[0];e.target.value="";if(!asset)return;
    try{await replaceActor(asset);$("error").hidden=true;}
    catch(error){$("error").textContent=error.message||"The local mesh could not be opened.";$("error").hidden=false;}
  };
  $("open").onclick=()=>$("file").click();
  $("file").onchange=async e=>{
    const file=e.target.files?.[0];e.target.value="";if(!file)return;
    try{if(file.size>32*1024*1024)throw Error("Choose a recording smaller than 32 MiB.");loadTrace(JSON.parse(await file.text()));}
    catch(err){$("error").textContent=err.message;$("error").hidden=false;}
  };
  $("fullscreen").onclick=async()=>{
    try{if(document.fullscreenElement)await document.exitFullscreen();else await stage.requestFullscreen();}
    catch{stage.classList.toggle("full-view");}snap();render();
  };
  const keycodes={KeyW:"up",ArrowUp:"up",KeyS:"down",ArrowDown:"down",KeyA:"left",ArrowLeft:"left",KeyD:"right",ArrowRight:"right"};
  window.addEventListener("keydown",e=>{
    if(e.target.closest("input,select,textarea")||e.ctrlKey||e.altKey||e.metaKey)return;
    if(mode==="walk"&&keycodes[e.code]){e.preventDefault();keys.add(keycodes[e.code]);}
    if(!e.repeat&&e.code==="KeyE"&&mode==="walk")interact();
    if(!e.repeat&&e.code==="Space"&&mode==="replay"&&e.target.tagName!=="BUTTON"){e.preventDefault();playback();}
    if(e.code==="Escape"){if(cinematic)setCinematic(false);stage.classList.remove("full-view");}
  });
  window.addEventListener("keyup",e=>keys.delete(keycodes[e.code]));window.addEventListener("blur",()=>keys.clear());
  for(const b of document.querySelectorAll("[data-direction]")){
    b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);keys.add(b.dataset.direction);};
    b.onpointerup=b.onpointercancel=b.onlostpointercapture=()=>keys.delete(b.dataset.direction);
  }
  const pointers=new Map();let dragging=false,pinch=null;
  canvas.addEventListener("pointerdown",e=>{
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY});canvas.setPointerCapture(e.pointerId);
    if(pointers.size===1)dragging=false;
    if(pointers.size===2){const [a,b]=[...pointers.values()];pinch={dist:Math.hypot(a.x-b.x,a.y-b.y),zoom};dragging=true;}
  });
  canvas.addEventListener("pointermove",e=>{
    const p=pointers.get(e.pointerId);if(!p)return;
    const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;
    if(pointers.size===2&&pinch){
      const [a,b]=[...pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y);zoom=clamp(pinch.zoom*pinch.dist/Math.max(d,1),.54,2.25);render();return;
    }
    if(Math.hypot(p.x-p.startX,p.y-p.startY)>4)dragging=true;
    if(dragging){yaw-=dx*.008;pitch=clamp(pitch+dy*.006,.09,1.39);render();}
  });
  function endPointer(e){
    const p=pointers.get(e.pointerId);if(!p)return;pointers.delete(e.pointerId);
    if(!dragging&&e.type==="pointerup"&&mode==="walk"){
      const hit=art.pick(e.clientX,e.clientY);if(hit)walkTo(hit.landmark,hit.landmark?null:hit.point);
      canvas.focus({preventScroll:true});
    }
    if(pointers.size<2)pinch=null;
  }
  canvas.addEventListener("pointerup",endPointer);canvas.addEventListener("pointercancel",endPointer);
  canvas.addEventListener("wheel",e=>{e.preventDefault();zoom=clamp(zoom*Math.exp(e.deltaY*.0011),.54,2.25);render();},{passive:false});
  canvas.addEventListener("webglcontextlost",e=>{e.preventDefault();fallback("WebGL context lost.");});
  new ResizeObserver(()=>{snap();render();}).observe(stage);
  residentDestinations(true);refreshRecordings();render();
  window.TuesdayStage3D={loadTrace,seek,setCamera,setCinematic,setDressing,replaceActor,resetActor,getState,projectWorld:(x,y,z)=>art.projectWorld(x,y,z),renderNow(){snap();render();return getState();},
    follow(name){cameraActor=String(name);lastUI="";snap();render();return getState();}};
  const query=new URLSearchParams(location.search);
  if(query.has("take")){
    try{
      const archive=query.get("take"),matches=shots.map((s,i)=>s.archive===archive||s.archive.endsWith("/"+archive)?i:-1).filter(i=>i>=0);
      if(matches.length!==1)throw new Error("The linked recording is unavailable in this offline bundle.");
      selectTake(matches[0]);
      const event=query.get("event"),slot=event?trace.events.findIndex(e=>e.id===event):0;
      if(slot<0)throw new Error("The linked decision is missing from this recording.");
      const fraction=Number(query.get("at")||0);
      if(!Number.isFinite(fraction))throw new Error("The linked recording position is invalid.");
      if(query.has("camera"))setCamera(query.get("camera"));
      cameraActor=query.get("subject")||"reporter";seek(slot,fraction);
      if(query.get("play")==="1")playback();
    }catch(error){$("error").textContent=error.message;$("error").hidden=false;}
  }
  window.dispatchEvent(new Event("tuesdaystage3d:ready"));requestAnimationFrame(loop);
})();
