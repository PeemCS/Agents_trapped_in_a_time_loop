"use strict";
window.WinterReplay = (() => {
  const W=WinterMap, PL=W.places;
  const clocks=["6:00 am","9:30 am","1:00 pm","7:00 pm"];
  const legacy={Lou:["inn","square","studio","diner"],Bea:["diner","diner","square","diner"]};
  const townRide=[{x:17.35,y:13.60},{x:18.43,y:13.65},{x:18.43,y:16.70},{x:24.3,y:16.70}];
  const cityRide=[{x:-1.05,y:12},{x:6,y:12},{x:10.75,y:12}];
  const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
  function clockSlot(clock){const c=clock.toLowerCase().replace(/\s/g,"");return clocks.findIndex(v=>v.replace(/\s/g,"")===c);}
  function brief(s,max=12000){return typeof s==="string"?s.slice(0,max):"";}
  function normEvent(row,i,main,header){
    const fail=msg=>{throw new Error(`Decision ${i+1}: ${msg}`);};
    if(!row||typeof row!=="object")fail("invalid event");
    const {day,origin,place,decision}=row,clock=brief(row.clock,64),slot=clockSlot(clock);
    if(!Number.isInteger(day)||day<1||slot<0)fail("expected a valid Tuesday and rehearsal clock");
    if(!Object.hasOwn(PL,origin)||!Object.hasOwn(PL,place))fail("unknown origin or destination");
    if(!decision||typeof decision.action!=="string"||!decision.action)fail("missing committed action");
    const actor=brief(row.actor,80)||header;
    const role=brief(row.role,64)||(main?"reporter":"resident");
    const id=brief(row.id,160)||`d${String(day).padStart(2,"0")}-t${String(slot).padStart(2,"0")}-${role}`;
    const o=row.other_call;
    return {id,day,clock,slot,origin,place,actor,role,action:brief(decision.action,160),
      words:brief(decision.words),proposal:brief(decision.proposal||decision.detail),intention:brief(decision.intention),
      effect:brief(row.effect),reply:o&&typeof o==="object"?{name:brief(o.name,80),action:brief(o.decision?.action,160),words:brief(o.decision?.words)}:null};
  }
  function props(raw){
    if(!raw||typeof raw!=="object")return {};
    const out={};
    for(const k of ["marked","weather_tape","aired","band_recorded","called_sister"])if(typeof raw[k]==="boolean")out[k]=raw[k];
    for(const k of ["dishes","camera_battery"])if(Number.isFinite(raw[k]))out[k]=clamp(Math.floor(raw[k]),0,12);
    if(raw.bulletin && typeof raw.bulletin==="object"){
      const src=raw.bulletin;
      out.bulletin={channel:brief(src.channel,80),source_role:brief(src.source_role,80),source_place:brief(src.source_place,80),
        selected_by:brief(src.selected_by,80),source_ids:Array.isArray(src.source_ids)?src.source_ids.filter(k=>typeof k==="string").slice(0,8):[]};
    }
    if(typeof raw.camera_footage==="string")out.camera_footage=brief(raw.camera_footage,100);
    return out;
  }
  function normalize(raw){
    if(!raw||!Array.isArray(raw.events)||!raw.events.length)throw new Error("Choose a JSON run containing an events array.");
    if(raw.events.length>50000)throw new Error("This viewer accepts up to 50,000 decisions per run.");
    const names=Object.fromEntries(Object.entries(raw.cast_names || {}).filter(([role,name])=>
      role.length<65 && typeof name==="string" && name.length>0 && name.length<=80));
    const header=brief(raw.protagonist,80)||brief(raw.actor,80)||brief(raw.events[0]?.actor,80)||names.reporter;
    if(!header)throw new Error("The run is missing its protagonist’s name.");
    const ids=new Set(),events=raw.events.map((r,i)=>{
      const e=normEvent(r,i,true,header);
      if(e.actor!==header)throw new Error(`Decision ${i+1}: protagonist identity changes inside a single run.`);
      if(ids.has(e.id))throw new Error(`Duplicate protagonist decision ID ${e.id}.`);ids.add(e.id);
      e.before=props(r.visible_before || r.world_before);e.after=props(r.visible_after || r.world_after);
      if(r.bulletin && !e.after.bulletin)e.after.bulletin=props({bulletin:r.bulletin}).bulletin;
      e.cast=Array.isArray(r.cast)?r.cast.map((n,j)=>{
        if(!n || typeof n!=="object")throw new Error(`Decision ${i+1}: invalid resident event.`);
        const role=n.role || Object.entries(names).find(([,name])=>name===n.actor)?.[0] || "resident";
        const member=normEvent({...n,role,day:n.day??e.day,clock:n.clock??e.clock},i,false,names[role]||("Resident "+(j+1)));
        if(member.day!==e.day || member.slot!==e.slot)throw new Error(`Decision ${i+1}: cast event belongs to another time slot.`);
        return member;
      }):null;
      return e;
    });
    for(let i=1;i<events.length;i++){
      const e=events[i],p=events[i-1];
      if(e.day<p.day||(e.day===p.day&&e.slot<=p.slot))throw new Error(`Decision ${i+1} is out of chronological order.`);
    }
    return {header,municipality:brief(raw.municipality,100)||"Mill Creek",seed:raw.seed??null,model:brief(raw.model,160),source:brief(raw.source,160),archive:brief(raw.archive,220),memory:brief(raw.memory,80),condition:brief(raw.cast_condition,80),label:brief(raw.label,120),
      days:events.at(-1).day,events,ids,castNames:names,isFixture:raw.source==="injected_fixture"};
  }
  const pathCache=new Map();
  function path(a,b,scene){
    const k=[scene,a.x,a.y,b.x,b.y].join("/");
    if(pathCache.has(k))return pathCache.get(k);
    const v=W.route(a,b,scene);if(pathCache.size>360)pathCache.delete(pathCache.keys().next().value);pathCache.set(k,v);return v;
  }
  function anchor(id,index=0){
    const p=PL[id],o=index===1?[-.45,.27]:index===2?[.50,.10]:[0,0],q={x:p.x+o[0],y:p.y+o[1]};
    return W.walkable(q,p.scene)?q:{x:p.x,y:p.y};
  }
  function move(e,f,idx=0){
    const a=anchor(e.origin,idx),b=anchor(e.place,idx),sc=PL[e.origin].scene;
    const mk=(scene,pos,moving,phase,bus=null,hidden=false)=>({scene,pos,moving,phase,bus,hidden});
    if(e.origin!=="Pittsburgh"&&e.place==="Pittsburgh"){
      if(f<.32)return mk("town",W.sample(path(a,anchor("depot",idx),"town"),f/.32),true,"walking to coach",{scene:"town",pos:townRide[0]});
      if(f<.38)return mk("town",anchor("depot",idx),false,"boarding coach",{scene:"town",pos:townRide[0]});
      if(f<.68){const p=W.sample(townRide,(f-.38)/.30);return mk("town",p,true,"aboard coach",{scene:"town",pos:p},true);}
      if(f<.89){const p=W.sample(cityRide,(f-.68)/.21);return mk("city",p,true,"arriving in Pittsburgh",{scene:"city",pos:p},true);}
      return mk("city",W.sample([cityRide.at(-1),b],clamp((f-.89)/.085)),f<.975,"in Pittsburgh",{scene:"city",pos:cityRide.at(-1)});
    }
    const k=clamp((f-.13)/.62);
    if(sc!==PL[e.place].scene)return f<.5?mk(sc,a,false,"departing"):mk(PL[e.place].scene,b,false,"arrived");
    if(e.origin===e.place)return mk(sc,b,false,"at location");
    return mk(sc,W.sample(path(a,b,sc),k),k>0&&k<1,k<1?"walking":"arrived");
  }
  function residents(e,prior,f){
    if(e.cast!==null)return e.cast.map((n,i)=>{
      const m=move(n,f,i+1);
      return {name:n.actor,role:n.role,action:n.action,origin:n.origin,place:n.place,at:m.scene==="city"?"Pittsburgh":f<.75?n.origin:n.place,words:n.words,effect:n.effect,skin:n.role==="camera"?"Bea":n.role==="producer"?"Lou":i%2?"Bea":"Lou",pos:m.pos,scene:m.scene,bus:m.bus,moving:m.moving,visible:!m.hidden,phase:m.phase};
    });
    return Object.entries(legacy).map(([name,schedule],i)=>{
      const loc=schedule[e.slot],from=prior&&prior.day===e.day?schedule[prior.slot]:loc;
      const m=move({origin:from,place:loc},f,i+1);
      return {name,skin:name,role:"resident",origin:from,place:loc,at:f<.75?from:loc,pos:m.pos,scene:m.scene,moving:m.moving,phase:"scheduled"};
    });
  }
  function at(trace,index,progress){
    const events=trace.events,e=events[index],prior=events[index-1],daybreak=prior&&prior.day!==e.day;
    let f=clamp(progress),transition=0,banner="",shown=e,prev=prior;
    if(daybreak && f<.10){shown=prior;prev=events[index-2];transition=clamp(f/.10);f=1;}
    else if(daybreak&&f<.25){transition=1-clamp((f-.1)/.09);banner="The alarm rings again.";f=0;}
    else if(daybreak){f=clamp((f-.25)/.75);}
    if(index===0&&f<.07)banner="Tuesday, February 2";
    const hero=move(shown,f),people=residents(shown,prev,f);
    people.unshift({name:shown.actor,role:"reporter",action:shown.action,origin:shown.origin,place:shown.place,at:hero.scene==="city"?"Pittsburgh":f<.75?shown.origin:shown.place,words:shown.words,effect:shown.effect,skin:"Phil",main:true,phase:hero.phase,pos:hero.pos,scene:hero.scene,moving:hero.moving,visible:!hero.hidden});
    let bus=hero.bus;
    if(!bus){bus=hero.scene==="city"?{scene:"city",pos:cityRide.at(-1)}:(shown.slot===2?{scene:"town",pos:townRide[0]}:null);}
    const t=(shown.day-1)*32+shown.slot*8+f*5;
    return {scene:hero.scene,people,bus,facts:f>=.68?shown.after:shown.before,before:shown.before,after:shown.after,actionProgress:f,day:shown.day,slot:shown.slot,clock:shown.clock,t,hero:hero.pos,transition,banner,
      place:hero.scene==="city"?"Pittsburgh":f>=.75?shown.place:shown.origin,phase:hero.phase,event:e,shown,daybreak:!!daybreak,
      caption:!!daybreak&&shown===e&&progress<.25?"The next morning":null};
  }
  return {clocks,townRide,cityRide,clamp,normalize,at,anchor,move};
})();
