"use strict";
// Counterfactual movement policy. Source proposals and raw model files are read-only.
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const {W,world,collides}=require("./resolve.cjs"),ctx={window:{},WinterMap:W};vm.createContext(ctx);
for(const file of ["geometry.js","placement.js"]){vm.runInContext(fs.readFileSync(path.join(__dirname,"../stage3d/viewer",file),"utf8"),ctx);ctx.TUESDAY_STAGE=ctx.window.TUESDAY_STAGE;}
const P=ctx.window.TownStagePlacement,step=.4,clearance=.52;
const rectangles=[...world.blocks];
const obs=P.coachObstacles("town",true),buildingCount=P.buildings("town",true).length;
for(const [i,o] of obs.entries()){
  if(o.id.endsWith("/Bandstand"))continue;
  rectangles.push({x:o.x-o.hx,y:o.z-o.hz,w:2*o.hx,d:2*o.hz,margin:i<buildingCount?.12:.055});
}
function legal(p){return W.walkable(p,"town")&&P.walkable(p,"town",true);}
function staticClear(a,b){return legal(a)&&legal(b)&&!rectangles.some(r=>collides(a,b,r));}
function gap(a,b,p){
  const dx=b.x-a.x,dy=b.y-a.y,den=dx*dx+dy*dy;
  const f=den?Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/den)):0;
  return Math.hypot(a.x+dx*f-p.x,a.y+dy*f-p.y);
}
function dynamicClear(a,b,still){return still.every(p=>gap(a,b,p)>=clearance-1e-9);}
const nodes=[],index=new Map(),edges=[];
for(let y=0;y<=50;y++)for(let x=0;x<=54;x++){const p={x:x*step,y:y*step};if(legal(p)){index.set(x+":"+y,nodes.length);nodes.push(p);}}
for(const p of nodes){const row=[],gx=Math.round(p.x/step),gy=Math.round(p.y/step);
  for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]){
    const j=index.get((gx+dx)+":"+(gy+dy));if(j!==undefined&&staticClear(p,nodes[j]))row.push([j,step*Math.hypot(dx,dy)]);}
  edges.push(row);}
class Queue{
  constructor(){this.values=[];}
  push(v){const a=this.values;let i=a.length;a.push(v);while(i){const parent=(i-1)>>1;if(a[parent][0]<=v[0])break;a[i]=a[parent];i=parent;}a[i]=v;}
  pop(){const a=this.values,head=a[0],end=a.pop();if(a.length){let i=0;while(i*2+1<a.length){let child=i*2+1;if(child+1<a.length&&a[child+1][0]<a[child][0])child++;if(a[child][0]>=end[0])break;a[i]=a[child];i=child;}a[i]=end;}return head;}
}
function reserve(start,ask,goal,still){
  if(!legal(start)||!dynamicClear(start,start,still))throw Error("Unsafe initial staging");
  if(W.distance(start,ask)<1e-5)return [start];
  if(staticClear(start,goal)&&dynamicClear(start,goal,still))return [start,goal];
  const cost=Array(nodes.length).fill(Infinity),parent=Array(nodes.length).fill(-1),queue=new Queue;
  for(let i=0;i<nodes.length;i++){const p=nodes[i],d=W.distance(p,start);if(d<1.05&&staticClear(start,p)&&dynamicClear(start,p,still)){cost[i]=d;queue.push([d,i]);}}
  while(queue.values.length){
    const [g,i]=queue.pop();if(g!==cost[i])continue;
    for(const [j,weight] of edges[i]){const ng=g+weight;if(ng+1e-7>=cost[j]||!dynamicClear(nodes[i],nodes[j],still))continue;
      cost[j]=ng;parent[j]=i;queue.push([ng,j]);}
  }
  let best=-1,bestRadius=Infinity,bestDistance=Infinity;
  for(let i=0;i<nodes.length;i++){if(!Number.isFinite(cost[i]))continue;const d=W.distance(nodes[i],goal);
    if(d>1.6+1e-7)continue;if(d<bestRadius-1e-7||(Math.abs(d-bestRadius)<1e-7&&cost[i]<bestDistance)){best=i;bestRadius=d;bestDistance=cost[i];}}
  if(best<0)return [start];
  const raw=[];for(let i=best;i!==-1;i=parent[i])raw.push(nodes[i]);raw.push(start);raw.reverse();
  const out=[start];for(let i=0;i<raw.length-1;){let j=i+1;while(j+1<raw.length&&staticClear(raw[i],raw[j+1])&&dynamicClear(raw[i],raw[j+1],still))j++;
    if(W.distance(out.at(-1),raw[j])>1e-8)out.push(raw[j]);i=j;}return out;
}
if(process.argv[2]==="--solve"){
  const input=JSON.parse(fs.readFileSync(0,"utf8")),current={...input.positions},stats={minimumGap:Infinity},rows=Array(input.events.length);let total=0;
  const order=input.events.map((_,i)=>(i+input.tick+input.seed)%input.events.length);
  for(const i of order){const e=input.events[i],start=current[e.role],still=Object.entries(current).filter(([r])=>r!==e.role).map(([,v])=>v);
    const route=reserve(start,e.requested,e.resolved,still),end=route.at(-1),length=W.pathLength(route);
    for(let j=0;j<Math.max(1,route.length-1);j++){const a=route[j],b=route[Math.min(route.length-1,j+1)];
      if(!staticClear(a,b)||!dynamicClear(a,b,still))throw Error("Prospective clearance failed");for(const q of still)stats.minimumGap=Math.min(stats.minimumGap,gap(a,b,q));}
    rows[i]={path:route,resolved:end,length,from:total,to:total+length};total+=length;current[e.role]=end;}
  for(const row of rows){row.from=total?row.from/total:0;row.to=total?row.to/total:1;}
  process.stdout.write(JSON.stringify({rows,...stats}));return;
}
const overlay={clearanceMetres:clearance,runs:{}};
const report={runs:0,proposals:0,originalTargetsReached:0,nearbyTargets:0,held:0,exactStartRequestsPreserved:0,continuousSegments:0,
  maxEndDeviationFromRecorded:0,minimumCrewSeparation:Infinity,staticViolations:0,pairViolations:0,changedEndpoints:0};
for(const folder of fs.readdirSync(path.join(__dirname,"runs")).sort()){
  const take=JSON.parse(fs.readFileSync(path.join(__dirname,"runs",folder,"take.json"))),current={...take.initial},ticks=[];report.runs++;
  for(const [tick,events] of take.ticks.entries()){
    const order=events.map((_,i)=>(i+tick+take.seed)%events.length),rows=Array(events.length);let total=0;
    for(const i of order){
      const e=events[i],start=current[e.role],still=Object.entries(current).filter(([r])=>r!==e.role).map(([,p])=>p);
      const route=reserve(start,e.requested,e.resolved,still),end=route.at(-1),length=W.pathLength(route),deviation=W.distance(end,e.resolved);
      for(let j=0;j<Math.max(1,route.length-1);j++){
        const a=route[j],b=route[Math.min(route.length-1,j+1)];report.continuousSegments++;
        if(!staticClear(a,b))report.staticViolations++;
        for(const p of still){const d=gap(a,b,p);report.minimumCrewSeparation=Math.min(d,report.minimumCrewSeparation);if(d<clearance-1e-8)report.pairViolations++;}
      }
      let reason=deviation<1e-6?"The reserved path reaches the recorded endpoint.":"A nearby available point clears the other performers and the dressed set.";
      if(W.distance(e.requested,start)<1e-5){reason="The actor requested their present position. The reservation keeps it exact.";report.exactStartRequestsPreserved++;}
      if(!length&&deviation>.4)reason="The reservation holds this actor until the next decision.";
      rows[i]={id:e.id,start,resolved:end,path:route,length,reason,from:total,to:total+length,sourceResolved:e.resolved};
      total+=length;current[e.role]=end;report.proposals++;
      if(deviation<1e-6)report.originalTargetsReached++;else if(deviation<=1.6+1e-6)report.nearbyTargets++;else report.held++;
      if(deviation>1e-6)report.changedEndpoints++;report.maxEndDeviationFromRecorded=Math.max(deviation,report.maxEndDeviationFromRecorded);
    }
    for(const r of rows){r.from=total?r.from/total:0;r.to=total?r.to/total:1;}
    ticks.push(rows);
  }
  overlay.runs[folder]=ticks;
}
if(report.staticViolations||report.pairViolations)throw Error("Reservation collision");
fs.writeFileSync(path.join(__dirname,"reserved.js"),"window.FreeWalkReservations = "+JSON.stringify(overlay)+";\n");
fs.writeFileSync(path.join(__dirname,"evidence/reservations.json"),JSON.stringify(report,null,2)+"\n");
console.log(report);
