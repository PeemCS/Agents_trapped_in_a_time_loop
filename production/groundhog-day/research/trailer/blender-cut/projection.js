import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {cut,unitFor,fps} from './edit.js';

const params=new URLSearchParams(location.search), W=+(params.get('w')||1920), H=+(params.get('h')||824);
const canvas=document.querySelector('#picture');
const renderer=new T.WebGLRenderer({canvas,antialias:false,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
renderer.setSize(W,H,false);
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=T.PCFSoftShadowMap;
renderer.toneMapping=T.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.22;
const frameBuffer=new T.WebGLRenderTarget(W,H,{type:T.HalfFloatType,samples:4});
frameBuffer.depthTexture=new T.DepthTexture(W,H,T.UnsignedIntType);
const scene=new T.Scene(), camera=new T.PerspectiveCamera(42,W/H,.018,220);
const sky=new T.HemisphereLight(0xcfdbe3,0x817073,1.4);
const sun=new T.DirectionalLight(0xffe4be,2.8), bounce=new T.DirectionalLight(0xd2dce6,.95);
scene.add(sky,sun,sun.target,bounce,bounce.target);
sun.castShadow=true; sun.shadow.mapSize.set(2048,2048);
sun.shadow.camera.near=.1; sun.shadow.camera.far=70;
sun.shadow.normalBias=.009; sun.shadow.bias=-.00016;
const post=new T.Scene(), postCam=new T.OrthographicCamera(-1,1,1,-1,0,1);
const grading=new T.ShaderMaterial({
 uniforms:{pic:{value:frameBuffer.texture},depth:{value:frameBuffer.depthTexture},res:{value:new T.Vector2(W,H)},moment:{value:0},closing:{value:0},focus:{value:1},aperture:{value:0}},
 vertexShader:'varying vec2 p;void main(){p=uv;gl_Position=vec4(position.xy,0.,1.);}',
 fragmentShader:`
 varying vec2 p;uniform sampler2D pic;uniform sampler2D depth;uniform vec2 res;uniform float moment;uniform float closing;uniform float focus;uniform float aperture;
 float z(vec2 q){float v=texture2D(depth,q).r;return .018*220./(220.-v*(220.-.018));}
 float noise(vec2 v){return fract(sin(mod(dot(v,vec2(127.1,311.7)),983.71))*43758.5453);}
 void main(){
  vec2 uv=p;vec3 rgb=texture2D(pic,uv).rgb;float dist=z(uv),shade=0.;
  float rad=clamp(res.y*.095/max(.35,dist),2.,32.);
  for(int k=0;k<12;k++){
   float a=float(k)*2.39996;vec2 off=vec2(cos(a),sin(a))*sqrt((float(k)+.6)/12.)*rad/res;
   float delta=dist-z(uv+off);
   shade+=smoothstep(.008,.065,delta)*(1.-smoothstep(.09,.47,delta));
  }
  // Finite-aperture focus keeps near faces and hands distinct from the far set.
  float coc=min(5.2,abs(1./max(.24,dist)-1./max(.24,focus))*aperture)*res.y/824.;
  if(coc>.30){
    vec3 blur=rgb*2.;float weight=2.;
    for(int k=0;k<14;k++){
      float a=float(k)*2.39996;vec2 q=uv+vec2(cos(a),sin(a))*sqrt((float(k)+.7)/14.)*coc/res;
      float nd=z(q),w=nd<dist-.05?.35:1.;blur+=texture2D(pic,q).rgb*w;weight+=w;
    }
    rgb=mix(rgb,blur/weight,smoothstep(.3,1.1,coc));
  }
  rgb*=1.-.31*shade/12.;
  rgb*=1.-.16*smoothstep(.18,.73,length(uv-.5));
  gl_FragColor=vec4(rgb,1.);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  float l=dot(gl_FragColor.rgb,vec3(.2126,.7152,.0722));
  gl_FragColor.rgb=mix(vec3(l),gl_FragColor.rgb,.94);
  gl_FragColor.rgb+=(noise(floor(uv*res)+vec2(moment*17.,moment*3.))-.5)*.025;
  gl_FragColor.rgb*=1.-closing;
 }`
});
post.add(new T.Mesh(new T.PlaneGeometry(2,2),grading));
const loader=new GLTFLoader(), units={}, roots={}, lookup={}, originals=new Map();
let currentRoot,shotId,currentUnit,touched=new Set(),recordTouches;
const v=(a)=>new T.Vector3(...a);
const aim=new T.Vector3();
const api={T,
 get(name){const obj=lookup[currentRoot]?.get(name);if(obj){touched.add(obj);if(recordTouches)recordTouches.add(obj);}return obj;},
 cam(eye,target,fov=42){camera.position.copy(v(eye));aim.copy(v(target));camera.fov=fov;camera.updateProjectionMatrix();camera.up.set(0,1,0);camera.lookAt(aim);},
 light(top,ground,key,intensity=2.8){sky.color.set(top);sky.groundColor.set(ground);sun.color.set(key);sun.intensity=intensity;}
};

function resetObjects(){
 for(const o of touched){
  const b=originals.get(o);
  if(b){o.position.copy(b[0]);o.quaternion.copy(b[1]);o.scale.copy(b[2]);o.visible=b[3];}
 }
 touched.clear();
}

// Merge static surfaces inside each moving part. Named animation controls stay independent.
function pack(root,moving){
 root.updateMatrixWorld(true);
 const buckets=new Map();
 root.traverse(o=>{
  if(!o.isMesh||moving.has(o)||Array.isArray(o.material)||o.children.length)return;
  let anchor=o.parent;
  while(anchor!==root&&!moving.has(anchor))anchor=anchor.parent;
  const casts=o.castShadow;
  const key=[anchor.uuid,o.material.uuid,casts].join('.');
  if(!buckets.has(key))buckets.set(key,{anchor,material:o.material,casts,meshes:[]});
  buckets.get(key).meshes.push(o);
 });
 for(const {anchor,material,casts,meshes} of buckets.values()){
  if(meshes.length<2)continue;
  const inverse=anchor.matrixWorld.clone().invert();
  const batch=meshes.map(o=>{
   let g=o.geometry.index?o.geometry.toNonIndexed():o.geometry.clone();
   for(const attr of Object.keys(g.attributes))if(attr!=='position'&&attr!=='normal')g.deleteAttribute(attr);
   g.applyMatrix4(new T.Matrix4().multiplyMatrices(inverse,o.matrixWorld));return g;
  });
  const g=mergeGeometries(batch),combined=new T.Mesh(g,material);
  combined.castShadow=casts;combined.receiveShadow=true;anchor.add(combined);
  meshes.forEach(o=>o.removeFromParent());batch.forEach(g=>g.dispose());
 }
}

const snowGeo=new T.BufferGeometry(),flakeCount=3400,snowPos=new Float32Array(flakeCount*3);
let seed=94183; const rand=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
for(let i=0;i<flakeCount;i++){snowPos[i*3]=(rand()-.5)*30;snowPos[i*3+1]=rand()*12;snowPos[i*3+2]=(rand()-.5)*28;}
snowGeo.setAttribute('position',new T.BufferAttribute(snowPos,3));
const snowMat=new T.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{t:{value:0},scale:{value:H/824}},vertexShader:`
 uniform float t;uniform float scale;varying float strength;
 void main(){vec3 p=position;p.y=mod(p.y-t*.80,12.);p.x+=sin(p.y*.7+p.z)*.20+t*.12;
 vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(19./max(.5,-mv.z),1.,5.)*scale;strength=clamp(1.+mv.z/25.,.1,.87);}
 `,fragmentShader:`varying float strength;void main(){float r=length(gl_PointCoord-.5);gl_FragColor=vec4(.88,.94,.98,(1.-smoothstep(.14,.5,r))*strength*.65);}`});
const snow=new T.Points(snowGeo,snowMat);snow.frustumCulled=false;scene.add(snow);
const card=document.createElement('canvas');card.width=W;card.height=H;
const ctx=card.getContext('2d');
const cardTex=new T.CanvasTexture(card);cardTex.colorSpace=T.SRGBColorSpace;
const cards=new T.Scene();cards.add(new T.Mesh(new T.PlaneGeometry(2,2),new T.MeshBasicMaterial({map:cardTex,toneMapped:false,depthTest:false})));
let previousCard;
function cardFrame(id){
 if(previousCard!==id){
  ctx.fillStyle='#090b0e';ctx.fillRect(0,0,W,H);
  if(id!=='black'){
   const text=id==='chapterOne'?'I.   SPEEDRUN THE SCRIPT':'II.   ESCAPE THE MAP';
   ctx.font='500 '+(W*.028)+'px Georgia';ctx.textBaseline='middle';ctx.textAlign='center';ctx.fillStyle='#e9e1cf';
   ctx.fillText(text,W/2,H/2);
  }
  cardTex.needsUpdate=true;previousCard=id;
 }
 renderer.setRenderTarget(null);renderer.render(cards,postCam);
}

const textured=new WeakSet();
function finishSurface(m){
 if(!m?.isMeshStandardMaterial||textured.has(m))return;
 textured.add(m);
 const previous=m.onBeforeCompile;
 m.onBeforeCompile=function(shader,renderer){
  previous.call(this,shader,renderer);
  shader.vertexShader='varying vec3 surfacePoint;\n'+shader.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nsurfacePoint=transformed*vec3(length(modelMatrix[0].xyz),length(modelMatrix[1].xyz),length(modelMatrix[2].xyz));');
  shader.fragmentShader=`varying vec3 surfacePoint;
   float hashGrid(vec3 p){p=fract(p*.1031);p+=dot(p,p.yxz+33.33);return fract((p.x+p.y)*p.z);}
   float patina(vec3 p){
    vec3 cell=floor(p),f=fract(p);f=f*f*(3.-2.*f);
    return mix(mix(mix(hashGrid(cell),hashGrid(cell+vec3(1,0,0)),f.x),mix(hashGrid(cell+vec3(0,1,0)),hashGrid(cell+vec3(1,1,0)),f.x),f.y),
               mix(mix(hashGrid(cell+vec3(0,0,1)),hashGrid(cell+vec3(1,0,1)),f.x),mix(hashGrid(cell+vec3(0,1,1)),hashGrid(cell+vec3(1,1,1)),f.x),f.y),f.z);
   }\n`+shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
    float mottling=patina(surfacePoint*8.)-.5;float fibre=patina(surfacePoint*vec3(140.,66.,119.))-.5;
    diffuseColor.rgb*=1.+.105*mottling+.090*fibre;`);
 };
 m.customProgramCacheKey=()=>'miniatureSurface';
}
async function loadUnit(name){
 if(units[name])return;
 const [{scene:model},logic]=await Promise.all([loader.loadAsync(name+'.glb'),import('./'+name+'.js')]);
 units[name]=logic;
 for(const root of [...model.children]){
  const key=root.userData.name||root.name;
  roots[key]=root;root.visible=false;scene.add(root);lookup[key]=new Map();
  root.traverse(o=>{
   const label=o.userData.name||o.name;
   lookup[key].set(label,o);
   originals.set(o,[o.position.clone(),o.quaternion.clone(),o.scale.clone(),o.visible]);
   if(o.isMesh){
    (Array.isArray(o.material)?o.material:[o.material]).forEach(finishSurface);
    o.castShadow=!/ceiling|backdrop|sky dome/i.test(label);
    o.receiveShadow=true;
   }
  });
  currentRoot=key;
  const moved=new Set();recordTouches=moved;
  for(const shot of cut.filter(c=>c.root===key))for(const u of [0,.12,.35,.48,.65,.9,1]){
   logic.shot(shot.id,u,api);resetObjects();
  }
  recordTouches=null;pack(root,moved);
 }
}

function paint(frame){
 const c=cut.findLast(s=>s.frame<=frame),i=cut.indexOf(c);
 const next=cut[i+1]?.frame||2592;
 const u=Math.min(1,(frame-c.frame)/Math.max(1,next-c.frame-1));
 resetObjects();
 if(!c.root){cardFrame(c.id);return;}
 if(currentRoot!==c.root||!roots[c.root].visible){
  Object.values(roots).forEach(o=>o.visible=false);roots[c.root].visible=true;
 }
 currentRoot=c.root;shotId=c.id;currentUnit=unitFor[currentRoot];
 const outside=currentRoot==='street';
 scene.background=new T.Color(c.id==='rooftops'?'#8c8390':outside||currentRoot==='coach'?'#a3b8c5':'#41474c');
 scene.fog=outside?new T.FogExp2(c.id==='rooftops'?'#958c96':'#b5c5ce',.024):null;
 sky.intensity=1.48;api.light('#efeee1','#9b8074','#ffe8c2',2.5);
 units[currentUnit].shot(shotId,u,api);
 const subject=aim.clone();
 grading.uniforms.focus.value=camera.position.distanceTo(aim);
 grading.uniforms.aperture.value=({streetCrew:.8,pianoHands:1.7,desk:4.2,waits:3.3,policy:4.2,signs:3.8,switcher:1.3,twoBars:4.0,chair:4.0,boothWork:4.1,curled:3.2,wheel:4.3,faresTake:1.5})[c.id]??1.9;
 if(c.id==='rooftops')sky.intensity=.9;
 let direction=new T.Vector3(-3.8,5.2,3.8);
 if(outside)direction.set(-5,7,2.9);
 sun.target.position.copy(subject);sun.position.copy(subject).addScaledVector(direction,2.4);
 bounce.target.position.copy(subject);bounce.position.copy(subject).add(new T.Vector3(3.5,3.5,-4.5));
 bounce.intensity=c.id==='rooftops'?.45:outside?.72:.78;
 const extent=outside?10:5.5;
 Object.assign(sun.shadow.camera,{left:-extent,right:extent,top:extent,bottom:-extent});sun.shadow.camera.updateProjectionMatrix();
 snow.visible=outside;snowMat.uniforms.t.value=(frame/24)%65;snow.position.set(camera.position.x,0,camera.position.z);
 grading.uniforms.moment.value=frame;grading.uniforms.closing.value=c.id==='bedNight'?Math.max(0,(u-.76)/.24):0;
 renderer.setRenderTarget(frameBuffer);renderer.render(scene,camera);
 renderer.setRenderTarget(null);renderer.render(post,postCam);
}
window.projection={loadUnit,paint,cut,unitFor,canvas,renderer,roots,lookup,api};
window.ready=true;

if(!params.has('render')){
 const message=document.getElementById('message');
 const controls=document.querySelector('#transport');
 const play=document.querySelector('#play'), scrub=document.querySelector('#scrub'), time=document.querySelector('#time');
 message.textContent='Loading the film…';
 try{
  // Set builders share temporary animation state, so load their scene graphs sequentially.
  for(const unit of ['exteriors','hotel','music'])await loadUnit(unit);
  controls.hidden=false;message.textContent='';paint(0);
  const duration=2592/24;
  let position=0,startedAt=null,lastFrame=-1,scheduled=0;
  function update(){
   if(startedAt!==null)position=Math.min(duration,(performance.now()-startedAt)/1000);
   const frame=Math.min(2591,Math.floor(position*24));
   if(frame!==lastFrame){paint(frame);scrub.value=position;lastFrame=frame;}
   const sec=Math.floor(position);time.value=Math.floor(sec/60)+':'+String(sec%60).padStart(2,'0');
   if(position>=duration){startedAt=null;play.textContent='Play';}
   cancelAnimationFrame(scheduled);if(startedAt!==null)scheduled=requestAnimationFrame(update);
  }
  play.onclick=()=>{
   if(startedAt===null){
    if(position>=duration)position=0;
    startedAt=performance.now()-position*1000;play.textContent='Pause';
   }else{
    position=Math.min(duration,(performance.now()-startedAt)/1000);
    startedAt=null;play.textContent='Play';
   }
   update();
  };
  scrub.oninput=()=>{
   position=Number(scrub.value);
   if(startedAt!==null)startedAt=performance.now()-position*1000;
   update();
  };
 }catch(error){message.textContent='The scene preview could not load. Open Play-It-Again.mp4 to watch the trailer.';console.error(error);}
}
