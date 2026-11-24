"use strict";
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),vm=require("node:vm");
const {W,resolve,world}=require("./resolve.cjs");
const root=__dirname,out=path.join(root,"evidence");fs.mkdirSync(out,{recursive:true});
const ctx={window:{},WinterMap:W};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,"../stage3d/viewer/geometry.js"),"utf8"),ctx);ctx.TUESDAY_STAGE=ctx.window.TUESDAY_STAGE;
vm.runInContext(fs.readFileSync(path.join(root,"../stage3d/viewer/placement.js"),"utf8"),ctx);
const dressing=ctx.window.TownStagePlacement;
const hash=x=>crypto.createHash("sha256").update(x).digest("hex");
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function assert(v,msg){if(!v)throw Error(msg);}
const groups={},counts={calls:0,sampledPositions:0,basePointViolations:0,segments:0,coincidentEndpointTicks:0,ticksWithMultipleActors:0,nearActorTicks:0,
  dressedConflictWalks:0,dressedConflictMovingWalks:0,retargetAttempts:0,retargetClear:0},dressed=[],near=[],roots=[];
const fps=24,framesPerSlot=96;
let native=null;
for(const folder of fs.readdirSync(path.join(root,"runs")).sort()){
  const file=path.join(root,"runs",folder,"take.json"),data=JSON.parse(fs.readFileSync(file));
  const sourceSha=hash(fs.readFileSync(file));roots.push({condition:data.condition,seed:data.seed,sourceSha});
  const position={...data.initial};const previous={};
  const sample={samples:[],slots:[],sourceSha,fps,framesPerSlot};
  for(const [tick,events] of data.ticks.entries()){
    let close=false,coincident=false;
    for(const e of events){
      const rawBytes=fs.readFileSync(path.join(root,e.raw)),raw=JSON.parse(rawBytes),choice=JSON.parse(raw.response.message.content);
      assert(hash(rawBytes)===e.raw_sha256&&raw.request.model==="qwen3:0.6b"&&raw.response.done_reason==="stop","Changed source");
      assert(choice.x===e.requested.x&&choice.y===e.requested.y&&choice.say===e.say,"Model/receipt mismatch");
      const obs=JSON.parse(raw.request.messages.find(m=>m.role==="user").content);
      assert(equal(obs.you_are_at,position[e.role])&&equal(e.start,position[e.role]),"Post-barrier position leaked");
      for(const peer of events.filter(p=>p.role!==e.role)){
        const seen=W.distance(e.start,position[peer.role])<=4;
        assert(seen===Object.hasOwn(obs.nearby_people,peer.actor),"Wrong observation radius");
        if(seen)assert(equal(obs.nearby_people[peer.actor],position[peer.role]),"Leaked later peer position");
      }
      assert(!obs.your_own_previous_walks.some(v=>v.role&&v.role!==e.role),"Another player's private history appeared");
      if(previous[e.role])assert(equal(obs.your_own_previous_walks.at(-1).resolved,previous[e.role].resolved)&&obs.your_own_previous_walks.at(-1).status===previous[e.role].status,"Prior own outcome missing");
      const again=resolve(e.start,e.requested);for(const k of Object.keys(again))assert(equal(again[k],e[k]),"Different geometry "+e.id+"/"+k);
      counts.calls++;counts.segments+=Math.max(0,e.path.length-1);
      const group=groups[data.condition]??={},g=group[e.role]??={calls:0,requestedOffDoor:0,resolvedOffDoor:0,traveledOffDoor:0,
        traveled:0,heldWithinOneCell:0,adjusted:0,policyCopiedExactDoor:0,gridDriftWhenStaying:0,uniqueRequested:new Set(),rootsOffDoor:new Set()};
      g.calls++;g.requestedOffDoor+=e.requestedOffDoor;g.resolvedOffDoor+=e.resolvedOffDoor;
      g.traveled+=e.length>.4+1e-7;g.heldWithinOneCell+=e.length<=.4+1e-7;
      g.traveledOffDoor+=e.resolvedOffDoor&&e.length>.4+1e-7;g.adjusted+=e.status==="adjusted";
      g.policyCopiedExactDoor+=Object.values(world.doors).some(p=>W.distance(p,e.requested)<1e-6);
      g.gridDriftWhenStaying+=W.distance(e.requested,e.start)<1e-6&&e.length>1e-5;
      g.uniqueRequested.add(e.requested.x.toFixed(3)+","+e.requested.y.toFixed(3));if(e.requestedOffDoor)g.rootsOffDoor.add(data.seed);
      let bad=false;const N=Math.max(1,Math.ceil(e.length/.035));
      for(let i=0;i<=N;i++){const p=W.sample(e.path,i/N);counts.sampledPositions++;
        if(!W.walkable(p,"town"))counts.basePointViolations++;if(!dressing.walkable(p,"town",true))bad=true;}
      if(bad){counts.dressedConflictWalks++;if(e.length>.4+1e-7)counts.dressedConflictMovingWalks++;dressed.push(e.id);
        const a=dressing.near(e.start,"town",true),b=dressing.near(e.resolved,"town",true),alternate=dressing.route(a,b,"town",true);
        const n=Math.max(1,Math.ceil(W.pathLength(alternate)/.025));counts.retargetAttempts++;
        let valid=!!alternate.length&&W.distance(alternate.at(-1),b)<.001;
        for(let i=0;i<=n;i++)valid&&=dressing.walkable(W.sample(alternate,i/n),"town",true);if(valid)counts.retargetClear++;
      }
    }
    const max=Math.max(.05,...events.map(e=>e.length));
    for(let frame=0;frame<framesPerSlot;frame++){
      const elapsed=frame/(framesPerSlot-1)*max,chars=events.map(e=>{const p=W.sample(e.path,e.length?Math.min(1,elapsed/e.length):1);return {name:e.actor,role:e.role,x:p.x,z:p.y,visible:true,moving:e.length>.01&&elapsed<e.length,scene:"town"};});
      for(let i=0;i<chars.length;i++)for(let j=i+1;j<chars.length;j++){const d=Math.hypot(chars[i].x-chars[j].x,chars[i].z-chars[j].z);if(d<.30)close=true;if(frame===framesPerSlot-1&&d<.001)coincident=true;}
      if(folder==="free-953")sample.samples.push({frame:sample.samples.length,actors:chars});
    }
    if(events.length>1)counts.ticksWithMultipleActors++;if(coincident)counts.coincidentEndpointTicks++;if(close){counts.nearActorTicks++;near.push({folder,tick,coincident});}
    sample.slots.push(events.map(e=>({id:e.id,request_sha256:e.raw_sha256})));
    for(const e of events){position[e.role]=e.resolved;previous[e.role]=e;}
  }
  if(folder==="free-953")native=sample;
}
for(const group of Object.values(groups))for(const g of Object.values(group)){g.uniqueRequested=g.uniqueRequested.size;g.rootsOffDoor=[...g.rootsOffDoor];}
const probes=[
 {id:"outside",requested:{x:30,y:30},expected:"outside"},
 {id:"hotel-interior",requested:{x:5.2,y:6},expected:"adjusted"},
 {id:"open-off-door",requested:{x:15,y:14},expected:"reached"}
].map(t=>{const result=resolve({x:6.75,y:8.25},t.requested);assert(result.status===t.expected&&W.walkable(result.resolved,"town"),"Geometry probe failed");return {...t,status:result.status,resolved:result.resolved};});
assert(counts.calls===110&&counts.basePointViolations===0,"Incomplete or invalid cohort");
const report={model:"qwen3:0.6b",runs:roots.length,criteria:{offDoor:"distance > 1.0 from the nearest of five doors",traveled:"route length > 0.4 map metres",nearActor:"pairwise separation <0.30 m at 96 shared-time samples per tick"},
 counts,groups,roots,probes,dressedConflictEventIds:dressed,coincidentOrClose:near};
fs.writeFileSync(path.join(out,"audit.json"),JSON.stringify(report,null,2)+"\n");fs.writeFileSync(path.join(out,"native-samples.json"),JSON.stringify(native)+"\n");
console.log(JSON.stringify(counts));
