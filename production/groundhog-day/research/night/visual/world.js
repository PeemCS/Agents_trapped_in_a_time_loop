"use strict";
window.WinterMap = (() => {
  const places = {
    inn: {label:"Hearthside Hotel", short:"Hotel", x:6.75,y:8.25, scene:"town"},
    diner: {label:"Bea's Diner", short:"Diner", x:7.35,y:15.65, scene:"town"},
    square: {label:"Town Square", short:"Town square", x:12.2,y:11.4, scene:"town"},
    studio: {label:"WRSE Radio", short:"Radio studio", x:14.45,y:7.7, scene:"town"},
    depot: {label:"Intercity Coach", short:"Coach depot", x:17.2,y:13.05, scene:"town"},
    Pittsburgh: {label:"Pittsburgh Terminal", short:"Pittsburgh", x:11.2,y:12.0, scene:"city"}
  };
  const buildings = [
    {id:"inn",x:3.1,y:4.6,w:4.1,d:2.9,h:2.05,kind:"hotel",label:"HEARTHSIDE",wall:"#af7764",side:"#8f685d",roof:"#5c605e"},
    {id:"diner",x:4.65,y:12.15,w:3.35,d:2.85,h:1.25,kind:"diner",label:"BEA’S DINER",wall:"#c6b49a",side:"#8eabaa",roof:"#6e8580"},
    {id:"studio",x:12.1,y:4.6,w:3.55,d:2.35,h:1.85,kind:"radio",label:"WRSE  •  AM",wall:"#b2a78f",side:"#939689",roof:"#5d7473"},
    {id:"depot",x:16.15,y:9.7,w:2.85,d:2.6,h:1.42,kind:"depot",label:"COACH",wall:"#a6b09a",side:"#818f89",roof:"#566b65"},
    {x:1.8,y:9.55,w:2.5,d:2.05,h:1.15,kind:"house",wall:"#aaa48f",side:"#8d9685",roof:"#8a7366"},
    {x:7.7,y:1.2,w:2.6,d:2.2,h:1.4,kind:"house",wall:"#a0abad",side:"#81959a",roof:"#636e78"},
    {x:13.7,y:0.8,w:2.4,d:1.9,h:1.48,kind:"house",wall:"#bbaa98",side:"#96978c",roof:"#6e625c"},
    {x:12.2,y:16.4,w:3.2,d:2.2,h:1.3,kind:"shop",label:"BOOKS",wall:"#bea487",side:"#9d8f7e",roof:"#798482"},
    {x:17.0,y:17.25,w:2.7,d:2.1,h:1.33,kind:"house",wall:"#b7a5a4",side:"#9c9298",roof:"#716773"},
    {x:19.0,y:3.8,w:2,d:2,h:1.18,kind:"house",wall:"#a3af9a",side:"#8b9989",roof:"#757e73"}
  ];
  const cityBuildings = [
    {x:6.0,y:5.25,w:6.9,d:4.0,h:3.25,kind:"terminal",label:"PITTSBURGH",wall:"#9fa8ab",side:"#778c94",roof:"#61747a"},
    {x:1.3,y:1,w:2.1,d:3.2,h:5.4,kind:"tower",wall:"#a19a8e",side:"#7a807f",roof:"#718184"},
    {x:4.7,y:0.2,w:2.4,d:2.3,h:4.1,kind:"tower",wall:"#a9ada1",side:"#8c9891",roof:"#748780"},
    {x:9.4,y:0.7,w:2.5,d:2.6,h:5.9,kind:"tower",wall:"#a7a4a0",side:"#868e91",roof:"#667882"},
    {x:14.2,y:1.8,w:2.5,d:2.55,h:4.3,kind:"tower",wall:"#a7aaa5",side:"#84938f",roof:"#7b8482"},
    {x:1.9,y:10,w:2.3,d:2.75,h:2.45,kind:"shop",label:"CAFE",wall:"#af9a89",side:"#938e83",roof:"#747c76"},
    {x:16.9,y:7.8,w:2.95,d:2.7,h:2.65,kind:"shop",label:"PARCELS",wall:"#9eaaa7",side:"#7f918e",roof:"#697b79"}
  ];
  const roads = {
    town: [
      [[-3,10.35],[25,10.35],1.78],
      [[9.45,-3],[9.45,24],1.65],
      [[1.5,16.7],[23.5,16.7],1.5],
      [[18.4,12.9],[18.4,22.5],1.3],
      [[19.75,-3],[19.75,10.35],1.25]
    ],
    city: [
      [[-4,12.0],[25,12.0],2.2], [[14.5,-3],[14.5,24],2.05], [[4.7,-3],[4.7,22],1.65],
      [[-2,2.8],[25,2.8],1.45], [[-2,16.7],[24,16.7],1.6]
    ]
  };
  const extent={town:{x1:.6,x2:21.25,y1:.45,y2:19.75},city:{x1:1.0,x2:21,y1:1.0,y2:18.4}};
  function pt(x,y){return {x,y};}
  function distance(a,b){return Math.hypot(a.x-b.x,a.y-b.y);}
  function mix(a,b,f){return {x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f};}
  function iso(a,z=0){return {x:(a.x-a.y)*37, y:(a.x+a.y)*18-z*34};}
  function uniso(x,y){return {x:(x/37+y/18)/2,y:(y/18-x/37)/2};}
  function inside(p,b,m=0){return p.x > b.x-m && p.x < b.x+b.w+m && p.y > b.y-m && p.y < b.y+b.d+m;}
  const obstacles={
    town:[...buildings.map(b=>({...b,margin:.12})),{x:11.4,y:11.95,w:1.6,d:1.5,margin:.05}],
    city:cityBuildings.map(b=>({...b,margin:.12}))
  };
  function walkable(p,scene){
    const b=extent[scene];
    if(!b || p.x<b.x1 || p.x>b.x2 || p.y<b.y1 || p.y>b.y2)return false;
    return !obstacles[scene].some(b=>inside(p,b,b.margin));
  }
  // The same navigation predicate governs free movement and recorded routes.
  const step=.4,dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,1],[1,-1],[-1,-1]];
  function gridKey(x,y){return x+128*y;}
  function nearNode(p,scene){
    const x=Math.round(p.x/step),y=Math.round(p.y/step);let best=null,bestD=Infinity;
    for(let r=0;r<14&&!best;r++)for(let i=-r;i<=r;i++)for(let j=-r;j<=r;j++){
      if(Math.max(Math.abs(i),Math.abs(j))!==r)continue;
      const a=pt((x+i)*step,(y+j)*step),d=distance(p,a);if(d<bestD&&walkable(a,scene)&&(!walkable(p,scene)||clear(p,a,scene))){best=[x+i,y+j];bestD=d;}
    }
    return best;
  }
  function clear(a,b,scene){
    if(!walkable(a,scene)||!walkable(b,scene))return false;
    // Intersect the entire motion segment with each inflated footprint. A sample-based
    // check can miss a sliver of a corner, producing small but visible sidewalk cuts.
    const dx=b.x-a.x,dy=b.y-a.y;
    for(const obstacle of obstacles[scene]){
      const m=obstacle.margin-1e-9;
      const left=obstacle.x-m,right=obstacle.x+obstacle.w+m,top=obstacle.y-m,bottom=obstacle.y+obstacle.d+m;
      if((!dx&&(a.x<left||a.x>right))||(!dy&&(a.y<top||a.y>bottom)))continue;
      const ax=dx?(left-a.x)/dx:-Infinity,bx=dx?(right-a.x)/dx:Infinity;
      const ay=dy?(top-a.y)/dy:-Infinity,by=dy?(bottom-a.y)/dy:Infinity;
      const enter=Math.max(0,Math.min(ax,bx),Math.min(ay,by));
      const leave=Math.min(1,Math.max(ax,bx),Math.max(ay,by));
      if(enter<=leave)return false;
    }
    return true;
  }
  class Heap{
    constructor(){this.a=[];}
    push(e){const h=this.a;let i=h.length;h.push(e);while(i){const p=(i-1)>>1;if(h[p].f<=e.f)break;h[i]=h[p];i=p;}h[i]=e;}
    pop(){const h=this.a;if(h.length===1)return h.pop();const x=h[0],last=h.pop();let i=0;
      while(2*i+1<h.length){let c=2*i+1;if(c+1<h.length&&h[c+1].f<h[c].f)c++;if(last.f<=h[c].f)break;h[i]=h[c];i=c;}h[i]=last;return x;}
  }
  function route(a,b,scene){
    const start=nearNode(a,scene),goal=nearNode(b,scene);
    if(!start||!goal)return [a];
    const end=walkable(b,scene)?pt(b.x,b.y):pt(goal[0]*step,goal[1]*step);
    if(clear(a,end,scene))return [pt(a.x,a.y),end];
    const [gx,gy]=goal,[sx,sy]=start, sk=gridKey(sx,sy),gk=gridKey(gx,gy);
    const heap=new Heap(),scores=new Map([[sk,0]]),parents=new Map();
    heap.push({x:sx,y:sy,k:sk,g:0,f:0});
    while(heap.a.length){
      const n=heap.pop();if(n.g!==scores.get(n.k))continue;if(n.k===gk)break;
      for(const [dx,dy] of dirs){
        const x=n.x+dx,y=n.y+dy,k=gridKey(x,y),p=pt(x*step,y*step),ng=n.g+Math.hypot(dx,dy);
        if(ng>=(scores.get(k)??Infinity)||!walkable(p,scene))continue;
        if(dx&&dy&&(!walkable(pt(n.x*step,p.y),scene)||!walkable(pt(p.x,n.y*step),scene)||!clear(pt(n.x*step,n.y*step),p,scene)))continue;
        scores.set(k,ng);parents.set(k,n.k);heap.push({x,y,k,g:ng,f:ng+Math.hypot(x-gx,y-gy)});
      }
    }
    if(!scores.has(gk))return [pt(a.x,a.y)];
    let k=gk;const nodes=[end];
    while(k!==sk){nodes.push(pt((k%128)*step,Math.floor(k/128)*step));k=parents.get(k);}
    nodes.push(pt(sx*step,sy*step),pt(a.x,a.y));nodes.reverse();
    const compact=[nodes[0]];let i=0;
    while(i<nodes.length-1){let j=i+1;while(j+1<nodes.length&&clear(nodes[i],nodes[j+1],scene))j++;compact.push(nodes[j]);i=j;}
    return compact;
  }
  function pathLength(path){let d=0;for(let i=1;i<path.length;i++)d+=distance(path[i-1],path[i]);return d;}
  function sample(path,f){
    if(path.length===1)return {...path[0],dx:0,dy:0};
    let left=pathLength(path)*Math.max(0,Math.min(1,f));
    for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],len=distance(a,b);if(left<=len||i===path.length-1)return {...mix(a,b,len?Math.min(1,left/len):1),dx:b.x-a.x,dy:b.y-a.y};left-=len;}
  }
  function nearestPlace(p,scene){
    let best=null,d=Infinity;
    for(const [id,v] of Object.entries(places)){if(v.scene!==scene)continue;const n=distance(p,v);if(n<d){d=n;best=id;}}
    return {id:best,distance:d};
  }
  return {places,buildings,cityBuildings,roads,extent,pt,distance,mix,iso,uniso,walkable,route,sample,pathLength,nearestPlace};
})();
