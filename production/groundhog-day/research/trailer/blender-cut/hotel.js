// Performance and camera blocking for the Hearthside negative.
// Stage coordinates and shot progress are absolute, so a frame can be rendered in isolation.
const clamp = (x) => Math.max(0, Math.min(1, x));
const ease = (a,b,t) => {const x=clamp((t-a)/(b-a));return x*x*(3-2*x);};
const mix = (a,b,t) => a+(b-a)*t;
const blend = (a,b,t) => a.map((v,i)=>mix(v,b[i],t));
const radians = Math.PI/180;
const bedIDs=new Set(['bedNight','wake','clock','reset','faresPocket','curtain','curled','shoe','warmWake','warmClock']);
const bedProps=['BedHandL','BedHandR','ReachClock','CurtainHandL','CurtainHandR','BedPhil','ShoePhil','PocketInsert','PocketHand','ReachClockBridge','CurtainHandLBridge','CurtainHandRBridge'];
const lobbyProps=['LobbyRita','LobbyLarry','LarryCase','LobbyNed','FareLeft','FareRight','PaidTicket','LobbyGreetingHand','RitaBoard','BlueCarbon','CarbonOriginal','FareCash','FareEnvelope'];
function at(s,name,pos,rot){
  const o=s.get(name);if(!o)return;
  if(pos)o.position.set(...pos);
  if(rot)o.rotation.set(...rot);
  return o;
}
function show(s,props,active){for(const n of props){const o=s.get(n);if(o)o.visible=active.includes(n);}}
function localLamp(s,node,id,pos,color,power,range){
  const anchor=s.get(node);if(!anchor)return;
  let lamp=anchor.getObjectByName(id);
  if(!lamp){lamp=new s.T.PointLight(color,power,range,2);lamp.name=id;lamp.position.set(...pos);anchor.add(lamp);}
  lamp.color.set(color);lamp.intensity=power;
}
function tint(s,name,base,emit,power){
  const o=s.get(name);if(!o)return;
  o.traverse(child=>{if(!child.isMesh||Array.isArray(child.material))return;const m=child.material;
    m.color.set(base);if(m.emissive){m.emissive.set(emit);m.emissiveIntensity=power;}
  });
}
function windowLight(s,mood){
  const settings={night:['#213741','#476375',.42],cold:['#9dbcbe','#c3e4ef',1.30],warm:['#e9c899','#ffdea0',1.45],shut:['#6f827e','#9daad0',.3],dusk:['#92908b','#deb18e',.42]};
  const [base,emission,strength]=settings[mood];
  for(const b of ['BayLeft','BayCenter','BayRight']){
    tint(s,b+'Glass',base,emission,strength);
    const f=s.get(b+'Frost');if(f)f.visible=mood!=='night';
  }
  const dark=mood==='night',gold=mood==='warm',closed=mood==='shut',dusk=mood==='dusk';
  s.light(dark?'#5c789a':gold?'#ffe2b6':closed?'#a39f99':dusk?'#af9b92':'#dfedf3', dark?'#493d42':gold?'#bd9b7b':closed?'#776677':'#998c8a',gold?'#ffcd91':dark?'#e1ab79':'#e6ddc6',dark?.23:gold?2.55:closed?.74:1.68);
  localLamp(s,'BedroomArchitecture','LampLight',[1.54,1.56,1.94],'#ffbb78',dark?4.8:gold?1.7:closed?.12:1.2,5.0);
  localLamp(s,'BedroomArchitecture','BayLight',[-.9,2.13,-1.93],gold?'#ffcc83':'#aecfde',dark?.13:closed?.53:gold?9.8:6.1,7.5);
  tint(s,'BedLampPleatedSilk',dark?'#daaa7d':'#ead0aa','#ffc486',dark?.69:.15);
}
function curtains(s,t){
  for(const [name,dir] of [['DrawCurtainL',-1],['DrawCurtainR',1]]){
    const o=s.get(name);if(!o)continue;
    // The inner edge travels a full metre while the outer hem remains at the casing.
    o.position.x=dir*mix(1.04,.596,t);o.scale.x=mix(1,3.0,t);
  }
}
const eye=[-.22,1.102,1.605];
function connectSleeve(s,name,shoulder){
  const wrist=s.get(name),sleeve=s.get(name+'Bridge');if(!wrist||!sleeve)return;
  const a=new s.T.Vector3(...shoulder),b=new s.T.Vector3(0,-.003,.052).applyQuaternion(wrist.quaternion).add(wrist.position);
  const d=b.clone().sub(a);sleeve.visible=true;sleeve.position.copy(a).lerp(b,.5);sleeve.scale.y=d.length();
  sleeve.quaternion.setFromUnitVectors(new s.T.Vector3(0,1,0),d.normalize());
}
function waking(id,u,s){
  const dark=id==='bedNight',warm=id.startsWith('warm'),turn=id==='clock'||id==='warmClock';
  windowLight(s,dark?'night':warm?'warm':'cold');curtains(s,0);
  show(s,bedProps,turn?['BedHandL','BedHandR','ReachClock']:['BedHandL','BedHandR']);
  const slow=turn?ease(.035,.74,u):0;
  const angle=slow*95*radians;
  const head=[eye[0],eye[1]+.007*Math.sin(Math.PI*u)*(turn?.55:1),eye[2]];
  const target=[head[0]+Math.sin(angle)*2.5,head[1]+mix(.12,-.237,slow),head[2]-Math.cos(angle)*2.5];
  s.cam(head,target,52.5);
  for(const [side,sign] of [['L',-1],['R',1]]){
    const fading=turn&&side==='R';const o=s.get('BedHand'+side);if(fading)o.visible=u<.30;
    at(s,'BedHand'+side,[-.22+sign*.285,.864+.022*Math.sin(Math.PI*u)+(dark?.095*(1-ease(.08,.76,u)):0),.94],[-.04,sign*.20,sign*.055]);
  }
  if(turn){
    const reach=ease(.26,.74,u),release=ease(.78,1,u);const p=blend(blend([.05,.82,1.24],[1.00,1.12,1.996],reach),[.80,.89,2.01],release);
    const h=at(s,'ReachClock',p,[.12,-mix(.14,.72,reach),-.19]);h.visible=u>=.29;if(h.visible)connectSleeve(s,'ReachClock',[-.12,.52,2.02]);
  }
}
function coatPocket(u,s){
  windowLight(s,'night');curtains(s,.16);show(s,bedProps,['PocketInsert','PocketHand']);
  at(s,'PocketInsert',[-.30,.92,.76],[-.88,-.08,-.055]);
  const take=ease(.12,.81,u),press=ease(.63,.92,u);
  at(s,'PocketBill',[.15,.058-.075*take,.142-.012*press],[-.10,-.02,-.16]);
  at(s,'PocketHand',[.034-.11*take,1.074-.067*take,.959-.026*take],[.19,-.64,-.17]);
  s.cam([-.17,1.63,1.30],[-.22,.965,.76],43);
}
const roomWideEye=[-2.48,1.79,-.86],roomWideAim=[-.14,.99,1.16];
function lying(s){
  // His feet point down the bed and his head reaches the pillow, one shoulder rolled toward camera.
  at(s,'BedPhil',[-.26,.957,.29],[1.48,-1.91,-.055]);
  at(s,'BedPhil.legL',null,[-.45,0,-.04]);at(s,'BedPhil.legR',null,[-.09,0,.05]);
  at(s,'BedPhil.armL',null,[-.76,0,-.26]);at(s,'BedPhil.foreL',null,[-.75,.14,.17]);
  at(s,'BedPhil.armR',null,[-.49,0,.16]);at(s,'BedPhil.foreR',null,[-.83,.18,-.15]);
  at(s,'BedPhil.head',null,[.04,.09,.02]);
}
function tieLaces(s,u){
  const {T}=s,shoe=s.get('ShoePhil.shoeL');shoe.updateWorldMatrix(true,false);
  const tie=shoe.localToWorld(new T.Vector3(0,.38,.14));
  for(const [side,sign] of [['L',1],['R',-1]]){
    const arm=s.get('ShoePhil.arm'+side),fore=s.get('ShoePhil.fore'+side);
    arm.parent.updateWorldMatrix(true,false);
    const a=arm.position.clone(),goal=arm.parent.worldToLocal(tie.clone());goal.x+=sign*(.043+.036*ease(.29,.76,u));
    const dir=goal.sub(a).normalize(),l1=fore.position.length(),l2=.248;
    const distance=Math.min(l1+l2-.001,a.distanceTo(arm.parent.worldToLocal(tie.clone())));
    const along=(l1*l1-l2*l2+distance*distance)/(2*distance),away=Math.sqrt(Math.max(0,l1*l1-along*along));
    const pole=new T.Vector3(sign,-.4,-.25);pole.addScaledVector(dir,-dir.dot(pole)).normalize();
    const elbow=dir.clone().multiplyScalar(along).addScaledVector(pole,away);
    arm.quaternion.setFromUnitVectors(fore.position.clone().normalize(),elbow.clone().normalize());
    const foreDir=dir.multiplyScalar(distance).sub(elbow).applyQuaternion(arm.quaternion.clone().invert()).normalize();
    fore.quaternion.setFromUnitVectors(new T.Vector3(0,-.244,.01).normalize(),foreDir);
  }
}
function curtainScene(id,u,s){
  const poseShoe=id==='shoe';const pulling=id==='curtain';const close=pulling?ease(.025,.47,u):1;
  windowLight(s,poseShoe?'dusk':close>.75?'shut':'cold');curtains(s,close);
  const before=pulling&&u<.51;
  show(s,bedProps,before?['CurtainHandL','CurtainHandR']:poseShoe?['ShoePhil']:['BedPhil']);
  if(before){
    // The crushed velvet crosses the optical axis before the viewpoint leaves Phil's eyes.
    for(const [side,sign] of [['L',-1],['R',1]]){
      at(s,'CurtainHand'+side,[sign*mix(.70,.057,close),mix(1.76,1.57,close),-2.08],[.31,sign*-.17,sign*.12]);
      connectSleeve(s,'CurtainHand'+side,[sign*.24,1.11,-1.21-.44*ease(.36,.51,u)]);
    }
    s.cam([0,1.63,-1.34-.55*ease(.36,.51,u)],[0,1.59,-2.42],53);return;
  }
  if(pulling){
    const a=ease(.51,.96,u),step=ease(.51,.74,u),sit=ease(.74,.96,u);lying(s);
    at(s,'BedPhil',blend([mix(-.57,-1.17,step),.009*Math.sin(step*Math.PI*4),mix(-1.10,.44,step)],[-.26,.957,.29],sit),[1.48*sit,mix(.02,-1.91,sit),-.055*sit]);
    if(sit<.94){
      at(s,'BedPhil.legL',null,[.24*Math.sin(step*Math.PI*4)*(1-sit)-.45*sit,0,-.04]);
      at(s,'BedPhil.legR',null,[-.24*Math.sin(step*Math.PI*4)*(1-sit)-.09*sit,0,.05]);
      at(s,'BedPhil.armL',null,[-.15-.61*sit,0,-.26*sit]);at(s,'BedPhil.armR',null,[-.11-.38*sit,0,.16*sit]);
    }
    // A close fold hides the cut. The wide begins near his shoulder then settles outside the bed.
    s.cam(blend([-.77,1.42,-1.42],roomWideEye,a),blend([-.57,1.34,-.75],roomWideAim,a),51);return;
  }
  s.cam(roomWideEye,roomWideAim,51);
  if(!poseShoe){lying(s);const b=s.get('BedPhil');b.position.y+=.008*Math.sin(u*4.8);}
  else{
    at(s,'ShoePhil',[-1.03,.20,1.18],[.03,-1.86,.009]);
    at(s,'ShoeTorso',null,[.68+.05*Math.sin(u*3.3),0,0]);at(s,'ShoePhil.head',null,[.29,.09,0]);
    const pull=ease(.2,.67,u);at(s,'ShoePhil.armL',null,[-.77-.16*pull,0,-.10]);at(s,'ShoePhil.foreL',null,[.23+.06*pull,0,.05]);
    at(s,'ShoePhil.armR',null,[-.76+.18*pull,0,.14]);at(s,'ShoePhil.foreR',null,[.21,0,-.08]);
    at(s,'ShoePhil.legL',null,[-.68,0,-.27]);tieLaces(s,u);
  }
}
function lobbyLight(s){
  s.light('#e2d8c6','#a28b77','#f5d7ad',2.14);
  localLamp(s,'LobbyArchitecture','DeskSconceLight',[2.46,2.03,-.79],'#ffc88c',6.2,6.4);
  localLamp(s,'LobbyArchitecture','WinterDoors',[.25,1.97,2.85],'#b8d7e5',8.8,7);
}
function gesture(s,who,side,upper,lower){at(s,who+'.arm'+side,null,upper);at(s,who+'.fore'+side,null,lower);}
function talk(s,who,strength,t){
  const mouth=s.get(who+'.mouth');if(mouth)mouth.scale.y*=1+strength*(.45+.55*Math.abs(Math.sin(t*11)))*1.2;
}
function departing(u,s){
  show(s,lobbyProps,['LobbyRita','LobbyLarry','LarryCase','FareLeft','PaidTicket','FareEnvelope','FareCash']);
  at(s,'LobbyRita',[-.68,0,2.01],[0,-2.75+.23*ease(.14,.55,u),0]);
  gesture(s,'LobbyRita','L',[-.24,0,-.72],[0,0,-.07]);gesture(s,'LobbyRita','R',[-.45,0,.35],[-.65,0,.10]);
  at(s,'LobbyRita.head',null,[.01,.35-.69*ease(.25,.86,u),.025]);
  const step=ease(.10,.95,u);
  at(s,'LobbyLarry',[.11+.20*step,Math.sin(u*12)*.012,2.20+.61*step],[0,.16,0]);
  at(s,'LobbyLarry.legL',null,[.17*Math.sin(u*10.3),0,0]);at(s,'LobbyLarry.legR',null,[-.17*Math.sin(u*10.3),0,0]);
  at(s,'LarryCase',[-.22+.20*step,.59,2.20+.61*step],[0,.13,.04]);
  const pan=ease(.56,1,u);const from=[1.20,1.61,.36],target=blend([-.05,1.38,2.48],[1.95,1.20,.39],pan*.89);
  s.cam(from,target,51);
  at(s,'FareLeft',[1.05,1.31,.77],[.34,2.65,-.11]);at(s,'PaidTicket',[1.07,1.35,.82],[-.34,-2.52,.10]);
}
function takeMoney(u,s){
  show(s,lobbyProps,['FareEnvelope','FareCash','FareLeft','FareRight']);
  const free=ease(.07,.59,u),leave=ease(.57,.97,u);
  // Reach in, slide the folded note clear of the envelope and draw it toward the coat.
  at(s,'FareCash',[1.997-.23*free-.22*leave,1.182+.061*free+.10*leave,.376+.028*free+.079*leave],[-Math.PI/2+.61*leave,-.035,.14-1.43*free]);
  at(s,'FareLeft',[1.85,1.20,.614],[-.11,-.95,-.05]);
  at(s,'FareRight',[1.90+.043*(1-free)-.17*free-.23*leave,1.208+.049*free+.09*leave,.277+.051*free+.078*leave],[.08,-1.30,-.11]);
  s.cam([1.25,1.68,.40],[1.96,1.165,.38],41);
}
function greet(u,s){
  show(s,lobbyProps,['LobbyRita','RitaBoard','LobbyGreetingHand','FareEnvelope']);
  const turn=ease(.59,.96,u),walk=ease(.72,1,u);const rita=[-.15+.24*walk,0,.30+.40*walk];
  at(s,'LobbyRita',rita,[0,-2.46+1.57*turn,0]);
  at(s,'LobbyRita.head',null,[-.045,.08+.19*ease(.19,.48,u),.025]);
  gesture(s,'LobbyRita','L',[-.62,0,-.19],[-.83,0,-.07]);gesture(s,'LobbyRita','R',[-.29,0,.18],[-.39,0,.17]);
  at(s,'RitaBoard',[rita[0]-.12,1.13,rita[2]-.22],[.05,-2.4+turn*1.55,-.13]);
  const hesitation=Math.sin(Math.PI*ease(.15,.71,u));at(s,'LobbyGreetingHand',[-1.22,1.00+.29*hesitation,-.48],[.03,2.85,.10]);
  talk(s,'LobbyRita',u<.30?.82:0,u*5.1);
  s.cam([-1.38,1.58,-.74],[-.12,1.27,.32],47);
}
function deskConversation(u,s){
  show(s,lobbyProps,['LobbyNed','LobbyRita','BlueCarbon','CarbonOriginal','FareEnvelope']);
  const settle=ease(0,.32,u),peel=ease(.49,.71,u),lookup=ease(.70,.91,u);
  const ned=[.16+.37*settle,.012*Math.sin(Math.PI*settle),.49-.10*settle];
  const rita=[1.44,0,.27];
  at(s,'LobbyNed',ned,[0,mix(1.61,1.09,settle),0]);
  at(s,'LobbyRita',rita,[0,-1.06,0]);
  at(s,'LobbyRita.head',null,[-.035+.10*(1-lookup),-.12+.15*lookup,-.032]);
  at(s,'LobbyNed.head',null,[.22*(1-lookup)-.03, .10*(1-settle)-.11*lookup,-.04]);
  gesture(s,'LobbyNed','L',[-.65,0,-.27],[-.68,0,.08]);
  gesture(s,'LobbyNed','R',[-.72+.10*peel,0,.15],[-.66,0,-.25-.2*peel]);
  gesture(s,'LobbyRita','L',[-.13,0,-.08],[-.42,0,-.10]);
  at(s,'BlueCarbon',[ned[0]+.23,1.12+.045*peel,ned[2]+.245],[.16,.60-.52*peel,-.13]);
  at(s,'CarbonOriginal',[ned[0]+.247,1.115,ned[2]+.198-.092*peel],[.18-.27*peel,.62+.23*peel,-.13-.12*peel]);
  talk(s,'LobbyRita',u<.25?1:0,u*4.8);talk(s,'LobbyNed',u>.24?.78:0,u*5.5);
  s.cam(blend([.31,1.51,2.58],[1.10,1.51,2.03],settle),blend([.93,1.25,.39],[.96,1.40,.33],settle),37);
}
export function shot(id,u,s){
  if(bedIDs.has(id)){
    if(id==='faresPocket')coatPocket(u,s);
    else if(['curtain','curled','shoe'].includes(id))curtainScene(id,u,s);
    else waking(id,u,s);
  }else{
    lobbyLight(s);
    if(id==='faresBye')departing(u,s);
    else if(id==='faresTake')takeMoney(u,s);
    else if(id==='greeting')greet(u,s);
    else deskConversation(u,s);
  }
}
