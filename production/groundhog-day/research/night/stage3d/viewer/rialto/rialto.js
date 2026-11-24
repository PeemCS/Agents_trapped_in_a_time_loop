(() => {
  "use strict";
  const $=id=>document.getElementById(id), data=window.RialtoTake, shots=data.shots, A=window.RialtoSets;
  const coords={
    piano:{house:[[4.5,2.75,5.3],[-1.30,.95,-.72]],close:[[1.13,1.67,1.30],[-1.42,.91,-.69]],overhead:[[.5,6.9,2.20],[-.92,.58,-.50]]},
    bench:{house:[[3.48,2.24,5.37],[.03,1.12,-1.57]],close:[[1.60,1.10,1.43],[.0,1.03,-1.62]],overhead:[[.6,6.8,3.15],[0,.44,-1.28]]},
    dance:{house:[[3.27,2.13,5.49],[.37,1.37,-1.18]],close:[[1.76,1.56,3.27],[.84,1.04,-.13]],overhead:[[.32,6.95,3.11],[.20,.41,-.58]]},
    coach:{house:[[3.99,2.31,6.42],[.13,1.14,-.28]],close:[[2.48,1.61,4.0],[.04,1.04,.70]],overhead:[[.30,7.04,3.23],[.09,.43,.09]]},
    interview:{house:[[3.84,2.49,5.66],[.03,1.34,-1.40]],close:[[-1.37,1.67,3.08],[1.10,1.16,-.85]],overhead:[[.22,6.50,2.91],[.13,.48,-.77]]},
    sleep:{house:[[3.80,2.05,5.28],[-.62,1.30,-1.66]],close:[[1.52,1.10,1.64],[-1.10,.92,-1.13]],overhead:[[.10,6.49,3.65],[-.72,.40,-.84]]},
    reel:{house:[[3.82,2.47,5.16],[.06,1.36,-1.45]],close:[[-2.40,1.76,2.69],[-.49,1.09,-.54]],overhead:[[.08,6.18,2.23],[.06,.46,-.60]]},
    line:{house:[[-3.71,2.53,5.37],[.13,1.34,-1.49]],close:[[2.9,2.14,1.78],[.58,1.21,-.99]],overhead:[[.13,6.18,2.23],[.10,.47,-.68]]},
    receipt:{house:[[3.75,2.44,5.41],[-.43,1.42,-1.37]],close:[[.66,2.32,1.35],[-.28,1.30,-.75]],overhead:[[.31,5.48,1.57],[-.27,.63,-.75]]}
  };
  const LABELS={piano:["Phil"],bench:["Phil"],dance:["Rita"],coach:["Phil"],interview:["Rita","Alma","Larry"],sleep:["Phil"],reel:["Larry","Rita"],line:["Rita","Larry"],receipt:["Phil"]};
  const tvec=(v)=>new THREE.Vector3(...v),clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,p)=>a+(b-a)*p;
  let renderer=null,scene=null,cam=null,lighting=null,hemi=null,rigs={},sets={},bus=null,labels={},index=0,progress=0,angle="house",playing=false,ready=false,nextUI=-1,raf=0;
  let parallel=false,comparison=[],cinematicCaptions=false;
  let focus=new THREE.Vector3(),eye=new THREE.Vector3(),actualEye=new THREE.Vector3(),currentSet=null;const canvas=$("view");
  function init(){
    try{
      renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:"high-performance",preserveDrawingBuffer:true});
      renderer.setPixelRatio(Math.min(1.65,window.devicePixelRatio||1));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.91;
      renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    }catch(error){$("fallback").hidden=false;document.body.classList.add("fallback-mode");return false;}
    scene=new THREE.Scene();cam=new THREE.PerspectiveCamera(36,1,.05,240);
    hemi=new THREE.HemisphereLight("#edede3","#8d8c87",.92);scene.add(hemi);
    lighting=new THREE.DirectionalLight("#ffe3c1",1.38);lighting.position.set(3.6,8.1,5.2);lighting.castShadow=true;
    Object.assign(lighting.shadow.camera,{left:-6.4,right:6.4,top:6.2,bottom:-5,near:.7,far:24});lighting.shadow.mapSize.set(1024,1024);lighting.shadow.bias=-.00017;lighting.shadow.normalBias=.016;
    scene.add(lighting,lighting.target);const rim=new THREE.DirectionalLight("#cee0da",.49);rim.position.set(-4,4,-3);scene.add(rim);
    for(const id of Object.keys(A.config)){sets[id]=A.buildSet(scene,id);sets[id].root.visible=false;}
    for(const name of ["Phil","Rita","Larry","Alma"]){
      const rig=A.figure(scene,name);rig.root.visible=false;rigs[name]=rig;
      const label=document.createElement("b");label.textContent=name;if(name==="Alma")label.className="world";$("labels").append(label);labels[name]=label;
    }
    rigs.Larry.camera=A.handheld(rigs.Larry,"camera");rigs.Larry.reel=A.handheld(rigs.Larry,"reel");rigs.Rita.mic=A.handheld(rigs.Rita,"mic");
    bus=A.coach(sets.terminal.root);bus.scale.set(1.56,1.50,1.47);bus.visible=false;
    return true;
  }
  function pose(rig,x,z,yaw,mode,p){
    const loc=sets[currentSet].cfg.offset;rig.root.visible=true;rig.root.position.set(loc[0]+x,0,loc[1]+z);rig.root.rotation.set(0,yaw,0);
    const moving=mode==="walk"||mode==="dance",a=p*Math.PI*(mode==="dance"?6:4),s=Math.sin(a);
    const seated=["piano","bench","sleep","interviewee"].includes(mode);
    rig.eyes.forEach(e=>e.visible=mode!=="sleep");rig.lids.forEach(e=>e.visible=mode==="sleep");
    rig.hips.position.set(0,seated?.61:.85,0);rig.body.rotation.set(0,0,0);rig.neck.rotation.set(0,0,0);
    if(rig.camera)rig.camera.visible=mode==="camera";if(rig.reel)rig.reel.visible=mode==="reel";if(rig.mic)rig.mic.visible=mode==="mic";
    rig.held.rotation.set(0,0,0);
    for(const [key,sign] of [["l",-1],["r",1]]){
      const part=rig.limbs[key];part.arm.rotation.set(.04,0,.10*sign);part.elbow.rotation.set(-.16,0,0);part.leg.rotation.set(0,0,0);part.knee.rotation.set(0,0,0);
      if(seated){part.leg.rotation.x=-1.29;part.knee.rotation.x=1.40;part.arm.rotation.x=-.48;part.elbow.rotation.x=-.72;}
      if(moving){
        part.leg.rotation.x=sign*s*(mode==="dance"?.34:.6);part.knee.rotation.x=Math.max(0,-sign*s)*.56;
        part.arm.rotation.x=-s*sign*.41;rig.hips.position.y+=.012*Math.abs(s);
      }
      if(mode==="piano"){rig.body.rotation.x=.11;part.arm.rotation.set(-1.27+sign*.085*Math.sin(16*Math.PI*p),0,.065*sign);part.elbow.rotation.x=-.22-.05*Math.cos(17*Math.PI*p);rig.neck.rotation.x=.10;}
      if(mode==="bench"){rig.body.rotation.x=.23;rig.neck.rotation.x=.20+.025*Math.sin(p*4);part.arm.rotation.x=-.55;part.elbow.rotation.x=-.68;}
      if(mode==="sleep"){rig.body.rotation.set(.57,.08,-.41);rig.neck.rotation.set(.40,.07,-.32);
        part.arm.rotation.set(sign>0?-.80:-.54,0,sign*-.19);part.elbow.rotation.x=sign>0?-1.44:-.86;
        if(sign>0)part.elbow.rotation.z=-.4;}
      if(mode==="dance"){
        const wave=Math.cos(a);part.arm.rotation.set(-.31+sign*s*.14,0,sign*(sign>0?1.49+.18*wave:.72+.19*wave));
        part.elbow.rotation.set(-.62,0,sign*(sign>0?.76+.13*wave:.35));part.leg.rotation.z=sign*.08+s*.075;
        rig.body.rotation.z=s*.08;rig.neck.rotation.y=.12*wave;
      }
      if(mode==="camera"){part.arm.rotation.set(-1.23,0,sign*.043);part.elbow.rotation.x=-.59;rig.held.rotation.x=1.82;rig.neck.rotation.x=.05;}
      if(mode==="mic"&&sign===1){part.arm.rotation.set(-.93,0,.09);part.elbow.rotation.x=-.71;rig.held.rotation.x=1.61;}
      if(mode==="interviewee"){rig.body.rotation.x=.04;rig.neck.rotation.y=.065*Math.sin(4*p);part.arm.rotation.x=-.43;part.elbow.rotation.x=-.81+sign*.08*Math.sin(5*p);}
      if(mode==="patch"){part.arm.rotation.set(-.85-.09*s,0,sign*.13);part.elbow.rotation.x=-.71;rig.body.rotation.x=.12;rig.neck.rotation.x=.20;}
      if(mode==="reel"&&sign===1){part.arm.rotation.x=-.73-.15*p;part.elbow.rotation.x=-.81;rig.held.rotation.x=1.40;}
      if(mode==="read"){rig.body.rotation.x=.15;rig.neck.rotation.x=.20;part.arm.rotation.x=-.61;part.elbow.rotation.x=-.87;}
    }
  }
  function performers(shot,p){
    const {kind}=shot;for(const r of Object.values(rigs))r.root.visible=false;bus.visible=false;
    const ph=rigs.Phil,ri=rigs.Rita,la=rigs.Larry,al=rigs.Alma;
    if(kind==="piano"){
      pose(ph,-1.50,-.30,Math.PI,"piano",p);
      for(const [i,k] of sets.ballroom.props.piano.keys.entries())k.position.y=.987-(Math.max(0,Math.sin(p*43-i*2.3))**9)*.024;
    }else if(kind==="bench")pose(ph,.0,-1.66,.105,"bench",p);
    else if(kind==="dance"){
      const a=p*Math.PI*2;pose(ri,.64+.48*Math.sin(a),-.11+.37*Math.cos(a),-.56+1.36*Math.sin(a),"dance",p);
    }else if(kind==="coach"){
      const ride=clamp(p/.50,0,1),smooth=ride*ride*(3-2*ride);bus.position.set(lerp(-6.9,-.76,smooth),0,.24);bus.visible=true;
      if(p>=.50){const f=clamp((p-.5)/.47,0,1);pose(ph,lerp(1.36,2.00,f),lerp(1.37,1.93,f),.83,f<.98?"walk":"idle",f);}
    }else if(kind==="interview"){
      pose(ri,-.17,-.07,2.10,"mic",p);pose(al,1.32,-.97,-.94,"interviewee",p);pose(la,2.72,.44,-2.32,"camera",p);
      la.camera.userData.tally.visible=Math.cos(p*20)>-.22;
    }else if(kind==="sleep")pose(ph,-1.14,-1.13,-.13,"sleep",p);
    else if(kind==="line"||kind==="reel"){
      pose(ri,.74,-.39,-2.90,"patch",p);
      const f=clamp(p/.67,0,1),pass=clamp((p-.66)/.18,0,1);
      pose(la,lerp(-2.62,-1.50,f),lerp(.27,-.18,f),2.11,"reel",p);
      const station=sets.station,can=station.props.deliveryCan;
      la.reel.visible=pass===0;can.visible=pass>0;
      if(can.visible){
        const start=station.root.worldToLocal(la.held.getWorldPosition(new THREE.Vector3()));
        can.position.copy(start).lerp(new THREE.Vector3(-1.25,1.17,-1.00),pass);
        can.rotation.set(-Math.PI*pass/2,.45*(1-pass),0);
      }
    }else if(kind==="receipt")pose(ph,-1.16,-.05,2.23,"read",p);
    const props=sets[currentSet].props;if(props.clock)props.clock.set(shot.phase);
    if(props.reels)props.reels.forEach((r,i)=>r.rotation.z=kind==="interview"?0:p*3.3*(i%2?1:-1));
    if(props.meters)props.meters.forEach((m,i)=>m.scale.y=.10+.18*Math.abs(Math.sin(p*29+i*.61)));
  }
  function camera(shot){
    const pair=coords[shot.kind][angle],off=sets[shot.set].cfg.offset;
    focus.copy(tvec(pair[1])).add(new THREE.Vector3(off[0],0,off[1]));eye.copy(tvec(pair[0])).add(new THREE.Vector3(off[0],0,off[1]));
    const aspect=cam.aspect;
    // Constrain horizontal composition across portrait and landscape without changing the stage coordinates.
    const extra=aspect<1.28?Math.min(1.73,1.28/aspect):1;
    actualEye.copy(eye).sub(focus).multiplyScalar(extra).add(focus);
    cam.position.copy(actualEye);cam.lookAt(focus);cam.updateMatrixWorld();
    lighting.position.set(off[0]+3.6,8.1,off[1]+5.2);lighting.target.position.set(off[0],0,off[1]);
  }
  function labelScreens(shot,rect){
    const visible=[];
    for(const name of LABELS[shot.kind]){
      const r=rigs[name];if(!r.root.visible)continue;
      const point=r.neck.localToWorld(new THREE.Vector3(0,.48,0)).project(cam);
      if(point.z<0||point.z>1||Math.abs(point.x)>.94||Math.abs(point.y)>.94)continue;
      const x=rect.x+(point.x+1)*rect.w/2;let y=rect.y+(1-point.y)*rect.h/2;
      for(const other of visible)if(Math.abs(x-other.x)<49&&Math.abs(y-other.y)<22)y=other.y-23;
      visible.push({name,x,y});
    }return visible;
  }
  function showLabels(points){
    for(const l of Object.values(labels))l.hidden=true;
    for(const {name,x,y} of points){const l=labels[name];l.hidden=false;l.style.left=x+"px";l.style.top=y+"px";}
  }
  function partnerShots(){
    if(index===1||index===2)return [1,2];
    if(index===3||index===4)return [3,4];
    if(index>=5&&index<=7)return [5,index===6?6:7];
    return [];
  }
  function viewRectangles(w,h){
    if(window.matchMedia("(max-width:650px)").matches){
      const split=Math.floor(h/2);return [{x:0,y:0,w,h:split},{x:0,y:split,w,h:h-split}];
    }
    const split=Math.floor(w/2);return [{x:0,y:0,w:split,h},{x:split,y:0,w:w-split,h}];
  }
  function selectSet(shot){
    const outdoors=shot.set==="depot"||shot.set==="terminal",night=shot.phase==="evening";
    lighting.intensity=night&&outdoors?.66:1.35;hemi.intensity=night&&outdoors?.63:.92;
    renderer.toneMappingExposure=night&&outdoors?.80:.90;
    if(currentSet===shot.set){lighting.color.set(night&&outdoors?"#a6bed1":sets[shot.set].cfg.lit);return;}currentSet=shot.set;
    for(const [k,s] of Object.entries(sets))s.root.visible=k===shot.set;
    const cfg=sets[shot.set].cfg;scene.background=new THREE.Color(cfg.bg);scene.fog=new THREE.Fog(cfg.bg,12,31);
    lighting.color.set(night&&outdoors?"#a6bed1":cfg.lit);
  }
  function setText(shot){
    $("where").textContent=data.sets[shot.set];$("when").textContent="Loop "+String(shot.day).padStart(2,"0")+" · Tue "+({afternoon:"afternoon",evening:"7 pm",dawn:"6 am"}[shot.phase]);
    $("heading").textContent=shot.title;$("count").textContent=String(index+1).padStart(2,"0")+" / "+String(shots.length).padStart(2,"0");$("shots").value=String(index);
    $("effect").textContent=shot.kind==="receipt"?"At the hotel, Phil can see the envelope from Pittsburgh. The clock still reads Tuesday.":shot.effect;
    $("source").textContent=shot.id+" · "+shot.key.slice(0,10);$("source").title="Source request "+shot.key;
    $("receipt").hidden=shot.kind!=="receipt";if(shot.kind==="receipt")$("receipt").querySelector("q").textContent=shot.receipt;
    $("other").replaceChildren();$("crew-label").textContent=shot.kind==="receipt"?"World receipt":"Same slot";
    if(shot.kind==="receipt")$("other").textContent="Written by the world · Observed by Phil";
    for(const v of Object.values(shot.crew)){
      const coverage=shots.findIndex(choice=>choice.id===v.id);
      const s=document.createElement(coverage>=0&&coverage!==index?"button":"span");s.textContent=v.actor+" · "+data.sets[v.location];
      if(s.tagName==="BUTTON"){s.title="Follow "+v.actor+" in this decision slot";s.onclick=()=>seek(coverage,progress);}
      $("other").append(s);
    }
  }
  function prepare(shot,w,h){
    cam.aspect=w/Math.max(1,h);cam.updateProjectionMatrix();selectSet(shot);performers(shot,progress);camera(shot);
  }
  function render(){
    const shot=shots[index],partners=partnerShots();if(!partners.length)parallel=false;
    if(nextUI!==index){setText(shot);nextUI=index;}
    $("parallel").hidden=!partners.length;$("parallel").setAttribute("aria-pressed",String(parallel));
    $("screen").classList.toggle("split",parallel);$("split-name").hidden=$("split-divider").hidden=!parallel;
    $("where").textContent=data.sets[parallel?shots[partners[0]].set:shot.set];
    if(parallel)$("split-name").textContent=data.sets[shots[partners[1]].set]+" · Same slot";
    const cutCaption=$("cut-caption");cutCaption.hidden=!cinematicCaptions;
    if(cinematicCaptions){
      cutCaption.querySelector("b").textContent=parallel?"Same decision slot":shot.kind==="receipt"?"World receipt":shot.speaker+" · Recorded action";
      cutCaption.querySelector("span").textContent=parallel?partners.map(i=>shots[i].effect).join(" "):shot.kind==="receipt"?"Tuesday, six am. An envelope has arrived from Pittsburgh.":shot.effect;
    }
    $("play").textContent=playing?"Pause":"Play";$("play").setAttribute("aria-label",playing?"Pause performance":"Play performance");
    $("time").value=String(index+progress);$("prev").disabled=index===0;$("next").disabled=index===shots.length-1;
    if(!ready)return;
    const w=canvas.clientWidth,h=canvas.clientHeight,ratio=renderer.getPixelRatio();
    if(renderer.domElement.width!==Math.round(w*ratio)||renderer.domElement.height!==Math.round(h*ratio))renderer.setSize(w,h,false);
    const slots=parallel?partners:[index],rectangles=parallel?viewRectangles(w,h):[{x:0,y:0,w,h}],points=[];comparison=[];
    renderer.setScissorTest(parallel);
    slots.forEach((id,i)=>{
      const source=shots[id],r=rectangles[i],glY=h-r.y-r.h;prepare(source,r.w,r.h);
      renderer.setViewport(r.x,glY,r.w,r.h);if(parallel)renderer.setScissor(r.x,glY,r.w,r.h);
      renderer.render(scene,cam);points.push(...labelScreens(source,r));
      if(parallel)comparison.push({id:source.id,key:source.key,set:source.set,visible:Object.values(rigs).filter(per=>per.root.visible).map(per=>per.name),rect:r});
    });
    renderer.setScissorTest(false);renderer.setViewport(0,0,w,h);
    if(parallel){const chosen=Math.max(0,partners.indexOf(index)),r=rectangles[chosen];prepare(shot,r.w,r.h);}
    showLabels(points);
  }
  function state(){
    const s=shots[index],world={},poses={};
    for(const [n,r] of Object.entries(rigs))if(r.root.visible){
      world[n]=r.root.position.toArray();poses[n]={heading:r.root.rotation.y,hip:r.hips.position.y,body:r.body.rotation.toArray().slice(0,3),
        wrist:r.held.getWorldPosition(new THREE.Vector3()).toArray(),knee:r.limbs.r.knee.rotation.x};
    }
    const props=ready?sets[s.set].props:{};
    let art={};if(props.piano)art.keys=props.piano.keys.map(k=>k.position.y);
    if(props.reels)art.spools=props.reels.map(r=>r.rotation.z);
    if(props.env)art.envelope=props.env.getWorldPosition(new THREE.Vector3()).toArray();
    if(props.meters)art.levels=props.meters.map(r=>r.scale.y);
    if(props.deliveryCan)art.intakeReel=props.deliveryCan.visible?props.deliveryCan.getWorldPosition(new THREE.Vector3()).toArray():null;
    if(s.kind==="interview"&&ready)art.cameraRecordingTally=rigs.Larry.camera.userData.tally.visible;
    if(s.kind==="sleep"&&ready)art.closedEyes=rigs.Phil.lids.every(lid=>lid.visible);
    return {renderer:ready?"WebGL":"video",id:s.id,key:s.key,kind:s.kind,day:s.day,phase:s.phase,set:s.set,actor:s.speaker,action:s.action,effect:s.effect,
      crew:s.crew,visible:Object.keys(world),positions:world,poses,art,geometry:ready?Object.fromEntries(Object.entries(sets).map(([k,v])=>[k,{origin:v.root.position.toArray(),visible:v.root.visible}])):{},
      bus:ready&&bus.visible?{position:bus.getWorldPosition(new THREE.Vector3()).toArray()}:null,
      index,progress,playing,angle,parallel,comparison,eye:actualEye.toArray(),target:focus.toArray(),receipt:s.receipt||null,sha256:data.sha256};
  }
  function seek(i,p=0){
    if(!Number.isInteger(i)||i<0||i>=shots.length||!Number.isFinite(p))throw new RangeError("Unknown shot or position");
    index=i;progress=clamp(p,0,1);playing=false;render();return state();
  }
  function setParallel(on){
    parallel=!!on&&partnerShots().length>0;render();return state();
  }
  function setCamera(a){
    if(!["house","close","overhead"].includes(a))throw new RangeError("Unknown angle");
    angle=a;document.querySelectorAll("[data-angle]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.angle===a)));render();return state();
  }
  function play(){
    if(!ready)return false;
    if(index===shots.length-1&&progress>=1){index=0;progress=0;}playing=!playing;render();return playing;
  }
  function tick(ts){
    const dt=raf?Math.min((ts-raf)/1000,.24):0;raf=ts;
    if(playing){progress+=dt/shots[index].seconds;
      if(progress>=1){if(index+1===shots.length){progress=1;playing=false;}else{const extra=(progress-1)*shots[index].seconds;index++;progress=extra/shots[index].seconds;}}
      render();}
    requestAnimationFrame(tick);
  }
  for(const [i,s] of shots.entries()){const o=document.createElement("option");o.value=String(i);o.textContent=String(i+1).padStart(2,"0")+"  "+s.title;$("shots").append(o);}
  $("parallel").onclick=()=>setParallel(!parallel);$("play").onclick=play;$("prev").onclick=()=>seek(Math.max(0,index-1));$("next").onclick=()=>seek(Math.min(shots.length-1,index+1));
  $("shots").onchange=e=>seek(Number(e.target.value));$("time").oninput=e=>{const v=Number(e.target.value),i=Math.min(shots.length-1,Math.floor(v));seek(i,v-i);};
  document.querySelectorAll("[data-angle]").forEach(b=>b.onclick=()=>setCamera(b.dataset.angle));
  $("full").onclick=()=>{if(document.fullscreenElement)document.exitFullscreen?.();else $("screen").requestFullscreen?.();};
  document.addEventListener("keydown",e=>{if(["INPUT","SELECT","BUTTON","A"].includes(e.target.tagName))return;
    if(e.key===" "){e.preventDefault();play();}if(e.key==="ArrowRight")seek(Math.min(shots.length-1,index+1));if(e.key==="ArrowLeft")seek(Math.max(0,index-1));});
  ready=init();render();
  const params=new URLSearchParams(location.search),target=shots.findIndex(s=>s.id===params.get("shot"));
  if(target>=0){const fraction=Number(params.get("at")||0);seek(target,Number.isFinite(fraction)?fraction:0);}
  const lens=params.get("camera");if(["house","close","overhead"].includes(lens))setCamera(lens);
  if(params.get("view")==="split")setParallel(true);
  new ResizeObserver(render).observe($("screen"));requestAnimationFrame(tick);
  window.Rialto3D={seek,setCamera,setParallel,getState:state,renderNow:render,setCinematic(v,options={}){cinematicCaptions=!!v&&options.captions!==false;document.body.classList.toggle("capture",!!v);render();return state();}};
  window.dispatchEvent(new Event("rialto3d:ready"));
})();
