"use strict";
/* Static-art clearance corrections for the dressed view. Recorded people and coach never move here. */
window.TownStagePlacement = (() => {
  const edits={
    town:{8:{dz:.64,prim:"house8"}},
    city:{5:{dz:-2.10,prim:"shop5"}}
  };
  const propEdits={town:[],city:[{prim:"Payphone",dz:-.32},{prim:"PayphoneSign",dz:-.32}]};
  const lamps={town:[[4.84,8.62],[10.55,8.4],[7,13.45],[10.7,11.8],[14.25,8.85],[16.11,13.37],[13.25,14.1],[5.9,15.7]],
    city:[[6.2,10.2],[12.7,10.4],[9.6,13.6],[15.8,12.9]]};
  const benches={town:[[11.22,11.82],[13.64,12.36],[16,13]],city:[[10.5,10.33],[8.4,10.33],[12.35,11.55]]};
  const spruces={town:[[2.1,7.1,2.8],[1.95,15.5,2.3],[10.9,3.4,2.6],[15.7,3.2,1.9],[20.9,14.55,1.7],[5.5,18.3,2.8]],city:[]};
  const styleRules=key=>[...Object.values(edits[key]),...propEdits[key]];
  function canonical(key){return key==="town"?WinterMap.buildings:WinterMap.cityBuildings;}
  function buildings(key,dressed){
    return canonical(key).map((b,i)=>dressed&&edits[key]?.[i]?{...b,y:b.y+edits[key][i].dz}:b);
  }
  function shiftForRow(key,path){
    const group=path.split("/")[1];
    return styleRules(key).find(p=>p.prim===group)?.dz||0;
  }
  const margin=.12;
  function rectangle(b,m=margin){return {x0:b.x-m,x1:b.x+b.w+m,z0:b.y-m,z1:b.y+b.d+m};}
  const occupied={};
  for(const key of ["town","city"]){
    occupied[key]=buildings(key,true).map(b=>rectangle(b));
    for(const o of coachObstacles(key,true).slice(canonical(key).length)){
      if(o.id.endsWith("/Bandstand"))continue;
      occupied[key].push(rectangle({x:o.x-o.hx,y:o.z-o.hz,w:2*o.hx,d:2*o.hz},.055));
    }
    if(key==="town")occupied[key].push(rectangle({x:11.4,y:11.95,w:1.6,d:1.5},.05));
  }
  function inBounds(p,key){
    const b=WinterMap.extent[key];return p.x>=b.x1&&p.x<=b.x2&&p.y>=b.y1&&p.y<=b.y2;
  }
  const inside=(p,b)=>p.x>b.x0&&p.x<b.x1&&p.y>b.z0&&p.y<b.z1;
  function walkable(p,key,dressed){
    if(!dressed)return WinterMap.walkable(p,key);
    return inBounds(p,key)&&!occupied[key].some(b=>inside(p,b));
  }
  function clear(a,b,key){
    if(!walkable(a,key,true)||!walkable(b,key,true))return false;
    const dx=b.x-a.x,dz=b.y-a.y;
    for(const o of occupied[key]){
      if((!dx&&(a.x<=o.x0||a.x>=o.x1))||(!dz&&(a.y<=o.z0||a.y>=o.z1)))continue;
      const tx0=dx?(o.x0-a.x)/dx:-Infinity,tx1=dx?(o.x1-a.x)/dx:Infinity;
      const tz0=dz?(o.z0-a.y)/dz:-Infinity,tz1=dz?(o.z1-a.y)/dz:Infinity;
      const enter=Math.max(0,Math.min(tx0,tx1),Math.min(tz0,tz1));
      const leave=Math.min(1,Math.max(tx0,tx1),Math.max(tz0,tz1));
      if(enter<leave-1e-7)return false;
    }
    return true;
  }
  function near(p,key,dressed){
    if(walkable(p,key,dressed))return p;
    const rects=dressed?occupied[key]:canonical(key).map(b=>rectangle(b));
    const choices=[];
    for(const o of rects){
      const x=Math.max(o.x0,Math.min(o.x1,p.x)),y=Math.max(o.z0,Math.min(o.z1,p.y));
      choices.push({x:o.x0-.025,y},{x:o.x1+.025,y},{x,y:o.z0-.025},{x,y:o.z1+.025});
    }
    return choices.filter(q=>walkable(q,key,dressed)).sort((q,r)=>WinterMap.distance(q,p)-WinterMap.distance(r,p))[0]||p;
  }
  function route(a,b,key,dressed){
    const W=WinterMap;
    if(!dressed)return W.route(a,b,key);
    const end=near(b,key,true),old=W.route(a,end,key);
    if(W.distance(old.at(-1),end)<.01&&old.slice(1).every((pt,i)=>clear(old[i],pt,key)))return old;
    if(clear(a,end,key))return [a,end];
    // The reference A* usually applies unchanged. For the two corrected parcels,
    // solve the tiny rectilinear visibility graph against the dressed footprints.
    const points=[a,end],e=.025;
    for(const o of occupied[key])for(const x of [o.x0-e,o.x1+e])for(const y of [o.z0-e,o.z1+e]){
      const p={x,y};if(walkable(p,key,true))points.push(p);
    }
    const cost=points.map(()=>Infinity),parent=points.map(()=>-1),open=new Set(points.map((_,i)=>i));cost[0]=0;
    while(open.size){
      let i=-1;for(const j of open)if(i<0||cost[j]<cost[i])i=j;
      if(!Number.isFinite(cost[i])||i===1)break;open.delete(i);
      for(const j of open){
        const newCost=cost[i]+W.distance(points[i],points[j]);
        if(newCost<cost[j]&&clear(points[i],points[j],key)){cost[j]=newCost;parent[j]=i;}
      }
    }
    if(!Number.isFinite(cost[1]))return [a];
    const result=[];for(let i=1;i>=0;i=parent[i])result.push(points[i]);return result.reverse();
  }
  function coachObstacles(key,dressed){
    const list=buildings(key,dressed).map((b,i)=>({id:key+"/"+(b.id||b.kind+i),x:b.x+b.w/2,z:b.y+b.d/2,hx:b.w/2,hz:b.d/2}));
    for(const r of TUESDAY_STAGE.sets[key].shapes){
      const tag=r.path.split("/").at(-1);
      if(!/^Spruce[0-9]+$|^Payphone$|^Bandstand$/.test(tag))continue;
      list.push({id:key+"/"+tag,x:r.position[0],z:r.position[2]+(dressed?shiftForRow(key,r.path):0),hx:r.size[0]/2,hz:r.size[2]/2});
    }
    if(dressed){
      for(const [i,[x,z]] of lamps[key].entries())list.push({id:key+"/lamp"+i,x,z,hx:.09,hz:.09});
      for(const [i,[x,z]] of benches[key].entries())list.push({id:key+"/bench"+i,x,z:z+.072,hx:.43,hz:.12});
      for(const [i,[x,z,h]] of spruces[key].entries())list.push({id:key+"/dressed-pine"+i,x,z,hx:h*.325,hz:h*.325});
    }
    return list;
  }
  // Each coach leg is a line segment with fixed yaw. Project the oriented
  // vehicle's half-extents onto the set axes and intersect its continuous
  // centerline with each inflated footprint. The envelope is conservative
  // on the first, slightly diagonal depot segment.
  function sweptCoach(dressed){
    const intersections=[];
    for(const [key,route] of [["town",WinterReplay.townRide],["city",WinterReplay.cityRide]]){
      const obstacles=coachObstacles(key,dressed);
      for(let i=1;i<route.length;i++){
        const a=route[i-1],b=route[i],dx=b.x-a.x,dz=b.y-a.y,len=Math.hypot(dx,dz);
        const hx=.97*Math.abs(dx/len)+.356*Math.abs(dz/len),hz=.97*Math.abs(dz/len)+.356*Math.abs(dx/len);
        for(const o of obstacles){
          const loX=o.x-o.hx-hx,hiX=o.x+o.hx+hx,loZ=o.z-o.hz-hz,hiZ=o.z+o.hz+hz;
          if((!dx&&(a.x<=loX||a.x>=hiX))||(!dz&&(a.y<=loZ||a.y>=hiZ)))continue;
          const x0=dx?(loX-a.x)/dx:-Infinity,x1=dx?(hiX-a.x)/dx:Infinity;
          const z0=dz?(loZ-a.y)/dz:-Infinity,z1=dz?(hiZ-a.y)/dz:Infinity;
          if(Math.max(0,Math.min(x0,x1),Math.min(z0,z1))<Math.min(1,Math.max(x0,x1),Math.max(z0,z1)))
            intersections.push({obstacle:o.id,leg:i-1});
        }
      }
    }
    return intersections;
  }
  return {edits,styleRules,lamps,benches,spruces,coachObstacles,sweptCoach,canonical,buildings,shiftForRow,walkable,near,route};
})();
