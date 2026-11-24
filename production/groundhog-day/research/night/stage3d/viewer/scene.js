"use strict";
window.TownStageArt = (() => {
  function seeded(seed) {
    return () => {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let v = Math.imul(seed ^ seed >>> 15, 1 | seed);
      v = v + Math.imul(v ^ v >>> 7, 61 | v) ^ v;
      return ((v ^ v >>> 14) >>> 0) / 4294967296;
    };
  }

  function build(canvas) {
    const T=window.THREE,data=window.TUESDAY_STAGE,placement=TownStagePlacement;
    if (!T || !data) throw new Error("The local renderer could not load.");
    const renderer = new T.WebGLRenderer({canvas, antialias: true, alpha: false, powerPreference: "high-performance"});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.useLegacyLights = false;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.14;

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(40, 1, .065, 155);
    const sun = new T.DirectionalLight(0xffdfad, 2.05);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024,1024);
    Object.assign(sun.shadow.camera, {left: -13, right: 13, top: 13, bottom: -13, far: 67});
    sun.shadow.bias = -.00035; sun.shadow.normalBias = .018;
    scene.add(sun, sun.target);
    const skyLight = new T.HemisphereLight(0xffefcc, 0x82989d, 1.45);
    scene.add(skyLight);
    const streetBounce=new T.DirectionalLight(0xffe5c0,.84);streetBounce.position.set(11,8,16);scene.add(streetBounce);
    scene.fog = new T.FogExp2(0xf2d7b2,.020);

    const forms = {
      Cube: new T.BoxGeometry(1,1,1),
      Cone: new T.ConeGeometry(.5,1,9),
      Cylinder: new T.CylinderGeometry(.5,.5,1,14),
      Sphere: new T.SphereGeometry(.5,12,8)
    };
    const transform = new T.Object3D();
    const instanceMat = new T.MeshStandardMaterial({roughness: .83, metalness: .02, flatShading: true});
    const materials = new Map();
    function ink(col) {
      const c = Array.isArray(col) ? new T.Color(...col) : new T.Color(col);
      const key = c.getHexString();
      if (!materials.has(key)) materials.set(key,new T.MeshStandardMaterial({color:c,roughness:.80,flatShading:true}));
      return materials.get(key);
    }
    function part(parent,type,p,s,col,rotation) {
      const mesh = new T.Mesh(forms[type],ink(col)); mesh.position.fromArray(p); mesh.scale.fromArray(s);
      if (rotation) mesh.rotation.set(...rotation);
      mesh.castShadow = true; mesh.receiveShadow = true; parent.add(mesh); return mesh;
    }
    function instanced(group, records) {
      for (const [type, geom] of Object.entries(forms)) {
        const rows = records.filter(s=>s.type===type);
        if (!rows.length) continue;
        const mesh = new T.InstancedMesh(geom,instanceMat,rows.length);
        for (let i=0; i<rows.length; i++) {
          const row=rows[i];
          transform.position.fromArray(row.position); transform.scale.fromArray(row.size);
          transform.rotation.set(...(row.rotation || [0,0,0])); transform.updateMatrix();
          mesh.setMatrixAt(i,transform.matrix);
          mesh.setColorAt(i,Array.isArray(row.color) ? new T.Color(...row.color) : new T.Color(row.color));
        }
        mesh.castShadow=true; mesh.receiveShadow=true; mesh.name=type+" instances";
        mesh.computeBoundingSphere(); group.add(mesh);
      }
    }

    const sky = new T.Mesh(new T.SphereGeometry(95,36,19),new T.ShaderMaterial({
      side:T.BackSide, depthWrite:false,
      uniforms:{top:{value:new T.Color()},horizon:{value:new T.Color()},glow:{value:new T.Color()}},
      vertexShader:"varying vec3 ray;void main(){ray=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
      fragmentShader:`varying vec3 ray; uniform vec3 top;uniform vec3 horizon;uniform vec3 glow;
      void main(){vec3 d=normalize(ray);float k=smoothstep(-0.05,0.73,d.y);
        vec3 c=mix(horizon,top,k);vec3 sun=normalize(vec3(-.68,.19,-.64));
        float h=max(dot(d,sun),0.0);c+=glow*(pow(h,26.)*.28+smoothstep(.9994,.99965,h)*.65);
        gl_FragColor=vec4(c,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`.replace("#include <colorspace_fragment>","#include <encodings_fragment>")
    }));
    sky.renderOrder=-10; sky.frustumCulled=false; scene.add(sky);

    function sign(group, words, xy, w, h, bg, fg, sub="") {
      const c=document.createElement("canvas"); c.width=640; c.height=144;
      const x=c.getContext("2d"); x.fillStyle=bg; x.fillRect(0,0,c.width,c.height);
      x.strokeStyle=fg; x.lineWidth=4; x.strokeRect(7,7,626,130);
      x.font="700 "+(sub?59:74)+"px Georgia,serif"; x.textAlign="center"; x.textBaseline="middle";
      x.fillStyle=fg; x.fillText(words,320,sub?59:73,586);
      if(sub){x.font="bold 24px monospace";x.fillText(sub,320,108,573);}
      const map=new T.CanvasTexture(c); map.colorSpace=T.SRGBColorSpace;
      map.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
      const surface=new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({map,toneMapped:false}));
      surface.position.fromArray(xy);group.add(surface);
      return surface;
    }

    const bindings=new Map(),identity=p=>JSON.stringify([p.name,p.role]);
    const sets={}, rigGroups=[], rigCache=[], collisionBoxes={}, occlusionBoxes={}, signs={}, practice={},dressingGroups=[];
    let treatment=true;
    const onTreatment=[];
    function makeExtraGroup(parent){const g=new T.Group();g.visible=treatment;parent.add(g);dressingGroups.push(g);return g;}
    function setDressing(value){treatment=!!value;for(const g of dressingGroups)g.visible=treatment;for(const fn of onTreatment)fn(treatment);}

    const targetPoint=new T.Vector3();
    function scenery(key) {
      const info=data.sets[key], parent=new T.Group();
      parent.name=key; parent.position.fromArray(info.offset); scene.add(parent);
      const boxList=placement.buildings(key,true),canonical=placement.canonical(key);
      const revised=info.shapes.map(row=>{
        const dz=placement.shiftForRow(key,row.path);
        return dz?{...row,position:[row.position[0],row.position[1],row.position[2]+dz]}:row;
      });
      const blockers=[];
      for(const b of boxList)blockers.push(new T.Box3(
        new T.Vector3(info.offset[0]+b.x,-.03,b.y),
        new T.Vector3(info.offset[0]+b.x+b.w,b.h+.14,b.y+b.d)));
      collisionBoxes[key]=blockers;
      for(const [index,edit] of Object.entries(placement.edits[key])){
        const b=canonical[index],box=blockers[index];
        onTreatment.push(on=>{box.min.z=b.y+(on?edit.dz:0);box.max.z=box.min.z+b.d;});
      }
      const stems=info.shapes.filter(r=>/\/Spruce[0-9]+$/.test(r.path)).map(r=>{
        const [x,y,z]=r.position,[width,height]=r.size,ofs=info.offset[0];
        return new T.Box3(new T.Vector3(x+ofs-width*.42,.08,z-width*.42),new T.Vector3(x+ofs+width*.42,y+height*.50,z+width*.42));
      });
      occlusionBoxes[key]=[...blockers,...stems];
      if(key==="town")occlusionBoxes[key].push(new T.Box3(
        new T.Vector3(10.84,1.22,11.50),new T.Vector3(13.16,2.35,13.88)));
      instanced(parent,info.shapes.filter(r=>!placement.shiftForRow(key,r.path)));
      for(const edit of placement.styleRules(key)){
        const patch=new T.Group();patch.position.z=edit.dz;parent.add(patch);
        instanced(patch,info.shapes.filter(r=>r.path.split("/")[1]===edit.prim));
        onTreatment.push(on=>patch.position.z=on?edit.dz:0);
      }
      const dressed=makeExtraGroup(parent);
      const dressing=[], rnd=seeded(key==="town"?836:157);
      const shape=(type,p,s,col,rotation=null)=>dressing.push({type,position:p,size:s,color:col,rotation});
      const cube=(p,s,col,rotation=null)=>shape("Cube",p,s,col,rotation);
      const pine=(x,z,h,far=false)=>{
        if(!far)occlusionBoxes[key].push(new T.Box3(
          new T.Vector3(x+info.offset[0]-h*.265,.12,z-h*.265),new T.Vector3(x+info.offset[0]+h*.265,h,z+h*.265)));
        if(!far)cube([x,h*.19,z],[h*.11,h*.39,h*.11],"#736b56");
        for(let j=0;j<3;j++){
          const y=h*(.33+j*.22),width=h*(.65-j*.14);
          shape("Cone",[x,y,z],[width,h*(.58-j*.07),width],j===0?"#56756b":"#648373");
          shape("Cone",[x,y+h*(.105-j*.015),z],[width*.72,h*(.42-j*.05),width*.72],"#dfe6d9");
        }
      };
      const signData={
        hotel:["HEARTHSIDE","MOTOR HOTEL","#37594f","#f4d4a0"],
        diner:["BEA’S DINER","COFFEE  •  PIE","#a55742","#fff0c8"],
        radio:["WRSE","LOCAL RADIO","#35575d","#f0d19a"],
        depot:["INTERCITY","COACH DEPOT","#3a665b","#eadeb7"],
        terminal:["PITTSBURGH","INTERCITY TERMINAL","#3c5b5d","#f0d49d"],
        shop:["BOOKS","","#546c62","#f5dfb7"]
      };
      signs[key]={};
      for(const [i,b] of boxList.entries()){
        const front=b.y+b.d, cx=b.x+b.w/2;
        cube([cx,.035,front+.31],[b.w+.23,.07,.67],"#c9cec3");
        cube([cx,.055,front+.62],[b.w+.23,.095,.06],"#dce0d0");
        cube([cx,.095,front+.22],[.74,.15,.41],"#a6aca0");
        cube([cx,.18,front+.115],[.64,.10,.32],"#c8c7b8");
        cube([b.x+b.w*.68,b.h+.24,b.y+b.d*.33],[.28,.47,.32],b.kind==="tower"?"#899491":"#a77c69");
        cube([b.x+b.w*.68,b.h+.49,b.y+b.d*.33],[.35,.07,.39],"#ece8d9");
        if(b.kind==="house"){
          const pitch=.39, half=b.d*.595;
          cube([cx,b.h+.22,b.y+b.d*.25],[b.w+.30,.14,half],"#cbd2ce",[-pitch,0,0]);
          cube([cx,b.h+.22,b.y+b.d*.75],[b.w+.30,.15,half],"#edf0df",[pitch,0,0]);
        }
        if(["hotel","diner","radio","depot","terminal"].includes(b.kind)){
          const text=signData[b.kind],sw=Math.min(b.w*.71,3.55);
          const tag=sign(dressed,text[0],[cx,b.h-.23,front+.077],sw,.39,text[2],text[3],text[1]);
          signs[key][b.id||"Pittsburgh"]=tag;
          if(b.kind==="diner"||b.kind==="hotel"){
            const count=b.kind==="diner"?13:7,wide=b.kind==="diner"?b.w*.95:b.w*.48,awningY=b.kind==="diner"?.80:1.27;
            for(let j=0;j<count;j++)cube([cx-wide/2+wide*(j+.5)/count,awningY,front+.19],
              [wide/count+.004,.055,.42],j%2?"#e0d3b6":b.kind==="diner"?"#ad5d4c":"#476d60",[.19,0,0]);
            cube([cx,awningY-.08,front+.395],[wide,.13,.045],b.kind==="diner"?"#ae614e":"#4f7563");
          }
        }
        if(b.kind==="radio"){
          cube([cx+.8,b.h+.65,b.y+.56],[.054,1.3,.054],"#6a7773");
          for(let j=0;j<3;j++)cube([cx+.8,b.h+.83+j*.21,b.y+.56],[.69-j*.12,.033,.04],"#849791");
        }
        if(b.kind==="hotel"||b.kind==="terminal"){
          for(const dx of [-.48,.48]){
            cube([cx+dx,.96,front+.10],[.06,.23,.11],"#50655a");
            cube([cx+dx,1.11,front+.13],[.12,.18,.12],"#ebc581");
          }
        }
        if(b.kind==="hotel"||b.kind==="diner"||b.kind==="terminal"){
          for(const x of [b.x+.22,b.x+b.w-.23]){
            cube([x,.15,front+.3],[.34,.27,.32],"#897761");
            shape("Sphere",[x,.35,front+.30],[.38,.36,.38],"#708c70");
            shape("Sphere",[x,.46,front+.30],[.29,.13,.27],"#dbe2d2");
          }
        }
        if(b.kind==="tower"){
          for(let floor=0;floor<Math.floor(b.h/.65);floor++)for(let j=0;j<Math.floor(b.w/.46);j++)
            cube([b.x+.24+j*.46,.45+floor*.65,front+.027],[.22,.25,.045],(i+j+floor)%5===0?"#dcc292":"#789096");
        }
      }
      const lamps=placement.lamps[key];
      for(const [x,z] of lamps){
        shape("Cylinder",[x,.11,z],[.17,.22,.17],"#51645b");
        shape("Cylinder",[x,.88,z],[.068,1.62,.068],"#53665e");
        shape("Sphere",[x,1.75,z],[.18,.25,.18],"#f3d9a0");
        shape("Cone",[x,1.92,z],[.30,.19,.30],"#64766d");
      }
      const bench=(x,z)=>{
        for(let j=0;j<3;j++)cube([x,.28,z+j*.085],[.86,.055,.06],"#946f55");
        cube([x,.49,z-.018],[.86,.16,.07],"#a78160");
        for(const dx of [-.30,.30]){cube([x+dx,.15,z+.08],[.06,.28,.15],"#51635a");cube([x+dx,.39,z-.018],[.05,.31,.045],"#51635a");}
      };
      if(key==="town"){

        for(const [x,z] of [[9.45,8.94],[9.45,11.73]])for(let j=0;j<6;j++)cube([x-.66+j*.27,.038,z],[.14,.012,.38],"#d5d6c4");
        for(const [x,z] of [[8.0,10.35],[10.85,10.35]])for(let j=0;j<6;j++)cube([x,.038,z-.65+j*.26],[.35,.012,.14],"#d5d6c4");
        for(let i=0;i<2;i++){
          const a=[10.7,2.14,11.55+i*1.72],b=[13.72,2.14,11.55+i*1.72];
          for(const q of [a,b])cube([q[0],1.07,q[2]],[.048,2.14,.048],"#857357");
          for(let j=0;j<=16;j++){
            const f=j/16,y=2.13-.23*Math.sin(Math.PI*f),x=a[0]+3.02*f;
            cube([x,y,a[2]],[.20,.015,.017],"#777969");
            if(j%2)shape("Cone",[x,y-.073,a[2]],[.12,.14,.047],["#a65c52","#d0a466","#709284"][(j+i)%3],[Math.PI,0,0]);
          }
        }
        // Snowbanks and a spruce grove around the occupied block.
        for(const [x,z,h] of placement.spruces[key])pine(x,z,h);
      }
      for(const [x,z] of placement.benches[key])bench(x,z);
      for(let j=0;j<96;j++){
        const side=j%4,across=rnd()*39-8,far=-7-rnd()*5;
        const x=side===0||side===2?across:side===1?far:25+rnd()*7;
        const z=side===1||side===3?across:side===0?far:25+rnd()*7;
        pine(x,z,1.4+rnd()*3.4,true);
      }
      for(let j=0;j<58;j++){
        const x=rnd()*24,z=rnd()*23;
        if(WinterMap.walkable({x,y:z},key) && (x<2.3||z<2.4||x>20||z>18.3))
          shape("Sphere",[x,.02,z],[.70+rnd()*.9,.13+rnd()*.20,.61+rnd()*.78],"#e4e8db");
      }
      TownStageDressing.groundDress({T,key,group:dressed,shape,cube});
      practice[key]=TownStageDressing.facades({T,group:dressed,boxes:boxList,rows:revised,cube,shape,sign,key});
      practice[key].night=TownStageDressing.practicals(T,dressed,practice[key].warm,lamps);
      instanced(dressed,dressing);
      // A continuous horizon outside the proxy stage keeps each city a distinct film set.
      const plateau=new T.Mesh(new T.CircleGeometry(75,80),ink("#dfe4da"));
      plateau.rotation.x=-Math.PI/2;plateau.position.set(10,-.201,10);plateau.receiveShadow=true;parent.add(plateau);
      const hills=[];
      for(let ring=0;ring<2;ring++){
        const verts=[],colors=[],steps=96;
        const phase=key==="town"?.7:1.7,rad=39+ring*12,base=-.48;
        const col=new T.Color(ring?"#9caca7":"#98a99d");
        for(let a=0;a<steps;a++){
          function point(i,y){
            const theta=2*Math.PI*i/steps;
            const h=4+1.45*Math.sin(4*theta+phase)+1.8*Math.sin(7*theta+phase)+1.4*Math.cos(3*theta)+(ring?2.5:0);
            return [10+rad*Math.cos(theta),y?h:base,10+rad*Math.sin(theta)];
          }
          const quad=[point(a,0),point(a,1),point(a+1,0),point(a,1),point(a+1,1),point(a+1,0)];
          verts.push(...quad.flat());for(let n=0;n<6;n++)colors.push(col.r,col.g,col.b);
        }
        const geom=new T.BufferGeometry();geom.setAttribute("position",new T.Float32BufferAttribute(verts,3));
        geom.setAttribute("color",new T.Float32BufferAttribute(colors,3));
        const mesh=new T.Mesh(geom,new T.MeshBasicMaterial({vertexColors:true,side:T.DoubleSide,fog:true}));
        hills.push(mesh);dressed.add(mesh);
      }
      sets[key]=parent;
    }
    scenery("town"); scenery("city");

    function actor(role,index){
      const profile=data.rigs[role]?role:["reporter","producer","camera"][Math.min(index,2)];
      const rig=data.rigs[profile];
      const group=new T.Group(),skin=new T.Group(),joints={};group.add(skin);group.visible=false;scene.add(group);
      for(const [k,pos] of Object.entries(rig.joints)){
        const joint=new T.Group();joint.position.fromArray(pos);skin.add(joint);joints[k]=joint;
      }
      for(const s of rig.shapes){
        const names=s.path.split("/"),parent=names.length===3?joints[names[1]]:skin;
        if(names.at(-1)==="Camera"&&role!=="camera")continue;
        const m=part(parent,s.type,s.position,s.size,s.color);m.name=names.at(-1);
      }
      const dress=makeExtraGroup(skin);
      if(role==="reporter"){
        part(dress,"Cube",[0,1.18,.10],[.36,.035,.23],"#424d4c");
        part(dress,"Cube",[.073,.82,.134],[.09,.24,.055],"#d7ad68");
        part(dress,"Cylinder",[.244,.61,.12],[.046,.18,.046],"#51605a",[.38,0,0]);
        part(dress,"Sphere",[.244,.70,.14],[.076,.095,.076],"#364d50");
      }else if(role==="producer"){
        part(dress,"Cube",[-.19,.74,.12],[.18,.28,.045],"#ad8965",[0,0,-.18]);
        part(dress,"Cube",[-.19,.75,.150],[.146,.228,.018],"#e9ddba",[0,0,-.18]);
      }else if(role==="camera"){
        part(dress,"Cylinder",[.18,.85,.32],[.13,.12,.13],"#283e40",[Math.PI/2,0,0]);
        part(dress,"Sphere",[0,1.29,-.01],[.095,.095,.095],"#80694e");
      }
      TownStageDressing.contact(T,dress);
      const costume=TownStageDressing.wardrobe({T,group:dress,joints,role,profile,part,makeExtraGroup});
      return {group,skin,joints,role,yaw:0,costume,asset:null,switcher:role==="producer"?TownStageDressing.switcher(T,makeExtraGroup(group),part):null};
    }
    const coach=new T.Group();scene.add(coach);
    for(const s of data.coach)part(coach,s.type,s.position,s.size,s.color);
    const coachDress=makeExtraGroup(coach);
    for(const dx of [-.65,.65])part(coachDress,"Sphere",[dx,-.25,-.315],[.35,.35,.12],"#364541");
    for(let i=0;i<5;i++)part(coachDress,"Cube",[-.70+i*.32,.145,-.339],[.25,.23,.026],"#749397");
    for(let i=0;i<5;i++)part(coachDress,"Cube",[-.71+i*.32,.145,.356],[.018,.24,.026],"#667a6e");
    part(coachDress,"Cube",[.94,.12,0],[.045,.22,.47],"#849c9a");part(coachDress,"Cube",[.955,-.05,.21],[.04,.07,.082],"#f5d29a");
    for(const direction of [-1,1]){
      const end=new T.Group();coachDress.add(end);end.position.set(direction*.967,0,0);end.rotation.y=direction*Math.PI/2;
      part(end,"Cube",[0,.13,.0],[.52,.24,.04],"#5f8387");
      part(end,"Cube",[0,.13,.026],[.024,.245,.025],"#c8a574");
      part(end,"Cube",[0,-.185,.024],[.66,.055,.038],"#59645b");
      for(const dx of [-.235,.235])part(end,"Cube",[dx,-.076,.027],[.069,.061,.035],direction>0?"#edd19b":"#ae5e4b");
      sign(end,direction>0?"PITTSBURGH":"INTERCITY",[0,.294,.032],.44,.062,"#415950","#f0d4a1");
    }
    for(const side of [-1,1]){
      const flank=new T.Group();coachDress.add(flank);flank.position.z=side*.354;flank.rotation.y=side>0?0:Math.PI;
      part(flank,"Cube",[0,-.085,.005],[1.86,.15,.018],"#42766d");
      part(flank,"Cube",[0,.009,.006],[1.865,.023,.022],"#d8bd8d");
      part(flank,"Cube",[0,-.19,.004],[1.76,.024,.018],"#a8a995");
      sign(flank,"INTERCITY",[0,-.081,.019],.72,.105,"#3c655f","#f7dfad");
    }
    const snowRng=seeded(427), snowPos=[];
    for(let i=0;i<430;i++)snowPos.push((snowRng()-.5)*35,snowRng()*10,(snowRng()-.5)*35);
    const snowGeom=new T.BufferGeometry();snowGeom.setAttribute("position",new T.Float32BufferAttribute(snowPos,3));
    const snow=new T.Points(snowGeom,new T.ShaderMaterial({
      transparent:true,depthWrite:false,uniforms:{time:{value:0}},vertexShader:`
        uniform float time;void main(){vec3 p=position;
          p.y=mod(position.y-time*.23,10.);p.x+=sin(time*.37+p.z)*.21;
          vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(9./(-mv.z),1.,2.8);}`,
      fragmentShader:"void main(){float d=length(gl_PointCoord-vec2(.5));if(d>.5)discard;gl_FragColor=vec4(1.,.995,.94,.65);}"
    }));snow.frustumCulled=false;scene.add(snow);

    const lighting=[
      ["#7192ad","#edcdaf","#ffc596","#ffd7a8","#899da5",3.65,2.25],
      ["#7197b3","#e4dac4","#fbd9ba","#fff0cf","#a1b0ae",4.1,2.22],
      ["#6993b0","#dcdfcf","#f1d7ba","#fff1d2","#9daeb6",4.2,2.10],
      ["#24354e","#9a8f93","#dbaa87","#ffbd88","#8394ae",1.8,1.32]
    ];
    let lastSlot=-1,lastScene="",size={w:0,h:0};
    function environment(key,slot,focus) {
      if(lastScene!==key){sets.town.visible=key==="town";sets.city.visible=key==="city";lastScene=key;}
      if(slot!==lastSlot){
        const c=lighting[slot]||lighting[0],u=sky.material.uniforms;
        u.top.value.set(c[0]);u.horizon.value.set(c[1]);u.glow.value.set(c[2]);scene.fog.color.set(c[1]);
        sun.color.set(c[3]);sun.intensity=c[5];streetBounce.intensity=slot===3?.33:.84;skyLight.color.set(slot===3?"#9cabc9":"#d4e3f0");skyLight.groundColor.set(c[4]);skyLight.intensity=c[6];
        renderer.toneMappingExposure=slot===3?1.06:1.14;lastSlot=slot;
      }
      practice[key].night.visible=slot===3;sky.position.copy(focus);snow.position.set(focus.x,0,focus.z);
      sun.target.position.copy(focus);sun.position.set(focus.x-9,slot===0?8:slot===3?6:14,focus.z-11);
    }
    function applyActors(w,active,clock){
      function castRole(p,i){
        if(["reporter","producer","camera"].includes(p.role))return p.role;
        return i%2?"legacy-producer":"legacy-diner";
      }
      w.people.forEach((p,i)=>{
        const role=castRole(p,i);
        if(!rigCache[i])rigCache[i]=new Map();
        if(!rigCache[i].has(role))rigCache[i].set(role,actor(role,i));
        const r=rigCache[i].get(role);
        if(rigGroups[i]&&rigGroups[i]!==r)rigGroups[i].group.visible=false;
        rigGroups[i]=r;
        const asset=treatment?(bindings.get(identity(p))||null):null;
        if(r.asset!==asset){
          if(r.asset?.carrier.parent===r.group)r.asset.carrier.removeFromParent();
          r.asset=asset||null;if(asset)r.group.add(asset.carrier);
        }
        r.skin.visible=!asset;if(asset)asset.pose(p,clock);
        r.group.visible=p.scene===active&&p.visible!==false;
        r.group.position.set(p.pos.x+data.sets[p.scene].offset[0],0,p.pos.y);
        const dx=p.pos.dx||0,dz=p.pos.dy||0;
        if(p.moving&&Math.abs(dx)+Math.abs(dz)>.0001)r.yaw=Math.atan2(dx,dz);
        else if(!p.moving){
          const partner=w.people.find(other=>other!==p&&other.scene===p.scene&&other.at===p.at&&p.action==="talk_to_"+other.name);
          r.yaw=partner?Math.atan2(partner.pos.x-p.pos.x,partner.pos.y-p.pos.y):[.19,2.48,-.68][i%3];
          if(p.scene==="city"&&/^(call_sister|call_home|call_live_report)$/.test(p.action||""))r.yaw=Math.atan2(11.5-p.pos.x,(treatment?11.33:11.65)-p.pos.y);
          if(p.at==="inn"&&p.action==="leave_pencil_mark")r.yaw=Math.PI;
        }
        r.group.rotation.y=r.yaw;
        r.switcher?.update(p,w.facts,treatment);
        r.costume.handheld.visible=treatment&&!p.moving&&/call_(sister|home|live_report)/.test(p.action||"");
        const step=p.moving?Math.sin(clock*8.8+i*.5):0;
        if(r.joints.Leg0){
          r.joints.Leg0.rotation.x=step*.38;r.joints.Leg1.rotation.x=-step*.38;
          r.joints.Arm0.rotation.x=-step*.29;r.joints.Arm1.rotation.x=step*.29;
          if(!p.moving&&/^(film_|shoot_)/.test(p.action||""))r.joints.Arm1.rotation.x=-.83;
          if(r.costume.handheld.visible)r.joints.Arm1.rotation.x=-1.9;
        }
      });
      if(practice.town.mark)practice.town.mark.visible=!!w.facts?.marked;
      rigGroups.slice(w.people.length).forEach(r=>r.group.visible=false);
      const onSet=!!w.bus&&w.bus.scene===active;
      // The coarse native set stages a parked coach on top of the platform anchor
      // after disembarkation. The model only records the trip. Release the vehicle
      // from the dressed evening shot while leaving the native blocking recoverable.
      const platformAfterRide=active==="city"&&w.people[0].visible!==false&&
        (w.shown?.origin==="Pittsburgh"||w.phase==="free walk");
      coach.visible=onSet&&(!treatment||!platformAfterRide);
      if(onSet){
        const p=w.bus.pos;coach.position.set(p.x+data.sets[active].offset[0],.4,p.y);
        coach.rotation.y=treatment&&Math.hypot(p.dx||0,p.dy||0)>.001?-Math.atan2(p.dy,p.dx):0;
      }
    }
    return {renderer,scene,camera,sets,rigGroups,coach,collisionBoxes,occlusionBoxes,setDressing,identity,
      assetFor(p){return bindings.get(identity(p));},
      bindAsset(p,asset){
        const key=identity(p),prior=bindings.get(key);if(prior)prior.dispose();
        if(asset)bindings.set(key,asset);else bindings.delete(key);
      },
      render(w,subject,view){
        const rect=canvas.getBoundingClientRect(),width=Math.max(1,Math.round(rect.width)),height=Math.max(1,Math.round(rect.height));
        if(width!==size.w||height!==size.h){size={w:width,h:height};renderer.setSize(width,height,false);camera.aspect=width/height;}
        const key=subject.scene, focus=targetPoint.set(subject.pos.x+data.sets[key].offset[0],view.targetHeight,subject.pos.y);
        camera.fov=view.fov;camera.updateProjectionMatrix();camera.position.fromArray(view.eye);
        camera.lookAt(view.target||focus);camera.updateMatrixWorld(true);
        environment(key,w.slot,focus);applyActors(w,key,w.t);snow.material.uniforms.time.value=w.t;
        renderer.render(scene,camera);
        let coachScreen=null;
        if(coach.visible){
          const xs=[],ys=[];
          for(const x of [-.97,.97])for(const y of [-.36,.41])for(const z of [-.36,.36]){
            const q=coach.localToWorld(new T.Vector3(x,y,z)).project(camera);
            xs.push(q.x*.5+.5);ys.push(.5-q.y*.5);
          }
          coachScreen={left:Math.min(...xs),right:Math.max(...xs),top:Math.min(...ys),bottom:Math.max(...ys)};
        }
        const activeSwitcher=rigGroups.find(r=>r.group.visible&&r.switcher?.cart.visible);
        let switcherScreen=null;
        if(activeSwitcher){
          const c=activeSwitcher.switcher.cart.localToWorld(new T.Vector3(.07,.80,.0)).project(camera);
          switcherScreen={x:(c.x*.5+.5)*width,y:(.5-c.y*.5)*height,visible:Math.abs(c.x)<1&&Math.abs(c.y)<1&&Math.abs(c.z)<1};
        }
        return {width,height,coachScreen,switcherScreen,focus:focus.toArray(),drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,
          visibleSets:Object.keys(sets).filter(k=>sets[k].visible),
          rigs:rigGroups.slice(0,w.people.length).map(r=>({position:r.group.position.toArray(),visible:r.group.visible,asset:r.asset?.name||null,assetClip:r.asset?.activeClip||null})),
          coach:coach.visible?coach.position.toArray():null,
          visibleSwitcher:activeSwitcher?.role||null};
      },
      pick(x,y){
        const bounds=canvas.getBoundingClientRect(),ray=new T.Raycaster();
        ray.setFromCamera(new T.Vector2(2*(x-bounds.left)/bounds.width-1,1-2*(y-bounds.top)/bounds.height),camera);
        const key=lastScene,offset=data.sets[key].offset[0];
        const ground=ray.ray.intersectPlane(new T.Plane(new T.Vector3(0,1,0),0),new T.Vector3());
        if(!ground)return null;
        const items=key==="town"?WinterMap.buildings:WinterMap.cityBuildings;
        let nearest=Infinity,landmark=null;
        collisionBoxes[key].forEach((box,i)=>{
          const hit=ray.ray.intersectBox(box,new T.Vector3());
          const d=hit&&hit.distanceTo(camera.position);
          if(hit&&d<nearest&&d<ground.distanceTo(camera.position)){nearest=d;landmark=items[i].id||(items[i].kind==="terminal"?"Pittsburgh":null);}
        });
        return {point:{x:ground.x-offset,y:ground.z},landmark};
      },
      projectWorld(x,y,z){
        const v=new T.Vector3(x,y,z).project(camera);
        return {x:(v.x*.5+.5)*size.w,y:(.5-v.y*.5)*size.h,visible:v.z>-1&&v.z<1&&Math.abs(v.x)<1&&Math.abs(v.y)<1};
      },
      screen(p){
        const v=new T.Vector3(p.pos.x+data.sets[p.scene].offset[0],1.51,p.pos.y).project(camera);
        return {x:(v.x*.5+.5)*size.w,y:(.5-v.y*.5)*size.h,visible:v.z>-1&&v.z<1&&Math.abs(v.x)<1&&Math.abs(v.y)<1};
      },
      dispose(){renderer.dispose();}
    };
  }
  return {build};
})();
