"use strict";
/* Renderer-only wardrobe, facade surfaces and props. Their parent transforms belong to the stage. */
window.TownStageDressing = (() => {
  const facadeCache=new Map();
  function rng(seed){return()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};}
  function rgb(hex){return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));}
  function tint(c,delta){return "rgb("+c.map(v=>Math.max(0,Math.min(255,Math.round(v+delta)))).join(",")+")";}
  function facadeMaterial(T,b){
    const brick=["hotel","terminal","shop","tower"].includes(b.kind);
    const key=[b.wall,brick,b.w,b.h].join("/");
    if(facadeCache.has(key))return facadeCache.get(key);
    const random=rng(157+b.w*987|0),c=document.createElement("canvas");c.width=384;c.height=256;
    const ctx=c.getContext("2d"),base=rgb(b.wall);
    ctx.fillStyle=tint(base,-4);ctx.fillRect(0,0,c.width,c.height);
    if(brick){
      const rows=Math.round(b.h/(b.kind==="tower"?.27:.16)),bh=c.height/rows,bw=Math.round(c.width/(b.w/.37));
      for(let row=0;row<rows;row++){
        for(let i=-1;i<=c.width/bw+1;i++){
          const x=(i+(row%2)*.5)*bw,y=row*bh;
          ctx.fillStyle=tint(base,random()*15-7);ctx.fillRect(x+1.25,y+1.1,bw-2.1,bh-2);
          ctx.fillStyle="rgba(242,221,179,.11)";ctx.fillRect(x+1.5,y+1.2,bw-2.4,.85);
        }
      }
    }else{
      const rows=Math.round(b.h/.14),step=c.height/rows;
      for(let i=0;i<rows;i++){
        const y=i*step;ctx.fillStyle=tint(base,-1+random()*7);ctx.fillRect(0,y,c.width,step);
        ctx.fillStyle="rgba(65,79,71,.16)";ctx.fillRect(0,y+step-1.5,c.width,1.5);
        ctx.fillStyle="rgba(255,240,202,.22)";ctx.fillRect(0,y,c.width,1.1);
        const x=(i%3)*111+29;ctx.fillStyle="rgba(70,82,69,.14)";ctx.fillRect(x,y,1,step);
      }
    }
    for(let j=0;j<2600;j++){
      const d=random()*1.1+.35;ctx.fillStyle=random()>.5?"rgba(255,245,221,.05)":"rgba(44,55,48,.045)";
      ctx.fillRect(random()*c.width,random()*c.height,d,d);
    }
    const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;tex.anisotropy=4;
    const mat=new T.MeshStandardMaterial({map:tex,roughness:.91});facadeCache.set(key,mat);return mat;
  }
  function groundDress({T,key,group,shape,cube}){
    const r=rng(key==="town"?212:295),geom=new T.PlaneGeometry(1,1);
    function finish(c){
      const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;tex.anisotropy=4;
      return tex;
    }
    const sc=document.createElement("canvas");sc.width=sc.height=320;
    const ctx=sc.getContext("2d");ctx.fillStyle="#e1e5df";ctx.fillRect(0,0,320,320);
    for(let i=0;i<110;i++){
      const x=r()*320,y=r()*320,rad=2+r()*27,g=ctx.createRadialGradient(x,y,0,x,y,rad);
      g.addColorStop(0,r()<.5?"rgba(133,162,169,.10)":"rgba(245,237,213,.18)");g.addColorStop(1,"rgba(222,229,221,0)");
      ctx.fillStyle=g;ctx.fillRect(x-rad,y-rad,rad*2,rad*2);
    }
    for(let i=0;i<3000;i++){ctx.fillStyle=r()>.5?"rgba(102,127,136,.08)":"rgba(255,254,237,.18)";ctx.fillRect(r()*320,r()*320,.6+r(),.6+r());}
    const flurry=finish(sc);flurry.wrapS=flurry.wrapT=T.RepeatWrapping;flurry.repeat.set(4.3,4.3);
    const snow=new T.Mesh(geom,new T.MeshStandardMaterial({map:flurry,roughness:1,polygonOffset:true,polygonOffsetFactor:-1}));
    snow.name="Snow surface";snow.rotation.x=-Math.PI/2;snow.scale.set(30,31,1);snow.position.set(10,-.002,10);snow.receiveShadow=true;group.add(snow);
    for(const [i,[a,b,width]] of WinterMap.roads[key].entries()){
      const c=document.createElement("canvas");c.width=768;c.height=128;const x=c.getContext("2d");
      x.fillStyle="#899997";x.fillRect(0,0,768,128);
      for(let n=0;n<10500;n++){
        x.fillStyle=r()<.55?"rgba(244,242,222,.16)":"rgba(63,84,85,.13)";
        x.fillRect(r()*768,r()*128,r()*1.8+.4,r()+.35);
      }
      for(const v of [21,41,86,107]){
        x.strokeStyle="rgba(65,86,86,.14)";x.lineWidth=4; x.beginPath();
        for(let d=0;d<=768;d+=12){const vy=v+Math.sin(d/102)*1.4;d?x.lineTo(d,vy):x.moveTo(d,vy);}x.stroke();
      }
      for(const bottom of [false,true]){
        x.fillStyle="rgba(205,213,201,.58)";x.beginPath();const edge=bottom?128:0,sign=bottom?-1:1;
        x.moveTo(0,edge);for(let u=0;u<=768;u+=8)x.lineTo(u,edge+sign*(2.1+r()*3.4+1.3*Math.sin(u*.03)));x.lineTo(768,edge);x.fill();
      }
      const map=finish(c),alongX=Math.abs(b[0]-a[0])>Math.abs(b[1]-a[1]),len=Math.hypot(b[0]-a[0],b[1]-a[1]);
      const surface=new T.Mesh(geom,new T.MeshStandardMaterial({map,roughness:.96}));
      surface.name="Road surface "+i;surface.rotation.order="YXZ";surface.rotation.set(-Math.PI/2,alongX?0:Math.PI/2,0);
      surface.scale.set(len,width,1);surface.position.set((a[0]+b[0])/2,.0157+i*.0006,(a[1]+b[1])/2);surface.receiveShadow=true;group.add(surface);
    }
    const poles=key==="town"?[[-2.4,9.06],[3.82,9.06],[14.8,9.06],[22.25,9.06]]:
      [[4.0,10.47],[11.9,10.47],[19.9,10.47]];
    const top=key==="town"?2.9:3.15;
    for(const [x,z] of poles){
      shape("Cylinder",[x,top/2,z],[.082,top,.082],"#786c58");
      cube([x,top-.18,z],[.071,.075,.57],"#8b7962");
      for(const d of [-.24,.24])shape("Cylinder",[x,top-.092,z+d],[.049,.077,.049],"#c4c6b2");
    }
    function cable(a,b){
      const p=new T.Vector3(...a),v=new T.Vector3(...b).sub(p),q=new T.Quaternion().setFromUnitVectors(new T.Vector3(0,1,0),v.clone().normalize());
      const e=new T.Euler().setFromQuaternion(q);p.addScaledVector(v,.5);
      shape("Cylinder",p.toArray(),[.012,v.length(),.012],"#5b6259",[e.x,e.y,e.z]);
    }
    for(let i=1;i<poles.length;i++)for(const dz of [-.24,.24]){
      const a=poles[i-1],b=poles[i];let last=[a[0],top-.05,a[1]+dz];
      for(let j=1;j<=7;j++){const f=j/7,at=[a[0]+(b[0]-a[0])*f,top-.05-.19*Math.sin(Math.PI*f),a[1]+dz];cable(last,at);last=at;}
    }
    if(key==="town")for(const [x,z,length] of [[2.2,12.65,1.7],[13.5,3.22,2.3],[3.05,3.93,1.45]]){
      for(let j=0;j<=length*4;j++){const xx=x+j*.25;cube([xx,.28,z],[.072,.56,.085],"#bcb7a3");}
      for(const y of [.18,.39])cube([x+length/2,y,z+.036],[length,.038,.065],"#b8ae98");
    }
  }
  function contact(T,parent){
    const c=document.createElement("canvas");c.width=c.height=64;
    const x=c.getContext("2d"),g=x.createRadialGradient(32,32,0,32,32,31);
    g.addColorStop(0,"rgba(45,55,52,.42)");g.addColorStop(.48,"rgba(59,71,65,.23)");g.addColorStop(1,"rgba(68,75,70,0)");
    x.fillStyle=g;x.fillRect(0,0,64,64);const tx=new T.CanvasTexture(c);tx.colorSpace=T.SRGBColorSpace;
    const plane=new T.Mesh(new T.PlaneGeometry(.72,.49),new T.MeshBasicMaterial({map:tx,transparent:true,depthWrite:false,toneMapped:false}));
    plane.rotation.x=-Math.PI/2;plane.position.y=.028;plane.renderOrder=2;parent.add(plane);
  }
  function facades(env){
    const {T,group,boxes,rows,cube,shape,sign,key}=env,base=new T.PlaneGeometry(1,1),matrix=new T.Object3D();
    for(const b of boxes){
      const mat=facadeMaterial(T,b),mesh=new T.InstancedMesh(base,mat,4);
      const cx=b.x+b.w*.5,cz=b.y+b.d*.5,y=b.h*.5,front=b.y+b.d;
      const sides=[[cx,y,front+.003,b.w,0],[cx,y,b.y-.003,b.w,Math.PI],
        [b.x+b.w+.003,y,cz,b.d,Math.PI/2],[b.x-.003,y,cz,b.d,-Math.PI/2]];
      sides.forEach(([x,y,z,width,rot],i)=>{
        matrix.position.set(x,y,z);matrix.scale.set(width,b.h,1);matrix.rotation.set(0,rot,0);matrix.updateMatrix();mesh.setMatrixAt(i,matrix.matrix);
      });
      mesh.receiveShadow=true;mesh.name="Facade surface";group.add(mesh);
      const trim=b.kind==="hotel"?"#cdba99":b.kind==="diner"?"#c9cbb7":"#bec0ae";
      for(const x of [b.x+.054,b.x+b.w-.054])cube([x,b.h*.49,front+.017],[.095,b.h*.98,.052],trim);
      cube([cx,.12,front+.035],[b.w+.035,.16,.066],"#a3a597");
      cube([cx,b.h-.095,front+.030],[b.w+.09,.075,.078],trim);
      const doorZ=front+.048;
      cube([cx,.48,doorZ],[.32,.78,.045],b.kind==="hotel"?"#48685a":"#55726b");
      cube([cx,.65,doorZ+.027],[.22,.29,.025],"#84978e");
      cube([cx,.255,doorZ+.027],[.215,.19,.025],"#688074");
      cube([cx,.432,doorZ+.045],[.248,.028,.033],"#94a593");
      shape("Sphere",[cx+.115,.443,doorZ+.065],[.039,.039,.041],"#ddb77b");
      cube([cx-.235,.48,front+.045],[.045,.95,.068],trim);
      cube([cx+.235,.48,front+.045],[.045,.95,.068],trim);
      cube([cx,.94,front+.044],[.505,.061,.071],trim);
      if(b.kind==="hotel"){
        for(const dx of [-b.w*.48,b.w*.48])cube([cx+dx,b.h+.16,cz],[.088,.17,b.d],"#c5c8b9");
        cube([cx,b.h+.15,b.y+.04],[b.w,.14,.09],"#c4c6b8");
        cube([cx,b.h+.18,b.y+b.d-.02],[b.w,.17,.095],"#c4c6b8");
        cube([cx,b.h+.27,b.y+b.d-.02],[b.w+.03,.025,.115],"#e3e6d6");
      }
      if(b.kind==="diner"){
        for(let i=0;i<2;i++){
          const x=b.x+.35+i*(b.w-.69);
          cube([x,.84,front+.38],[.04,.61,.04],"#7f9285");
        }
        cube([cx,.40,front+.056],[b.w-.1,.044,.045],"#ad6855");
      }
    }
    const warm=[];
    for(const row of rows){
      const name=row.path.split("/").at(-1);
      if(!name.includes("Window"))continue;
      const [x,y,z]=row.position,[sx,sy,sz]=row.size,side=name.startsWith("Side"),wide=side?sz:sx;
      const [xdir,zdir]=side?[0,1]:[1,0],out=side?[1,0]:[0,1];
      const px=x+out[0]*.036,pz=z+out[1]*.036;
      const piece=(offsetX,offsetY,w,h,thick,col,depth=.0)=>{
        const loc=[px+xdir*offsetX+out[0]*depth,y+offsetY,pz+zdir*offsetX+out[1]*depth];
        cube(loc,side?[thick,h,w]:[w,h,thick],col);
      };
      const trim="#d4ccaf",dark="#697d73";
      piece(0,0,wide+.066,sy+.059,.042,dark,-.021);
      const lit=row.color[0]>.55&&row.color[1]>.32;
      piece(0,0,wide-.03,sy-.04,.027,lit?"#d9bb83":"#7f9999",.006);
      piece(0,-sy*.26,wide-.035,sy*.305,.018,lit?"#c9a980":"#617d83",.024);
      for(const sxv of [-1,1])piece(sxv*wide*.505,0,.027,sy+.04,.046,trim,.033);
      piece(0,sy*.48,wide+.047,.033,.065,trim,.034);
      piece(0,-sy*.50,wide+.085,.042,.085,trim,.038);
      piece(0,0,.018,sy-.035,.035,"#b6baaa",.031);
      piece(0,sy*.018,wide-.012,.022,.035,"#bec1ae",.032);
      if(lit)warm.push([px,y,pz]);
    }
    let mark=null;
    if(key==="town"){
      const b=boxes.find(v=>v.id==="inn"),front=b.y+b.d;
      mark=new T.Group();group.add(mark);
      const xm=b.x+b.w*.87;
      for(const angle of [-.72,.72]){
        const slat=new T.Mesh(new T.BoxGeometry(.105,.012,.012),new T.MeshStandardMaterial({color:"#473e34"}));
        slat.position.set(xm,.337,front+.118);slat.rotation.z=angle;mark.add(slat);
      }
      mark.visible=false;
      sign(group,"TUESDAY  •  FEB 02",[12,1.19,13.26],1.46,.18,"#3d6257","#f4dbac");
      const cx=12,cz=12.68;
      cube([cx,.43,cz+.06],[.46,.25,.32],"#a17550");
      shape("Sphere",[cx,.67,cz+.06],[.26,.29,.20],"#977052");
      shape("Sphere",[cx,.81,cz+.085],[.18,.17,.155],"#aa8364");
      for(const dx of [-.069,.069])shape("Sphere",[cx+dx,.879,cz+.071],[.062,.06,.055],"#8f6b53");
    }else{
      const x=11.5,z=11.33;
      cube([x,1.02,z+.127],[.27,.19,.035],"#bdc8bc");
      for(let j=0;j<3;j++)for(let i=0;i<3;i++)
        cube([x-.063+i*.056,.75-j*.06,z+.124],[.029,.038,.019],"#b4bdad");
      cube([x-.129,.73,z+.14],[.045,.25,.035],"#2d4443");
      for(const y of [.60,.86])cube([x-.107,y,z+.155],[.094,.045,.047],"#364e49");
      sign(group,"TELEPHONE",[x,1.092,z+.123],.43,.125,"#426357","#eee2b7");
    }
    return {mark,warm};
  }
  function practicals(T,parent,warm,lamps){
    const c=document.createElement("canvas");c.width=c.height=64;
    const ctx=c.getContext("2d"),gradient=ctx.createRadialGradient(32,32,0,32,32,31);
    gradient.addColorStop(0,"rgba(255,234,169,.95)");gradient.addColorStop(.18,"rgba(255,218,144,.67)");
    gradient.addColorStop(.51,"rgba(255,197,116,.14)");gradient.addColorStop(1,"rgba(255,197,112,0)");
    ctx.fillStyle=gradient;ctx.fillRect(0,0,64,64);
    const map=new T.CanvasTexture(c);map.colorSpace=T.SRGBColorSpace;
    const group=new T.Group();parent.add(group);
    function halo(coords,size){
      const geom=new T.BufferGeometry();geom.setAttribute("position",new T.Float32BufferAttribute(coords.flat(),3));
      group.add(new T.Points(geom,new T.PointsMaterial({size,map,color:0xffdc93,transparent:true,opacity:.88,
        blending:T.AdditiveBlending,depthWrite:false,fog:true,toneMapped:false})));
    }
    halo(warm,.41);halo(lamps.map(([x,z])=>[x,1.75,z]),.52);
    const poolMaterial=new T.MeshBasicMaterial({map,color:"#f3ba75",transparent:true,opacity:.32,
      blending:T.AdditiveBlending,depthWrite:false,toneMapped:false});
    const plane=new T.PlaneGeometry(2.1,2.1);
    for(const [x,z] of lamps){
      const pool=new T.Mesh(plane,poolMaterial);pool.rotation.x=-Math.PI/2;pool.position.set(x,.036,z);pool.renderOrder=1;group.add(pool);
    }
    group.visible=false;return group;
  }
  const channelNames={live_report:"LIVE REPORT",silent_live_reporter_line:"SILENT LINE",camera_take:"CAMERA TAPE",producer_live:"PRODUCER MIC",
    silent_producer_mic:"SILENT MIC",filed_forecast:"FILED REEL",empty_selected_return:"EMPTY RETURN",station_ident:"STATION ID"};
  function switcher(T,parent,part){
    const cart=new T.Group();cart.position.set(.24,0,.41);parent.add(cart);
    for(const x of [-.20,.20])for(const z of [-.10,.10])part(cart,"Cube",[x,.28,z],[.034,.56,.034],"#52675c");
    part(cart,"Cube",[0,.58,0],[.51,.075,.30],"#626b59");
    part(cart,"Cube",[0,.64,-.02],[.46,.075,.215],"#475d56");
    for(let i=0;i<4;i++)part(cart,"Cube",[-.13+i*.080,.686,-.032],[.047,.022,.037],i%2?"#ba976f":"#8ca59c");
    for(let i=0;i<2;i++)part(cart,"Cylinder",[-.135+i*.21,.692,.042],[.043,.033,.043],"#ccb995");
    const panel=document.createElement("canvas");panel.width=384;panel.height=92;
    const ctx=panel.getContext("2d"),map=new T.CanvasTexture(panel);map.colorSpace=T.SRGBColorSpace;
    const screen=new T.Mesh(new T.PlaneGeometry(.44,.135),new T.MeshBasicMaterial({map,side:T.DoubleSide,toneMapped:false}));
    screen.position.set(.0,.72,.078);cart.add(screen);
    let last=null;cart.visible=false;
    return {cart,update(p,facts,dressed){
      cart.visible=dressed&&!p.moving&&/^(patch_reporter_line|patch_camera_line|host_bulletin|play_filed_forecast)$/.test(p.action||"");
      if(!cart.visible)return;
      const key=facts?.bulletin?.channel||"";
      if(key===last)return;last=key;
      ctx.fillStyle="#2c493e";ctx.fillRect(0,0,384,92);ctx.fillStyle="#97ac85";ctx.fillRect(4,4,376,2);
      ctx.font="bold 35px Menlo,monospace";ctx.fillStyle=key?"#f5d193":"#bfd0b4";ctx.textAlign="center";ctx.textBaseline="middle";
      ctx.fillText(channelNames[key]||"RETURN READY",192,47,363);map.needsUpdate=true;
    }};
  }
  function wardrobe({T,group,joints,role,profile,part,makeExtraGroup}){
    const palette=profile==="reporter"?["#ad604b","#774a40","#e0b578","#4b5556","#c99b7b","#655044"]:
      profile==="producer"?["#657d8d","#4f626d","#d7ad70","#635b68","#ac7f64","#594a41"]:
      ["#72896d","#516d5c","#c89367","#896c59","#cea183","#756354"];
    const [coat,shadow,scarf,hat,skin,hair]=palette;
    const cloth=(kind,pos,size,color,rot)=>part(group,kind,pos,size,color,rot);
    // Separate cuffs and boots inherit the same USD joints as the base cloth.
    for(let i=0;i<2;i++){
      const side=i?1:-1,arm=makeExtraGroup(joints["Arm"+i]),leg=makeExtraGroup(joints["Leg"+i]);
      part(arm,"Sphere",[0,-.05,0],[.159,.17,.185],coat);
      part(arm,"Cube",[0,-.325,0],[.132,.067,.157],shadow);
      part(arm,"Sphere",[0,-.392,.014],[.116,.139,.132],skin);
      part(leg,"Sphere",[0,-.384,.041],[.154,.115,.256],"#514b41");
      part(leg,"Cube",[0,-.420,.053],[.145,.032,.211],"#393f39");
      cloth("Sphere",[side*.144,1.064,.005],[.055,.085,.055],skin);
      cloth("Cube",[side*.078,1.130,.130],[.052,.013,.019],hair,[0,0,side*.11]);
      cloth("Sphere",[side*.054,1.10,.145],[.012,.011,.009],"#efdfbb");
    }
    cloth("Cylinder",[0,.948,.011],[.131,.15,.13],skin);
    cloth("Sphere",[0,1.066,-.099],[.303,.287,.124],hair);
    cloth("Cube",[0,1.015,.141],[.062,.012,.016],"#946f5c");
    cloth("Cube",[0,.658,.136],[.018,.478,.018],shadow);
    for(const yy of [.56,.68,.80])cloth("Sphere",[.025,yy,.152],[.022,.022,.018],"#ceb891");
    for(const side of [-1,1]){
      cloth("Cube",[side*.113,.59,.135],[.091,.017,.023],shadow,[0,0,side*.11]);
      cloth("Sphere",[side*.118,.85,.031],[.176,.274,.225],coat);
    }
    const panel=new T.BufferGeometry();
    panel.setAttribute("position",new T.Float32BufferAttribute([
      -.105,.923,.151,-.117,.846,.148,-.010,.784,.149,
      .091,.924,.15,.110,.851,.151,.015,.80,.151
    ],3));panel.computeVertexNormals();
    const lapel=new T.Mesh(panel,new T.MeshStandardMaterial({color:shadow,roughness:.91,side:T.DoubleSide}));group.add(lapel);
    cloth("Cube",[.079,.83,.151],[.077,.242,.039],scarf,[0,0,.095]);
    if(profile==="reporter"){
      cloth("Cylinder",[0,1.171,.012],[.372,.036,.302],hat);
      cloth("Cube",[0,1.167,.142],[.29,.026,.105],hat,[.035,0,0]);
      cloth("Cylinder",[0,1.197,0],[.291,.028,.272],"#907b5e");
    }else if(profile==="producer"){
      cloth("Sphere",[0,1.064,-.08],[.319,.34,.175],hair);
      cloth("Sphere",[-.14,1.065,.015],[.047,.199,.096],hair);
      cloth("Sphere",[.141,1.058,.016],[.048,.193,.094],hair);
      cloth("Cylinder",[0,1.167,0],[.328,.042,.296],hat);
    }else{
      cloth("Cylinder",[0,1.156,0],[.33,.058,.303],hat);
      for(let i=0;i<9;i++){
        const a=i*Math.PI*2/9;
        cloth("Cube",[Math.sin(a)*.151,1.157,Math.cos(a)*.140],[.011,.042,.013],"#a1846a",[0,a,0]);
      }
    }
    const handheld=makeExtraGroup(group);handheld.name="Recorded action props";handheld.visible=false;
    const receiver=part(handheld,"Cube",[.19,1.055,.073],[.049,.158,.060],"#354e4c",[.13,0,-.18]);
    return {handheld,receiver};
  }
  return {facades,wardrobe,groundDress,contact,practicals,switcher,channelNames};
})();
