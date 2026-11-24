"use strict";
(() => {
  const W=WinterMap,R=WinterReplay,A=WinterArt,places=W.places,$=id=>document.getElementById(id);
  const canvas=$("town"),stage=$("stage"),node=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!=null)e.textContent=content;return e;};
  const formatClock=s=>s.toUpperCase(),num=n=>String(n).padStart(2,"0"),clamp=R.clamp;
  const prettify=s=>s.replace(/_/g," ").replace(/^./,c=>c.toUpperCase());
  const traces=window.TOWN_TRACES.map(R.normalize),options=traces.map(t=>t.label),keys=new Set();
  let framing="street",cameraActor="reporter",cameraScale=1;
  let mode="walk",selected=Math.max(0,traces.findIndex(t=>t.header==="Phil")),trace=traces[selected],index=0,progress=0,playing=false,speed=1,overview=false,cinema=false,filmCaptions=true;
  let sound=false,audioCtx=null,liveWaiting=false,last=performance.now(),viewTransform=null,renderWorld=null,uiKey="",logKey="",frame=0;
  let width=1,height=1,dpr=1,follow=null,followScene=null,lastInteraction="",noticeUntil=0,gameTime=0;
  const reduced=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const manual={day:1,slot:0,scene:"town",pos:R.anchor("inn"),lastPlace:"inn",marked:false,forecast:false,dishes:2,called:false,lastAction:"",log:[],logSeq:0,route:null,walked:0,dir:{dx:1,dy:1},special:null,cast:[]};
  const schedules={Rita:["inn","square","studio","diner"],Larry:["square","studio","depot","diner"]};
  function residents(immediate=false){
    manual.cast=["Rita","Larry"].map((name,i)=>{
      const loc=schedules[name][manual.slot],target=R.anchor(loc,i+1),old=manual.cast[i];
      const p=immediate||!old?target:old.pos;
      return {name,role:i===0?"producer":"camera",skin:i===0?"Lou":"Bea",scene:"town",place:loc,at:loc,pos:{...p},dest:loc,path:W.route(p,target,"town"),moved:0,moving:false};
    });
  }
  function log(action,effect,words="",who="Phil",extra=""){
    manual.log.push({id:"free-"+(++manual.logSeq),day:manual.day,clock:R.clocks[manual.slot],actor:who,action,effect,words,extra});
    if(manual.log.length>320)manual.log.shift();logKey="";
  }
  function blip(){
    if(!sound||!audioCtx)return;
    const now=audioCtx.currentTime;[392,493.883,587.33].forEach((freq,i)=>{
      const os=audioCtx.createOscillator(),v=audioCtx.createGain();os.type="sine";os.frequency.value=freq;
      v.gain.setValueAtTime(0,now+i*.125);v.gain.linearRampToValueAtTime(.045,now+i*.125+.012);v.gain.exponentialRampToValueAtTime(.001,now+i*.125+.17);
      os.connect(v);v.connect(audioCtx.destination);os.start(now+i*.125);os.stop(now+i*.125+.19);
    });
  }
  function nextTime(){
    if(manual.special)return;
    manual.route=null;
    if(manual.slot===3){
      manual.special={kind:"dawn",elapsed:0,duration:reduced?.50:1.7,changed:false};return;
    }
    manual.slot++;residents();log("time advances","It is "+formatClock(R.clocks[manual.slot])+".");uiKey="";
  }
  function resetAtDawn(){
    manual.day++;manual.slot=0;manual.scene="town";manual.pos=R.anchor("inn");manual.dir={dx:1,dy:1};manual.lastPlace="inn";
    manual.marked=false;manual.forecast=false;manual.dishes=2;manual.called=false;manual.lastAction="";manual.route=null;manual.walked=0;residents(true);
    log("wake at the hotel","The radio plays three notes. The date is February 2 again.");blip();follow=null;uiKey="";
  }
  function near(){
    const place=W.nearestPlace(manual.pos,manual.scene);
    const neighbors=manual.cast.filter(p=>p.scene===manual.scene&&W.distance(p.pos,manual.pos)<1.45);
    return {place,neighbors};
  }
  const locInfo={
    inn:[["Read the date","read the calendar","The display reads Tuesday, February 2."],["Mark the sill","leave a pencil mark","A pencil cross is visible on the hotel windowsill."]],
    diner:[["Clear the tables","clear the tables","Phil carries the dirty cups to the counter."]],
    square:[["Watch the forecast","watch the ceremony","The crowd turns toward the bandstand."]],
    studio:[["File a forecast","file a forecast","The red studio light comes on. The station records the forecast."],["Play the piano","play the piano","Phil plays a scale at the upright piano."]],
    depot:[["Read the timetable","check the timetable","The coach leaves for Pittsburgh at 1:00 PM."]],
    Pittsburgh:[["Use the payphone","call home","Phil leaves a message on his home phone."]]
  };
  function notice(s){lastInteraction=s;noticeUntil=gameTime+3.6;}
  function manualAction(id){
    if(mode!=="walk"||manual.special)return;
    const {place,neighbors}=near(),here=place.distance<1.58?place.id:null;
    if(id.startsWith("talk:")){
      const name=id.slice(5);if(!neighbors.some(n=>n.name===name))return;
      const line=name==="Rita"?["What do you want to lead with?","The band is nearly ready.","The studio is yours if you need it.","How did your piece turn out?"][manual.slot]:
        ["I've got a clean tape and one battery.","The light is good out by the square.","There's still time for a shot of the coach.","I'll put the camera away."][manual.slot];
      log("talk to "+name,name+" speaks with Phil.",line,name);notice(name+" speaks");return;
    }
    if(id==="wait-coach"&&here==="depot"&&manual.slot<2){while(manual.slot<2)nextTime();return;}
    if(id==="coach"&&here==="depot"&&manual.slot===2){
      manual.route=null;manual.special={kind:"coach",elapsed:0,duration:reduced?1.1:5.8};
      log("take the coach","Phil uses his ticket and boards the afternoon coach.");uiKey="";return;
    }
    if(id==="sleep"&&here==="Pittsburgh"){manual.special={kind:"dawn",elapsed:0,duration:reduced?.5:1.7,changed:false};log("stay in Pittsburgh","Phil stays in Pittsburgh until the end of the evening.");return;}
    const item=(locInfo[here]||[]).find(x=>x[1]===id);
    if(!item)return;
    let effect=item[2];if(id==="leave a pencil mark"){manual.marked=true;}if(id==="file a forecast")manual.forecast=true;
    if(id==="clear the tables")manual.dishes=Math.max(0,manual.dishes-1);if(id==="call home")manual.called=true;manual.lastAction=id.replaceAll(" ","_");
    if(id==="read the calendar"&&manual.marked)effect+=" The pencil mark is still there.";
    log(id,effect);notice(item[0]);uiKey="";
  }
  function actionsAvailable(){
    if(manual.special)return [];
    const {place,neighbors}=near(),here=place.distance<1.58?place.id:null;
    const arr=neighbors.map(p=>["Talk to "+p.name,"talk:"+p.name]);
    if(here==="depot"){if(manual.slot===2)arr.unshift(["Board the coach","coach"]);else if(manual.slot<2)arr.push(["Wait for the 1 PM coach","wait-coach"]);}
    if(here)arr.push(...locInfo[here].map(r=>[r[0],r[1]]));
    if(here==="Pittsburgh")arr.push(["Stay until morning","sleep"]);
    return arr;
  }
  function walkTo(q,label=""){
    if(mode!=="walk"||manual.special)return false;
    const path=W.route(manual.pos,q,manual.scene),length=W.pathLength(path);
    if(length<.03){manual.route=null;return false;}
    manual.route={path,length,travel:0,label};
    return true;
  }
  function simpleMove(dx,dy){
    const pos=manual.pos,n=W.distance({x:0,y:0},{x:dx,y:dy});if(!n)return;
    const target={x:pos.x+dx,y:pos.y+dy};
    if(W.walkable(target,manual.scene)){manual.pos=target;}
    else if(W.walkable({x:target.x,y:pos.y},manual.scene)){manual.pos={x:target.x,y:pos.y};}
    else if(W.walkable({x:pos.x,y:target.y},manual.scene)){manual.pos={x:pos.x,y:target.y};}
    manual.dir={dx:manual.pos.x-pos.x,dy:manual.pos.y-pos.y};manual.walked+=W.distance(manual.pos,pos);
  }
  function updateManual(dt){
    if(manual.special){
      const s=manual.special;s.elapsed+=dt;const f=clamp(s.elapsed/s.duration);
      if(s.kind==="dawn"&&!s.changed&&f>=.47){resetAtDawn();s.changed=true;}
      if(f>=1){
        if(s.kind==="coach"){manual.scene="city";manual.pos=R.anchor("Pittsburgh");manual.lastPlace="Pittsburgh";log("arrive in Pittsburgh","The coach doors open at the Pittsburgh terminal. Phil steps onto the platform.");follow=null;}
        manual.special=null;notice("");uiKey="";
      }return;
    }
    for(const npc of manual.cast){
      const len=W.pathLength(npc.path);npc.moving=npc.moved<len-.03;
      if(npc.moving){npc.moved=Math.min(len,npc.moved+dt*1.8);npc.pos=W.sample(npc.path,npc.moved/len);}
    }
    let x=Number(keys.has("right"))-Number(keys.has("left")),y=Number(keys.has("down"))-Number(keys.has("up"));
    const norm=Math.hypot(x,y);
    manual.moving=false;
    if(norm){
      manual.route=null; x/=norm;y/=norm;
      const v=W.uniso(x,y),nv=Math.hypot(v.x,v.y);simpleMove(dt*3.25*v.x/nv,dt*3.25*v.y/nv);
      manual.moving=!!(manual.dir.dx||manual.dir.dy);
    }else if(manual.route){
      const p=manual.route;p.travel=Math.min(p.length,p.travel+dt*3.2);const pos=W.sample(p.path,p.travel/p.length);manual.pos={x:pos.x,y:pos.y};manual.dir={dx:pos.dx,dy:pos.dy};manual.moving=true;
      if(p.travel>=p.length){manual.route=null;manual.moving=false;}
    }
    const nearest=W.nearestPlace(manual.pos,manual.scene);
    if(nearest.distance<1.4&&nearest.id!==manual.lastPlace){manual.lastPlace=nearest.id;log("walk to "+places[nearest.id].short,"Phil reaches "+places[nearest.id].label+".");}
  }
  function manualWorld(){
    let scene=manual.scene,hero={...manual.pos,...manual.dir},moving=manual.moving,visible=true,bus=null,transition=0,banner="",phase="free walk";
    if(scene==="city")bus={scene,pos:R.cityRide.at(-1)};
    else if(manual.slot===2)bus={scene,pos:R.townRide[0]};
    if(manual.special){
      const s=manual.special,f=clamp(s.elapsed/s.duration);
      if(s.kind==="coach"){
        const p=R.move({origin:"depot",place:"Pittsburgh"},.32+.68*f);scene=p.scene;hero=p.pos;visible=!p.hidden;bus=p.bus;moving=p.moving;phase=p.phase;
      }else{
        transition=f<.47?f/.47:1-(f-.47)/.53;banner=f>.55?"The alarm rings again.":"";phase="dawn";
      }
    }
    const location=scene==="city"?"Pittsburgh":manual.lastPlace;
    return {day:manual.day,slot:manual.slot,clock:R.clocks[manual.slot],scene,hero,bus,people:[
      {name:"Phil",main:true,role:"reporter",skin:"Phil",pos:hero,scene,moving,visible,origin:manual.lastPlace,place:location,at:location,action:manual.lastAction},...manual.cast],
      facts:{marked:manual.marked,weather_tape:manual.forecast,dishes:manual.dishes,called_sister:manual.called},
      transition,banner,phase,t:gameTime,place:location,path:manual.route?manual.route.path:null};
  }
  function entry(e,active=false,more=true){
    const wrap=node("article","entry"+(active?" selected":""));
    wrap.append(node("span","stamp",`Day ${num(e.day)} · ${formatClock(e.clock)}`));
    wrap.append(node("strong","",prettify(e.action)));
    if(more){
      if(e.words)wrap.append(node("blockquote","",e.actor+" · “"+e.words+"”"));
      if(e.effect)wrap.append(node("p","",e.effect));
      if(e.reply?.words)wrap.append(node("div","cast",e.reply.name+" · “"+e.reply.words+"”"));
      if(e.cast)for(const a of e.cast){const detail=a.words?" · “"+a.words+"”":"";wrap.append(node("div","cast",a.actor+" · "+prettify(a.action)+detail));}
      if(e.id&&!e.id.startsWith("free-"))wrap.append(node("div","evidence",e.id));
    }
    return wrap;
  }
  function setOptions(){
    const s=$("source");s.replaceChildren(...options.map((name,i)=>{const op=node("option","",name);op.value=String(i);return op;}));s.value=String(selected);
  }
  function showError(message){const er=$("error");er.hidden=!message;er.textContent=message||"";}
  function toMode(next){
    mode=next;if(mode==="walk")cameraActor="reporter";playing=false;liveWaiting=false;keys.clear();follow=null;uiKey="";logKey="";showError("");
    document.body.classList.toggle("is-replay",mode==="replay");
    $("walk-mode").classList.toggle("active",mode==="walk");$("walk-mode").setAttribute("aria-pressed",String(mode==="walk"));
    $("replay-mode").classList.toggle("active",mode==="replay");$("replay-mode").setAttribute("aria-pressed",String(mode==="replay"));
    $("walk-content").hidden=$("manual-controls").hidden=mode!=="walk";
    $("replay-content").hidden=$("replay-controls").hidden=mode!=="replay";
  }
  function selectTrace(i){
    selected=i;trace=traces[i];index=progress=0;playing=false;toMode("replay");$("source").value=String(i);
    $("scrub").max=String(trace.events.length);uiKey="";logKey="";render(0,true);
  }
  function seek(i,f=0){
    if(!Number.isInteger(i)||i<0||i>=trace.events.length||!Number.isFinite(f))throw new RangeError("Seek outside the loaded recording.");
    if(mode!=="replay")toMode("replay");index=i;progress=clamp(f);playing=false;liveWaiting=false;follow=null;uiKey="";logKey="";render(0,true);return getState();
  }
  function playToggle(){
    if(mode!=="replay")toMode("replay");
    if(index===trace.events.length-1&&progress>=.999){index=0;progress=0;follow=null;}
    playing=!playing;liveWaiting=false;uiKey="";
  }
  function play(){
    if(mode!=="replay")toMode("replay");
    liveWaiting=true;
    if(index<trace.events.length-1 || progress<1)playing=true;
    uiKey="";render(0,true);return getState();
  }
  function loadTrace(raw){
    const next=R.normalize(raw);traces.push(next);
    const prefix=next.isFixture?"Fixture · ":"";
    options.push(prefix+(next.label||next.header+" · "+(next.model||"imported run"))+(next.seed==null?"":" · "+next.seed));
    setOptions();selectTrace(traces.length-1);return getState();
  }
  function appendOrRefresh(raw,{follow:willFollow=true}={}){
    const incoming=R.normalize(raw);
    const same=mode==="replay"&&trace.header===incoming.header&&trace.model===incoming.model&&String(trace.seed)===String(incoming.seed)
      &&trace.source===incoming.source&&trace.memory===incoming.memory&&trace.condition===incoming.condition&&trace.municipality===incoming.municipality&&selected>=window.TOWN_TRACES.length&&trace===traces[selected];
    if(!same){loadTrace(raw);if(willFollow){playing=true;liveWaiting=true;}return getState();}
    if(incoming.events.length<trace.events.length)throw new Error("A live update cannot remove committed decisions.");
    for(let i=0;i<trace.events.length;i++)if(JSON.stringify(trace.events[i])!==JSON.stringify(incoming.events[i]))throw new Error("Committed decision "+(i+1)+" changed in the live update.");
    const grew=incoming.events.length>trace.events.length;
    trace=incoming;traces[selected]=incoming;
    return refreshTail(grew,willFollow);
  }
  function refreshTail(grew,willFollow){
    $("scrub").max=String(trace.events.length);
    if(willFollow&&grew&&liveWaiting)playing=true;
    if(willFollow)liveWaiting=true;
    if(grew){logKey="";uiKey="";render(0,true);}
    return getState();
  }
  function appendEvents(rows,{offset,follow:willFollow=true}={}){
    if(mode!=="replay"||selected<window.TOWN_TRACES.length)throw new Error("Load the first segment before appending.");
    if(!Number.isInteger(offset)||offset<0||offset>trace.events.length)throw new RangeError("Invalid committed offset.");
    if(!Array.isArray(rows))throw new TypeError("Expected an array of source events.");
    if(!rows.length)return getState();
    if(offset+rows.length>50000)throw new RangeError("This viewer accepts up to 50,000 decisions per run.");
    const parsed=R.normalize({protagonist:trace.header,cast_names:trace.castNames,events:rows}).events;
    const overlap=Math.min(parsed.length,trace.events.length-offset);
    for(let j=0;j<overlap;j++){
      if(JSON.stringify(parsed[j])!==JSON.stringify(trace.events[offset+j]))throw new Error("A retried segment changed a committed decision.");
    }
    const fresh=parsed.slice(overlap);
    if(!fresh.length)return refreshTail(false,willFollow);
    const last=trace.events.at(-1),first=fresh[0];
    if(first.day<last.day||(first.day===last.day&&first.slot<=last.slot))throw new Error("New decisions must follow the committed timeline.");
    if(fresh.some(row=>trace.ids.has(row.id)))throw new Error("New decision ID already occurs on the timeline.");
    // Validate the entire segment before exposing any of its rows to the player.
    for(const row of fresh){trace.events.push(row);trace.ids.add(row.id);}
    trace.days=trace.events.at(-1).day;
    return refreshTail(true,willFollow);
  }
  function setCamera({actor="reporter",framing:shot="street",scale=1}={}){
    if(!["street","close"].includes(shot))throw new RangeError("Camera framing is street or close.");
    cameraActor=String(actor);framing=shot;cameraScale=clamp(Number(scale)||1,.65,2.5);follow=null;uiKey="";
    $("close-shot").setAttribute("aria-pressed",String(framing==="close"));$("close-shot").textContent=framing==="close"?"Street":"Close-up";
    render(0,true);return getState();
  }
  function setCinematic(on,{captions=true}={}){
    cinema=!!on;filmCaptions=!!captions;document.body.classList.toggle("cinema",cinema);measure();follow=null;render(0,true);return getState();
  }
  function getState(){
    const w=renderWorld||manualWorld();
    return {mode,index:mode==="replay"?index:null,progress:mode==="replay"?progress:null,phase:w.phase,actor:mode==="replay"?trace.header:"Phil",
      place:w.place,scene:w.scene,municipality:mode==="replay"?trace.municipality:"Mill Creek",day:w.day,clock:w.clock,playing,overview,cinematic:cinema,position:{x:w.hero.x,y:w.hero.y},
      total:mode==="replay"?trace.events.length:manual.logSeq,source:mode==="replay"?trace.source:"manual",eventId:mode==="replay"?trace.events[index].id:null,archive:mode==="replay"?trace.archive:"",cameraActor:w.cameraSubject?.name||w.people[0].name,cameraPlace:w.cameraSubject?.at||w.place,heroScene:w.people[0].scene,
      subjects:w.people.map(p=>({name:p.name,role:p.role,scene:p.scene,at:p.at,action:p.action||"",x:p.pos.x,y:p.pos.y,visible:p.visible!==false})),framing:w.isClose?"close":"street",worldFacts:w.facts||{}};
  }
  function updateUi(world){
    const modeIsWalk=mode==="walk",act=modeIsWalk?actionsAvailable():[];
    const subject=world.cameraSubject,shown=world.shown;
    let e=shown;
    if(!subject.main && shown){
      e=shown.cast?.find(n=>n.actor===subject.name);
      if(!e&&shown.reply?.name===subject.name){
        e={id:shown.id+"/reply",actor:subject.name,action:shown.reply.action,words:shown.reply.words,effect:""};
      }
    }
    const where=modeIsWalk?world.phase!=="free walk"?world.phase:(W.nearestPlace(manual.pos,manual.scene).distance<1.62?places[W.nearestPlace(manual.pos,manual.scene).id].label:"On foot"):world.cameraSubject.phase==="walking"?"Walking to "+places[world.cameraSubject.place].short:
      ["aboard coach","boarding coach","arriving in Pittsburgh","walking to coach"].includes(world.cameraSubject.phase)?prettify(world.cameraSubject.phase):places[world.cameraSubject.at]?.label||world.cameraSubject.at;
    const key=[mode,world.day,world.slot,world.phase,world.scene,where,trace.header,index,selected,playing,speed,act.map(x=>x[1]).join(","),world.banner,filmCaptions,cinema,e?.id||"",world.caption||"",framing,cameraActor].join("|");
    if(key!==uiKey){
      uiKey=key;
      $("hud-time").textContent=formatClock(world.clock);$("hud-day").textContent="TUESDAY · DAY "+num(world.day);
      const townName=modeIsWalk?"Mill Creek":trace.municipality;
      $("scene-name").textContent=world.scene==="city"?"Pittsburgh, PA":townName+(townName.includes(",")?"":", PA");$("actor-name").textContent=world.cameraSubject.name;
      $("place-name").textContent=where;$("mode-label").textContent=modeIsWalk?"FREE WALK":trace.isFixture?"FIXTURE REPLAY":"RECORDED RUN";
      $("alarm").textContent=world.banner||"";$("play").textContent=playing?"Pause":"Play";$("play").setAttribute("aria-label",playing?"Pause recording":"Play recording");
      $("speed").textContent=speed+"×";$("position").textContent=(index+1)+" / "+trace.events.length;
      const words=e?.words||"",effect=e?.effect||"";
      const showCaption=!modeIsWalk&&filmCaptions&&!world.caption&&!world.banner&&(words||effect);
      $("film-caption").hidden=!showCaption;$("film-speaker").textContent=words?e?.actor||"":e?.actor+" · "+prettify(e?.action||"");
      $("film-line").textContent=words?"“"+words+"”":effect;
      if(modeIsWalk){
        $("actions").replaceChildren(...act.map(([label,id])=>{const b=node("button","",label);b.addEventListener("click",()=>manualAction(id));return b;}));
        $("wait").textContent=manual.slot===3?"Next morning →":"Wait until "+formatClock(R.clocks[manual.slot+1])+" →";$("wait").disabled=!!manual.special;
        const dest=$("destination"),old=dest.value;dest.replaceChildren(...Object.entries(places).filter(([,p])=>p.scene===manual.scene).map(([id,p])=>{const op=node("option","",p.label);op.value=id;return op;}));
        if([...dest.options].some(o=>o.value===old))dest.value=old;else if(manual.scene==="town")dest.value="square";
        $("walk-destinations").hidden=manual.scene==="city"||!!manual.special;
      }else{
        const followSelect=$("camera-actor");
        const menu=world.people.map(p=>{
          const option=node("option","",p.name+" · "+(p.role==="camera"?"cameraman":p.role));
          option.value=p.name;return option;
        });
        followSelect.replaceChildren(...menu);followSelect.value=world.cameraSubject.name;
        $("run-meta").textContent=(trace.isFixture?"Injected test fixture · ":trace.label?"Archived model run · ":"")+[trace.model,trace.seed!=null?"seed "+trace.seed:"",trace.days+" days"].filter(Boolean).join(" · ");
      }
    }
    $("dawn").style.opacity=String(world.transition||0);
    if(!modeIsWalk)$("scrub").value=String(index+progress);
    const lk=modeIsWalk?"m"+manual.log.at(-1)?.id:"r"+selected+"/"+index+"/"+world.shown.id;
    if(logKey!==lk){
      logKey=lk;const list=$("events");list.replaceChildren();
      if(modeIsWalk){$("event-count").textContent=String(manual.logSeq);for(const v of manual.log.slice(-12).reverse())list.append(entry(v,true));}
      else{const visible=world.shown===trace.events[index]?index:Math.max(0,index-1);
        $("event-count").textContent=(visible+1)+" / "+trace.events.length;
        for(let i=visible;i>=Math.max(0,visible-10);i--)list.append(entry(trace.events[i],i===visible,i===visible));
      }
      list.scrollTop=0;
    }
  }
  function measure(){
    const r=canvas.getBoundingClientRect();width=Math.max(1,r.width);height=Math.max(1,r.height);dpr=Math.min(window.devicePixelRatio||1,2);
    if(canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)){canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);}
  }
  function render(dt=0,snap=false){
    const w=mode==="walk"?manualWorld():R.at(trace,index,progress);
    const subject=w.people.find(p=>p.role===cameraActor||p.name===cameraActor)||w.people[0];
    w.cameraSubject=subject;const focusPlace=subject.at||w.place;
    const stationary=mode==="walk"?(!manual.special && !subject.moving && W.distance(subject.pos,places[focusPlace]||subject.pos)<1.65):
      !subject.moving && !["aboard coach","boarding coach","arriving in Pittsburgh","walking to coach","walking","departing"].includes(subject.phase) &&
      (subject.origin===subject.place || w.actionProgress>=.78 || (w.caption && w.daybreak));
    w.isClose=framing==="close"&&!overview&&stationary&&!!places[focusPlace]&&!!window.WinterInterior;
    w.scene=subject.scene;if(subject.bus)w.bus=subject.bus;renderWorld=w;
    let focus={...subject.pos};const compact=width<600;
    const fit=clamp(Math.min(width/1440,height/785),.25,1.6);
    const zoom=overview?fit:(compact?clamp(width/510,.71,1.10):clamp(Math.min(width/735,height/475),.90,1.95))*cameraScale;
    if(overview)focus=w.scene==="town"?{x:10,y:10.3}:{x:10,y:9.65};
    else if(mode==="walk"&&!w.bus?.pos?.hidden){focus.x+=(10.1-focus.x)*.15;focus.y+=(9.9-focus.y)*.15;}
    if(snap||!follow||followScene!==w.scene||mode==="replay")follow={...focus};
    else{const k=1-Math.exp(-dt*5.8);follow=W.mix(follow,focus,k);}
    followScene=w.scene;
    viewTransform=w.isClose?null:A.draw(canvas,w,{width,height,dpr,focus:follow,zoom,overview});
    if(w.isClose)WinterInterior.draw(canvas,w,focusPlace,{width,height,dpr});
    updateUi(w);
  }
  function step(now){
    if(mode==="replay"&&!playing&&uiKey){last=now;frame=requestAnimationFrame(step);return;}
    if(now-last<1000/35){frame=requestAnimationFrame(step);return;}
    const dt=Math.min(.085,Math.max(0,(now-last)/1000));last=now;gameTime+=dt;
    if(mode==="walk")updateManual(dt);
    else if(playing){const current=trace.events[index];
      const base=current.place==="Pittsburgh"&&current.origin!=="Pittsburgh"?6.9:4.5;
      progress+=dt*speed/base;
      if(progress>=1){if(index<trace.events.length-1){index++;progress=0;if(trace.events[index].day!==current.day)blip();}
        else{progress=1;playing=false;}}
    }
    render(dt);frame=requestAnimationFrame(step);
  }
  $("walk-mode").addEventListener("click",()=>{toMode("walk");render(0,true);});
  $("replay-mode").addEventListener("click",()=>{toMode("replay");render(0,true);});
  $("open-file").addEventListener("click",()=>$("file").click());
  $("file").addEventListener("change",async e=>{
    const file=e.target.files?.[0];e.target.value="";if(!file)return;
    try{if(file.size>32*1024*1024)throw new Error("Please use a run below 32 MB.");loadTrace(JSON.parse(await file.text()));}
    catch(err){showError(err.message||"Unable to read recording.");}
  });
  $("source").addEventListener("change",e=>selectTrace(Number(e.target.value)));
  $("camera-actor").addEventListener("change",e=>setCamera({actor:e.target.value,framing,scale:cameraScale}));
  $("close-shot").addEventListener("click",()=>{overview=false;$("overview").textContent="Overview";$("overview").setAttribute("aria-pressed","false");setCamera({actor:cameraActor,framing:framing==="close"?"street":"close"});});
  $("overview").addEventListener("click",()=>{overview=!overview;$("overview").setAttribute("aria-pressed",String(overview));$("overview").textContent=overview?"Follow actor":"Overview";render(0,true);});
  $("expand").addEventListener("click",async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await stage.requestFullscreen();}catch{setCinematic(!cinema);}});
  $("wait").addEventListener("click",nextTime);
  $("go").addEventListener("click",()=>{const id=$("destination").value;if(places[id])walkTo(R.anchor(id),id);});
  $("prev").addEventListener("click",()=>seek(Math.max(0,index-1),0));$("next").addEventListener("click",()=>seek(Math.min(trace.events.length-1,index+1),0));
  $("play").addEventListener("click",playToggle);$("speed").addEventListener("click",()=>{speed=speed===1?2:speed===2?4:1;uiKey="";});
  $("scrub").addEventListener("input",e=>{const v=Number(e.target.value),i=Math.min(trace.events.length-1,Math.floor(v));seek(i,v-i);});
  $("sound").addEventListener("click",()=>{try{if(!audioCtx)audioCtx=new(window.AudioContext||window.webkitAudioContext)();audioCtx.resume();sound=!sound;$("sound").setAttribute("aria-pressed",String(sound));$("sound").textContent=sound?"Sound on":"Sound off";if(sound)blip();}catch{showError("This browser could not open the audio device.");}});
  const keysByCode={ArrowUp:"up",KeyW:"up",ArrowDown:"down",KeyS:"down",ArrowLeft:"left",KeyA:"left",ArrowRight:"right",KeyD:"right"};
  window.addEventListener("keydown",e=>{
    if(e.target.closest("input,select,textarea")||e.metaKey||e.ctrlKey||e.altKey)return;
    if(e.code==="Escape"&&cinema){setCinematic(false);return;}
    if(mode==="walk"&&keysByCode[e.code]){e.preventDefault();keys.add(keysByCode[e.code]);}
    if(!e.repeat&&mode==="walk"&&e.code==="KeyE"){const a=actionsAvailable()[0];if(a)manualAction(a[1]);}
    if(!e.repeat&&mode==="replay"&&e.code==="Space"&&e.target.tagName!=="BUTTON"){e.preventDefault();playToggle();}
  });
  window.addEventListener("keyup",e=>{if(keysByCode[e.code])keys.delete(keysByCode[e.code]);});
  window.addEventListener("blur",()=>keys.clear());
  for(const b of document.querySelectorAll("[data-dir]")){
    b.addEventListener("pointerdown",e=>{e.preventDefault();keys.add(b.dataset.dir);b.setPointerCapture(e.pointerId);});
    const clear=()=>keys.delete(b.dataset.dir);b.addEventListener("pointerup",clear);b.addEventListener("pointercancel",clear);b.addEventListener("lostpointercapture",clear);
  }
  canvas.addEventListener("pointerup",e=>{
    if(mode!=="walk"||manual.special||!viewTransform)return;const rect=canvas.getBoundingClientRect();
    const local={x:(e.clientX-rect.left-viewTransform.ox)/viewTransform.z,y:(e.clientY-rect.top-viewTransform.oy)/viewTransform.z};
    const building=A.landmarkAt(local,manual.scene);
    if(building){walkTo(R.anchor(building),building);canvas.focus({preventScroll:true});return;}
    const target=W.uniso(local.x,local.y);
    const bounds=W.extent[manual.scene];target.x=clamp(target.x,bounds.x1,bounds.x2);target.y=clamp(target.y,bounds.y1,bounds.y2);
    const hit=W.nearestPlace(target,manual.scene);if(hit.distance<.95)walkTo(R.anchor(hit.id),hit.id);else walkTo(target);canvas.focus({preventScroll:true});
  });
  new ResizeObserver(()=>{measure();render(0,true);}).observe(stage);
  residents(true);log("wake at the hotel","The radio plays three notes. A van backfires twice outside.");
  setOptions();$("scrub").max=String(trace.events.length);measure();render(0,true);
  window.TuesdayTown={loadTrace,appendOrRefresh,appendEvents,play,seek,setCinematic,setCamera,getState,
    // A renderer can ask for a clean frame after changing its viewport.
    renderNow(){measure();render(0,true);return getState();}};
  window.dispatchEvent(new Event("tuesdaytown:ready"));frame=requestAnimationFrame(step);
})();
