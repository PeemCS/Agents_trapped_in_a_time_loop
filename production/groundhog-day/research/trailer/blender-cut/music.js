import score from './piano-score.json' with {type:'json'};
// Shot-specific blocking for the practical miniatures authored in music.py.
const sat = n => Math.max(0, Math.min(1, n));
const smooth = n => { const x = sat(n); return x*x*(3-2*x); };
const mix = (a,b,t) => a + (b-a)*t;
const tau = Math.PI*2;
const prepared = new WeakMap();

function fetchNode(s, name) {
  return s.get(name) || s.get(name.replaceAll('.', '')) || s.get(name.replaceAll(' ', '_'));
}
function show(s,name,value) { const o=fetchNode(s,name); if(o)o.visible=value; }
function pose(s,name,x=0,y=0,z=0) { const o=fetchNode(s,name); if(o)o.rotation.set(x,y,z); }
function move(s,name,x,y,z) { const o=fetchNode(s,name); if(o)o.position.set(x,y,z); }

// Patina and fine fibres are procedural in object/world space. They stay on the
// actual wood and fabric through a camera move; the film grain is a separate pass.
function finishSurfaces(root) {
  const wood=new Set(['684631','352d2b','987250','86694f','8e7154','977a5a','9e805b','a28262','887058','ab8a65','76503a','755138','78543a','5d493b','664c38']);
  const cloth=new Set(['343d48','3d6958','435e61','313a47','414b54','405a50']);
  const paper=new Set(['bac1ad','abb7aa','b7b8a1']);
  const glass=new Set(['a8c0c4','526f80']);
  const polished=new Set(['c4a16a','898d87','e1c68e','c0bb9c','a4a298','65706a']);
  const seen=new Set();
  root.traverse(o=>{
    const m=o.material;if(!m?.isMeshStandardMaterial||seen.has(m))return;seen.add(m);
    const hex=m.color.getHexString();
    if(polished.has(hex)){m.roughness=.37;m.metalness=.24;}
    if(['ffda95','ffdd95','e1c68e'].includes(hex)){m.emissive.copy(m.color);m.emissiveIntensity=hex==='e1c68e'?.30:.79;}
    const style=wood.has(hex)?'wood':cloth.has(hex)?'cloth':paper.has(hex)?'paper':glass.has(hex)?'glass':'';
    if(!style)return;
    const effect={
      wood:`float knot=sin(w.x*7.1+w.z*4.8)+.24*sin(w.x*22.0-w.z*13.);float growth=sin(w.y*310.+w.z*93.+2.6*knot);float fibre=sin(w.y*922.+w.z*273.+7.1*knot);diffuseColor.rgb*=.99+.072*growth+.028*fibre+.040*sin(w.x*6.0+w.z*3.3);`,
      cloth:`float weave=sin(w.x*985.+w.z*580.)*sin(w.y*922.);diffuseColor.rgb*=1.+.052*weave;`,
      paper:`vec2 tile=fract(vec2(w.x+w.z,w.y)*vec2(3.4,3.35))-.5;float diamond=abs(abs(tile.x)*1.9+abs(tile.y)-.32);float filigree=1.-smoothstep(.014,.049,diamond);float wear=.019*sin(w.y*5.2+sin(w.x*3.7));diffuseColor.rgb*=1.-.126*filigree+wear;`,
      glass:`float streak=sin(w.y*41.+sin(w.x*28.)*.78)+.6*sin(w.x*92.+w.y*181.);diffuseColor.rgb*=1.+.025*streak;`}[style];
    m.onBeforeCompile=shader=>{
      shader.vertexShader='varying vec3 surfaceWorld;\n'+shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n surfaceWorld=(modelMatrix*vec4(transformed,1.)).xyz;');
      shader.fragmentShader='varying vec3 surfaceWorld;\n'+shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n{ vec3 w=surfaceWorld;'+effect+' }');
    };
    m.customProgramCacheKey=()=>`music-surface-${style}`;
    m.needsUpdate=true;
  });
}

function dress(s,rootName) {
  const root=fetchNode(s,rootName); if(!root) return {};
  if(prepared.has(root)) return prepared.get(root);
  finishSurfaces(root);
  const T=s.T, local={lights:[],glows:[]};
  const canvas=document.createElement('canvas'); canvas.width=canvas.height=64;
  const c=canvas.getContext('2d'), grad=c.createRadialGradient(32,32,0,32,32,32);
  grad.addColorStop(0,'rgba(255,246,208,.92)'); grad.addColorStop(.09,'rgba(255,206,110,.47)');
  grad.addColorStop(.28,'rgba(255,180,81,.15)'); grad.addColorStop(1,'rgba(255,168,79,0)');
  c.fillStyle=grad; c.fillRect(0,0,64,64);
  const tex=new T.CanvasTexture(canvas); tex.colorSpace=T.SRGBColorSpace;
  const glow=(x,y,z,size) => {
    const m=new T.SpriteMaterial({map:tex,color:0xffe2ac,transparent:true,depthWrite:false,opacity:.70,blending:T.AdditiveBlending});
    const g=new T.Sprite(m);g.position.set(x,y,z);g.scale.set(size,size,1);root.add(g);local.glows.push(g);
  };
  const light=(x,y,z,color,power,distance) => {
    const l=new T.PointLight(color,power,distance,2);l.position.set(x,y,z);root.add(l);local.lights.push(l);
  };
  if(rootName==='ballroom'){
    for(const x of [-3.5,-.88,.88,3.5])glow(x,2.48,-2.94,1.22);
    light(-.9,2.43,-2.68,0xffc076,3.4,5);light(1.02,2.4,-2.65,0xffb675,3.0,5);
  }else{
    glow(1.14,1.51,-1.13,.80);light(1.1,1.62,-.96,0xffce8c,3.4,4.4);
    light(12.85,2.23,-.70,0xffc990,3.5,4.2);
  }
  prepared.set(root,local);return local;
}

// A ten-note practice cell. Each strike moves one finger and depresses its key.

function piano(s,t,wide) {
  const notes=wide?score.reprise:score.practice;
  const rate=wide?2.0:3.0;
  const elapsed=Math.min(t,wide?4.46:5.62),phase=elapsed*rate;
  const steady=wide?1-smooth((t-4.33)/.26):1-smooth((t-5.43)/.43);
  const att=Math.floor(phase);
  for (const [hand,side] of ['L','R'].entries()) {
    const sign=hand===0?-1:1, wobble=.014*Math.sin(phase*.97+hand)*steady;
    move(s,'PianoHand'+side,sign*.185+wobble,.873+.003*Math.sin(phase*Math.PI)*steady,-2.21+.009*Math.sin(t*2.6+hand));
    show(s,'PianoHand'+side,true);
    for(let i=0;i<5;i++) {
      const index=hand*5+i;
      let strike=0;
      for(let ago=0;ago<3;ago++) if(notes[(att-ago+notes.length)%notes.length]===index){
        const a=(phase-att+ago);strike=Math.max(strike,Math.sin(Math.PI*sat(a/1.5))**1.1);
      }
      const held=(i===1||i===3)?.70:0;
      strike=mix(held,strike,steady);
      pose(s,'PianoFinger'+side+i,-strike*.41,0,(i-2)*.04*sign);
      const keyIndex=Math.round((sign*.185+sign*[-.09,-.043,0,.042,.07][i]+.73)/.0286);
      const key=fetchNode(s,'whiteKey'+String(keyIndex).padStart(2,'0'));
      if(key){key.position.y=.81-.010*strike;key.rotation.x=.023*strike;}
    }
  }
}

function ballroomShot(id,u,s) {
  const close=id==='pianoHands';
  const local=dress(s,'ballroom');
  for(const l of local.lights||[])l.intensity=close?1.35:4.4;
  for(const g of local.glows||[])g.material.opacity=close?.23:.74;
  s.light(close?0xd2e1ed:0xf4d8b6,close?0x857b73:0x8e6e5c,close?0xffe5c9:0xffcf91,close?1.5:1.67);
  show(s,'BallPhil',!close);show(s,'BallRita',!close);show(s,'BallRitaSeated',false);
  show(s,'RitaChair',true);
  if(close) {
    const t=u*6.5;
    piano(s,t,false);
    // Breathing and a shift toward the treble hand retain the seated anchor.
    s.cam([.009*Math.sin(t*1.05),1.25+.004*Math.sin(t*2),-1.455],
      [.014+.035*smooth((t-2.1)/1.8)-.021*smooth((t-4.9)/1.2),.846+.011*Math.sin(t*.56),-2.267],57);
    return;
  }
  const t=id==='chair'?2*u:2+4*u;
  const pull=smooth((t-.19)/1.49), sit=smooth((t-1.67)/1.03);
  show(s,'BallRita',sit<.82);show(s,'BallRitaSeated',sit>=.82);
  move(s,'RitaChair',mix(-1.43,-.92,pull),0,mix(-1.03,-1.17,pull));
  pose(s,'RitaChair',0,mix(1.50,1.68,pull),0);
  move(s,'BallRita',mix(-1.58,-.92,pull),-.31*sit,mix(-.80,-1.13,pull));
  pose(s,'BallRita',-.09-.15*sit,mix(1.53,1.78,pull),0);
  pose(s,'BallRita.armR',-.46,0,.18); pose(s,'BallRita.foreR',-.88,0,.09);
  pose(s,'BallRita.head',.16*(1-sit),.28,0);
  move(s,'BallRitaSeated',-.92,0,-1.17);pose(s,'BallRitaSeated',0,1.78,0);
  pose(s,'BallRitaSeated.head',.06+.037*Math.sin(t*2.6),-.23+.15*smooth((t-3.1)/.8),.05);
  pose(s,'BallRitaSeated.armR',-.25,0,.24);pose(s,'BallRitaSeated.foreR',-.80,0,.19);
  pose(s,'BallRitaSeated.armL',-.34,0,-.19);pose(s,'BallRitaSeated.foreL',-.68,0,-.14);
  const turn=smooth((t-1.1)/.72)*.14 + smooth((t-3.05)/1.1)*.17;
  pose(s,'BallPhil',0,Math.PI-.27,0);
  pose(s,'BallPhil.head',.15-.12*turn,turn,.014*Math.sin(t*1.3));
  for(const side of ['L','R']){
    pose(s,'BallPhil.arm'+side,-.48,.0,side==='L'?.06:-.06);
    show(s,'BallPhil.fore'+side,false);
  }
  piano(s,t,true);
  s.cam([2.28,1.45,-.78],[-.34,1.07,-1.83],39);
}

function boothShot(id,u,s) {
  dress(s,'booth');const mixRoom=id==='switcher';
  s.light(mixRoom?0xb9c7c7:0xcedad4,0x66645e,mixRoom?0xffc98d:0xffddb5,mixRoom?1.72:1.64);
  if(!mixRoom){
    const reach=smooth((u-.1)/.56),receive=smooth((u-.52)/.36);
    pose(s,'BoothLarry.head',.16,.21-.12*reach,-.04);pose(s,'BoothRita.head',.16-.045*receive,-.29,.04);
    pose(s,'BoothLarry.armL',-.68-.38*reach,0,.13);pose(s,'BoothLarry.foreL',-.72,0,.34);
    pose(s,'BoothRita.armR',-.46-.45*receive,0,-.17);pose(s,'BoothRita.foreR',-.88,0,-.28);
    move(s,'LarryCassette',-.17+.46*reach,1.14+.13*Math.sin(u*Math.PI),-.29);
    pose(s,'LarryCassette',-.40,-.22+.51*reach,.15-.30*receive);
    for(let i=0;i<2;i++)pose(s,'FilmReel'+i,0,0,u*.62*(i?1:-1));
    s.cam([-1.48,1.54,1.22],[.06,1.39,-.64],41);
    return;
  }
  const press=smooth((u-.24)/.31),release=smooth((u-.67)/.26),hold=press-.7*release;
  pose(s,'StationRita.head',.30,.11,-.045);
  pose(s,'StationRita.armR',-.62,0,-.43);show(s,'StationRita.foreR',false);
  pose(s,'StationRita.armL',-.49,0,.055);pose(s,'StationRita.foreL',-.67);
  move(s,'WireHand',12.47,1.332-hold*.074,-.815-.012*hold);
  pose(s,'WireHand',-.13*hold,0,.035);
  const key=fetchNode(s,'WireSwitch');if(key)key.position.y=1.246-.012*hold;
  for(let i=0;i<2;i++)pose(s,'VuNeedle'+i,0,0,.69-press*(.87+.24*Math.sin(23*u+i)));
  const lamp=fetchNode(s,'TransmissionLamp');if(lamp?.material){lamp.material.emissive?.setHex(0xffc06d);lamp.material.emissiveIntensity=.12+1.25*press;}
  s.cam([11.01,1.89,-.10],[12.18,1.216,-1.035],39);
}

export function shot(id,u,s) {
  if(id==='pianoHands'||id==='chair'||id==='twoBars')ballroomShot(id,u,s);
  else boothShot(id,u,s);
}
