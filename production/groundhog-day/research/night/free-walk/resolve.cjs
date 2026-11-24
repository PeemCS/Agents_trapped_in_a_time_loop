"use strict";
const fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
const context={window:{}};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,"../visual/world.js"),"utf8"),context);
const W=context.window.WinterMap;
const bounds=W.extent.town,doors=Object.fromEntries(Object.entries(W.places).filter(([,v])=>v.scene==="town").map(([k,v])=>[k,{x:v.x,y:v.y,label:v.label}]));
// Same obstacle rectangles that define the existing town's walkability.
const blocks=W.buildings.map((b,i)=>({id:b.id||b.label||"building_"+i,x:b.x,y:b.y,w:b.w,d:b.d,margin:.12}));
blocks.push({id:"bandstand",x:11.4,y:11.95,w:1.6,d:1.5,margin:.05});
const world={bounds,doors,blocks};
function collides(a,b,r){
  let enter=0,leave=1;
  for(const [k,length] of [["x","w"],["y","d"]]){
    const min=r[k]-r.margin+1e-8,max=r[k]+r[length]+r.margin-1e-8,v=b[k]-a[k];
    if(!v){if(a[k]<=min||a[k]>=max)return false;continue;}
    const t0=(min-a[k])/v,t1=(max-a[k])/v;enter=Math.max(enter,Math.min(t0,t1));leave=Math.min(leave,Math.max(t0,t1));
    if(enter>=leave)return false;
  }return enter<leave;
}
function resolve(start,requested){
  if(!W.walkable(start,"town"))throw Error("Bad origin");
  const valid=Number.isFinite(requested.x)&&Number.isFinite(requested.y);
  const q={x:Math.round(requested.x/.4)*.4,y:Math.round(requested.y/.4)*.4};
  const limits=valid&&requested.x>=bounds.x1&&requested.x<=bounds.x2&&requested.y>=bounds.y1&&requested.y<=bounds.y2;
  let route=[{...start}],status="outside",reason="Requested point is outside the town limits.";
  if(limits){
    route=W.route(start,q,"town");const end=route.at(-1),adjust=W.distance(q,end);
    if(!W.walkable(q,"town")){status="adjusted";const block=blocks.find(r=>collides(q,q,r));reason="Closest reachable point beside "+(block?.id||"map boundary")+".";}
    else if(adjust>1e-6){status="blocked";reason="No traversable route to the requested grid point.";}
    else{status="reached";reason="Reached the chosen grid point.";}
  }
  const end=route.at(-1),length=W.pathLength(route);
  for(let i=0;i<route.length;i++){
    if(!W.walkable(route[i],"town"))throw Error("Route point intersects the town");
    if(i&&blocks.some(o=>collides(route[i-1],route[i],o)))throw Error("Segment intersects an inflated obstacle");
  }
  const near=W.nearestPlace(end,"town"),ask=W.nearestPlace(requested,"town");
  return {start,requested,quantized:q,resolved:end,status,reason,path:route,length,
    requestedDoorDistance:ask.distance,resolvedDoorDistance:near.distance,nearDoor:near.id,
    gridError:W.distance(requested,q),adjustment:W.distance(q,end),requestedOffDoor:ask.distance>1,resolvedOffDoor:near.distance>1,
    yUp:route.map(p=>[p.x,0,p.y])};
}
if(require.main===module){
  const read=require("node:readline").createInterface({input:process.stdin});
  read.on("line",line=>{try{const a=JSON.parse(line);process.stdout.write(JSON.stringify(a.world?world:resolve(a.start,a.requested))+"\n");}
    catch(e){process.stdout.write(JSON.stringify({error:String(e)})+"\n");}});
}
module.exports={resolve,world,W,collides};
