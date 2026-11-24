// Additional camera coverage for the Rialto stage. Loaded in the stage's renderer scope.
let phoneProps;
function phoneInTerminal() {
  if (phoneProps) return phoneProps;
  const material = color => new THREE.MeshStandardMaterial({color, roughness:.68});
  const add = (parent,geometry,color,x,y,z) => {
    const part=new THREE.Mesh(geometry,material(color));
    part.position.set(x,y,z);part.castShadow=true;part.receiveShadow=true;parent.add(part);return part;
  };
  const box=(parent,color,x,y,z,w,h,d)=>add(parent,new THREE.BoxGeometry(w,h,d),color,x,y,z);
  const base=sets.terminal.root;
  box(base,0x384948,-.92,.55,.05,.14,1.1,.16);
  box(base,0x365452,-.92,1.47,.06,.57,1.1,.32);
  box(base,0xb1b7a7,-.92,1.49,.24,.43,.66,.045);
  box(base,0x303d3c,-.92,1.75,.275,.27,.08,.02);
  for(let i=0;i<12;i++)box(base,0x536060,-1.025+(i%3)*.094,1.58-Math.floor(i/3)*.081,.28,.061,.049,.025);
  box(base,0x2e3b3a,-.92,1.91,.12,.64,.07,.53);
  box(base,0x273739,-.92,1.01,.242,.25,.09,.026);
  const handset=new THREE.Group();rigs.Phil.neck.add(handset);handset.position.set(.196,.127,.113);
  handset.rotation.x=-.32;
  box(handset,0x293638,0,0,0,.061,.252,.074);
  for(const dy of [-.137,.137])add(handset,new THREE.SphereGeometry(.068,14,10),0x263336,0,dy,.025);
  const rope=new THREE.Mesh(undefined,material(0x293230));base.add(rope);
  phoneProps={handset,rope};return phoneProps;
}
window.trailerCamera=(name,p)=>{
  const tel=name.startsWith('phone'), clock=name==='frontdesk', booth=name==='projector-detail';
  const set=tel?'terminal':clock?'hotel':booth?'rialto':'station';
  const slot={set,phase:tel||set==='station'?'evening':'afternoon'};
  selectSet(slot);
  for(const rig of Object.values(rigs))rig.root.visible=false;
  bus.visible=false;
  if(phoneProps)phoneProps.handset.visible=tel;
  const off=sets[set].cfg.offset;
  let eyePos,look;
  renderer.toneMappingExposure=tel?.82:booth?.84:clock?.83:.68;
  if(tel){
    const {handset,rope}=phoneInTerminal();handset.visible=true;
    const ph=rigs.Phil;pose(ph,-.20,.47,-.44,'idle',p);
    ph.neck.rotation.set(.08+.026*Math.sin(p*6),-.08+.052*Math.sin(p*4),.03);
    ph.limbs.r.arm.rotation.set(-.75,.22,.31);
    ph.limbs.r.elbow.rotation.set(-2.19,0,.14);
    ph.limbs.l.arm.rotation.x=-.15+.04*Math.cos(5*p);
    sets.terminal.root.updateMatrixWorld(true);ph.root.updateMatrixWorld(true);
    const end=sets.terminal.root.worldToLocal(handset.localToWorld(new THREE.Vector3(0,-.13,0)));
    const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(-.66,1.36,.22),new THREE.Vector3(-.53,.89,.33),new THREE.Vector3(-.16,.82,.45),end]);
    rope.geometry.dispose();rope.geometry=new THREE.TubeGeometry(curve,22,.014,6,false);
    if(name==='phone-wide'){eyePos=[1.66-p*.28,2.06,4.72-p*.46];look=[-.46,1.45,-.13];}
    else if(name==='phone-close'){eyePos=[1.02-p*.10,1.89,2.94-p*.18];look=[-.33,1.51,.33];}
    else {eyePos=[.45+p*.10,1.70,2.05-p*.08];look=[-.25,1.58,.38];}
  }else if(clock){eyePos=[2.70-p*.24,2.27,4.3-p*.28];look=[-.52,2.1,-2.78];}
  else if(booth){eyePos=[-.69-p*.27,1.95,2.36-p*.34];look=[-2.39,1.45,-.70];}
  else{
    sets.station.props.deliveryCan.visible=false;
    sets.station.props.meters.forEach(m=>m.scale.y=.035);
    sets.station.props.reels.forEach(r=>r.rotation.z=0);
    if(name==='quiet-desk'){eyePos=[2.55-.45*p,2.2,3.2-.6*p];look=[-.05,1.52,-1.35];}
    else {eyePos=[-.78+.32*p,1.58,.52-.14*p];look=[-.33,1.44,-1.16];}
  }
  cam.aspect=canvas.clientWidth/canvas.clientHeight;cam.updateProjectionMatrix();
  cam.position.set(eyePos[0]+off[0],eyePos[1],eyePos[2]+off[1]);
  cam.lookAt(look[0]+off[0],look[1],look[2]+off[1]);
  lighting.position.set(off[0]+3.6,8.1,off[1]+5.2);lighting.target.position.set(off[0],0,off[1]);
  renderer.setScissorTest(false);renderer.setViewport(0,0,canvas.clientWidth,canvas.clientHeight);
  renderer.render(scene,cam);
};
