// Shot blocking for the first-person winter street and Ned's return to the pier.
// Distances are metres. The stage actors face +Z and their elbows bend about X.
const PI = Math.PI;
const blend = (a,b,t) => a+(b-a)*t;
const sat = t => Math.max(0,Math.min(1,t));
const ease = t => { const k=sat(t); return k*k*(3-2*k); };
const turn = (t,start,end) => ease((t-start)/(end-start));
const mix = (a,b,t) => a.map((v,i)=>blend(v,b[i],t));

export function shot(id,u,s) {
  const T=s.T;
  const get=n=>s.get(n);
  const show=(n,on)=>{const o=get(n); if(o)o.visible=on;};
  const pose=(n,p,r)=>{const o=get(n); if(!o)return; if(p)o.position.set(...p); if(r)o.rotation.set(...r);};
  const swing=(n,x,y=0,z=0)=>{const o=get(n); if(o)o.rotation.set(x,y,z);};
  const cam=(eye,aim,fov)=>s.cam(eye,aim,fov);
  const cold=()=>s.light('#e7ece6','#9b9b8e','#fff1d4',2.05);
  const nearCamera=(name,pos,at,eye,angles)=>{
    const obj=get(name);
    if(!obj)return;
    const camera=new T.PerspectiveCamera();
    camera.position.set(...eye);
    camera.lookAt(...at);
    camera.updateMatrixWorld();
    obj.position.copy(camera.localToWorld(new T.Vector3(...pos)));
    obj.quaternion.copy(camera.quaternion).multiply(new T.Quaternion().setFromEuler(new T.Euler(...angles)));
  };
  const part=(actor,bone,x,y=0,z=0)=>swing(actor+'.'+bone,x,y,z);
  const body=(name,x,z,yaw,step=0,intensity=0)=>{
    pose(name,[x,.134+Math.abs(Math.sin(step))*intensity*.022,z],[0,yaw,0]);
    part(name,'head',.012,0,0);
    part(name,'armL',Math.sin(step)*.36*intensity,0,.07);
    part(name,'armR',-Math.sin(step)*.36*intensity,0,-.07);
    part(name,'foreL',-.10,0,0);
    part(name,'foreR',-.10,0,0);
    part(name,'legL',-Math.sin(step)*.38*intensity,0,0);
    part(name,'legR',Math.sin(step)*.38*intensity,0,0);
  };
  // Two-link arm solve keeps palms on the actual book, pen and paper.
  function reach(name,side,point,elbowBias){
    const arm=get(name+'.arm'+side),fore=get(name+'.fore'+side);
    if(!arm||!fore)return;
    const world=new T.Vector3(),parentQ=new T.Quaternion(),down=new T.Vector3(0,-1,0);
    const target=new T.Vector3(...point);
    arm.getWorldPosition(world);
    const distance=target.distanceTo(world),upper=.264,lower=.320;
    const direction=target.clone().sub(world).normalize();
    const pole=new T.Vector3(...elbowBias);
    pole.addScaledVector(direction,-pole.dot(direction)).normalize();
    const d=Math.max(.025,Math.min(upper+lower-.0001,distance));
    const axial=(upper*upper-lower*lower+d*d)/(2*d);
    const elbow=world.clone().addScaledVector(direction,axial)
      .addScaledVector(pole,Math.sqrt(Math.max(0,upper*upper-axial*axial)));
    arm.parent.getWorldQuaternion(parentQ).invert();
    arm.quaternion.setFromUnitVectors(down,elbow.clone().sub(world).normalize().applyQuaternion(parentQ));
    fore.parent.getWorldQuaternion(parentQ).invert();
    fore.quaternion.setFromUnitVectors(down,target.sub(elbow).normalize().applyQuaternion(parentQ));
  }
  const holdBook=(x,y,z,yaw=0)=>{
    pose('ExtPolicy',[x,y,z],[.24,yaw,-.025]);
    reach('StreetNed','R',[x-.172*Math.cos(yaw),y-.039,z+.172*Math.sin(yaw)],[-.75,-.95,.13]);
    reach('StreetNed','L',[x+.172*Math.cos(yaw),y-.036,z-.172*Math.sin(yaw)],[.75,-.95,.13]);
  };
  const speak=(name,p)=>{
    const o=get(name+'.mouth');
    if(o){
      if(!o.userData.neutralMouth)o.userData.neutralMouth=o.scale.clone();
      o.scale.copy(o.userData.neutralMouth);
      o.scale.y*=1+1.05*Math.abs(Math.sin(p*31)*Math.cos(p*19));
    }
  };
  const street=['streetCrew','streetNed','rooftops','wheel','policy','waits','signs','follows'].includes(id);
  if(street){
    cold();
    const crew=id==='streetCrew', ned=['streetNed','policy','waits','signs','follows'].includes(id);
    const phil=['policy','waits','signs','follows'].includes(id);
    for(const n of ['StreetLarry','StreetRita','ExtWatch','ExtWatchFinger','ExtCamera'])show(n,crew);
    show('StreetNed',ned);show('StreetPhil',phil);
    show('ExtWheelHand',id==='wheel');show('ExtWarmWindows',id==='rooftops');
    show('ExtPolicy',ned);show('ExtBallpoint',['waits','signs','follows'].includes(id));
    show('ExtReceipt',id==='signs'||id==='follows');show('ExtCarbon',id==='signs'||id==='follows');
    pose('ExtSedan',[-7.38,.02,4.43],[0,0,0]);
    pose('ExtWagon',[4.87,.02,3.75],[0,0,0]);
    if(ned){
      body('StreetNed',.68,.74,-.46);
      part('StreetNed','armL',-.63,0,.22);part('StreetNed','foreL',-.72,0,.28);
      part('StreetNed','armR',-.48,0,-.26);part('StreetNed','foreR',-.51,0,-.23);
      holdBook(.53,1.19,1.049,-.34);
    }
    if(phil)body('StreetPhil',-.38,.79,.84);
  }
  if(id==='streetCrew'){
    const phase=turn(u,.13,.50),away=turn(u,.67,1);
    body('StreetRita',-4.15,.45,.29);
    part('StreetRita','armR',-.55-.18*phase,.04,-1.61+.12*Math.sin(u*6));
    part('StreetRita','foreR',-.40,.04,-.42);
    part('StreetRita','head',.012+.05*Math.sin(u*6),.15-.21*u,-.035);
    speak('StreetRita',u);
    body('StreetLarry',-5.73,1.31,.87);
    part('StreetLarry','armL',-.74,0,.12);part('StreetLarry','foreL',-.79);
    part('StreetLarry','armR',-.56,0,-.18);part('StreetLarry','foreR',-.96);
    const eye=[-3.51+.07*u,1.72+.012*Math.sin(u*5),2.76-.12*u];
    const aim=[-4.54+.37*away,1.61-.25*phase+.20*away,.46];
    cam(eye,aim,53);
    const lift=turn(u,0,.37)-.73*turn(u,.65,1);
    nearCamera('ExtWatch',[-.12,-.36+.183*lift,-.59],aim,eye,[.74,-.15,.06]);
    nearCamera('ExtWatchFinger',[.16-.308*lift,-.29+.155*lift+.017*Math.abs(Math.sin(u*18)),-.526],aim,eye,[.78,-.18,.04]);
  } else if(id==='streetNed'){
    const stride=turn(u,.13,1);
    const eye=[-.39+2.04*stride,1.71+.035*Math.sin(u*PI*3)*stride,2.34-.12*stride];
    const aim=[.68+2.63*turn(u,.40,1),1.64-.18*stride,.81-.23*stride];
    part('StreetNed','head',.035,-.12+.59*stride,-.045);
    part('StreetNed','armR',-.51-.20*ease(u),0,-.21);
    speak('StreetNed',u);
    cam(eye,aim,52);
  } else if(id==='depotHands'||id==='depotWide'){
    s.light('#d9e8e7','#85918c','#fff2d9',1.6);
    const k=id==='depotWide'?turn(u,.02,.92):0;
    const eye=[1.25,1.20+.011*Math.sin(u*4),1.57-.018*k];
    const target=mix([1.25,.575,1.18],[1.18,1.59,-2.8],k);
    pose('ExtLap',[1.25,.077+.005*Math.sin(u*5),1.13]);
    cam(eye,target,blend(40,56,k));
  } else if(id==='coachDoor'){
    cold();
    pose('ExtScenery',[0,0,0]);
    show('ExtRailHand',u>.58);
    const k=ease(u);
    const pull=turn(u,.58,1);
    const eye=mix([-5.99,1.49,6.68],[-4.55,1.57,3.11],k);
    eye[2]-=.96*pull;eye[1]+=.13*pull;

    eye[1]+=.085*Math.sin(u*PI);
    const aim=mix([-3.80,1.40,1.01],[-4.19,1.27,1.0],k);
    cam(eye,aim,48);
    const wrist=get('ExtRailHand');
    nearCamera('ExtRailHand',[.54,-.66,-.41],aim,eye,[.18,.12,0]);
    wrist.position.lerp(new T.Vector3(-3.57,1.26,1.43),pull);
    wrist.quaternion.slerp(new T.Quaternion(),pull);
  } else if(id==='coachWindow'){
    s.light('#d8e5e4','#8e9387','#f6ebd8',1.82);
    show('ExtRailHand',false);
    pose('ExtScenery',[u*8.8,0,0]);
    const jitter=.016*Math.sin(u*PI*4);
    cam([.55,1.76+jitter,.49],[-.46,1.58,2.74],47);
  } else if(id==='payphone'){
    s.light('#d1ded1','#738a7b','#eaf2ce',1.64);
    const k=turn(u,.02,.55),breath=.009*Math.sin(u*PI*3);
    pose('ExtReceiver',[-.59-.014*k,1.49+.035*k+breath,.82+.014*k],[.01*k,0,.036*k]);
    cam([-.72-.014*k,1.68+breath,1.67-.023*k],[-.18,1.63+.012*k,.105],47);
  } else if(id==='rooftops'){
    s.light('#8a98b4','#625d6a','#f7a76d',.72);
    cam([-9.3,11.84,8.5],[-1.2,8.35,-6.50],34);
  } else if(id==='wheel'){
    const roll=turn(u,.41,1);
    pose('ExtSedan',[-7.38-1.17*roll,.02,4.43]);
    const checking=turn(u,.06,.48);
    pose('ExtWheelHand',[-6.26+.47*checking,.56+.34*checking,5.38+.15*checking],[-.09,-.19,-.19-.29*checking]);
    const eye=[-5.42,.62,6.49];
    cam(eye,[-6.11-.33*roll,.52,5.25],34);
  } else if(id==='policy'){
    part('StreetPhil','head',.17-.18*turn(u,.1,.56),.25,-.018);
    part('StreetNed','head',.24-.26*ease(u),-.20,-.055);
    speak(u<.65?'StreetNed':'StreetPhil',u);
    cam([.29,1.58,3.39],[.12,1.52,.81],34);
  } else if(id==='waits'){
    const go=turn(u,.03,.42),back=turn(u,.55,.95);
    const d=go-back;
    const xx=.68+2.57*d,zz=.74+1.46*d;
    const vel=u<.45?1:-1;
    const yaw=blend(-.52,vel>0?1.09:-2.05,Math.min(1,d*4));
    const walk=Math.min(1,Math.abs(Math.sin(u*PI*2))*2);
    body('StreetNed',xx,zz,yaw,u*PI*9,walk);
    part('StreetNed','armL',-.4,0,.18);part('StreetNed','foreL',-.8);
    const bx=xx+.17*Math.cos(yaw)+.15*Math.sin(yaw),bz=zz+.15*Math.cos(yaw)-.17*Math.sin(yaw);
    pose('ExtPolicy',[bx,1.04,bz],[1.31,yaw,-.16]);
    reach('StreetNed','L',[bx,1.025,bz+.06],[.82,-.93,.08]);
    const pen=get('ExtBallpoint');
    if(pen){pen.visible=u>.53;const px=xx-.19,pz=zz+.18;pose('ExtBallpoint',[px,1.08,pz],[0,0,.69]);reach('StreetNed','R',[px,1.078,pz],[-.82,-.90,.08]);}
    part('StreetPhil','head',.026,.28+.43*d,.02);
    cam([1.13,1.66,6.12],[1.40,1.34,1.08],33);
  } else if(id==='signs'){
    const away=turn(u,.52,1);
    const xx=.00-1.79*away;
    body('StreetPhil',xx,.79,blend(.88,-1.25,away),u*PI*5,away);
    part('StreetPhil','head',.37*(1-away),.30,0);
    const ink=1-turn(u,.43,.56);
    part('StreetPhil','armL',-.76*ink,0,-.09);
    part('StreetPhil','foreL',-.64*ink,0,.19);
    part('StreetNed','head',.29-.27*turn(u,.38,1),-.24,.01);
    holdBook(.275,1.17,.995,-.22);
    const penX=.235+.049*ink*Math.sin(u*35),penZ=1.04-.038*ink*Math.cos(u*19);
    const handName=ink>.08?'StreetPhil.handR':'StreetNed.handR';
    if(ink>.08)reach('StreetPhil','R',[penX-.01,1.262,penZ+.005],[-.8,-.43,.35]);
    const grip=get(handName).localToWorld(new T.Vector3(0,-.089,.013));
    pose('ExtBallpoint',[grip.x+.015,grip.y-.033,grip.z],[.06,0,-1.14]);
    pose('ExtReceipt',[.266-.22*away-1.62*away,1.194-.09*away,1.00+.065*away],[.25+1.11*away,.14,-.03]);
    if(away>.10)reach('StreetPhil','L',[.27-.22*away-1.62*away,1.174-.09*away,1.01+.065*away],[.8,-.60,.15]);
    pose('ExtCarbon',[.271,1.188,.995],[.25,.13,-.03]);
    cam(mix([.13,1.54,2.06],[.37,1.64,3.71],ease(u)),mix([.13,1.22,1.05],[.38,1.46,.76],ease(u)),33);
  } else if(id==='follows'){
    show('StreetPhil',false);show('ExtReceipt',false);show('ExtBallpoint',false);
    const k=ease(u),near=turn(u,.67,1);
    const xx=blend(.68,6.34,k),zz=blend(.75,-.87,near);
    const yaw=blend(1.55,PI,near);
    body('StreetNed',xx,zz,yaw,u*PI*13,1);
    part('StreetNed','armL',-.32,0,.18);part('StreetNed','foreL',-.93);
    pose('ExtPolicy',[xx+.16*Math.sin(yaw),1.07,zz-.18*Math.sin(yaw)],[1.38,yaw,.06]);
    pose('ExtCarbon',[xx+.17*Math.sin(yaw),1.08,zz-.19*Math.sin(yaw)],[1.37,yaw,.06]);
    reach('StreetNed','L',[xx+.16*Math.sin(yaw),1.06,zz-.18*Math.sin(yaw)],[.45,-.96,.15]);
    const eye=[xx+blend(.13,-.48,k),1.64+.012*Math.sin(u*30),zz+blend(1.73,1.06,k)];
    cam(eye,[xx+.19-.16*near,1.54,zz-.04],37);
  }
}
