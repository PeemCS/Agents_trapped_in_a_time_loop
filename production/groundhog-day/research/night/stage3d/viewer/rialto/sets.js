/* Original editorial set models. Local coordinates are metres, Y-up, with the audience on +Z. */
(() => {
  const T=THREE, box=new T.BoxGeometry(1,1,1), cyl=new T.CylinderGeometry(1,1,1,20);
  const sphere=new T.SphereGeometry(1,16,12), torus=new T.TorusGeometry(1,.12,8,28);
  const mats=new Map(), textures=new Map();
  function material(color,light=0){
    const key=color+":"+light;
    if(!mats.has(key))mats.set(key,new T.MeshStandardMaterial({color,roughness:.83,emissive:color,emissiveIntensity:light}));
    return mats.get(key);
  }
  function group(parent,x=0,y=0,z=0){
    const g=new T.Group();g.position.set(x,y,z);parent.add(g);return g;
  }
  function primitive(parent,geo,color,x,y,z,w,h,d,light=0){
    const mesh=new T.Mesh(geo,material(color,light));mesh.position.set(x,y,z);mesh.scale.set(w,h,d);
    mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;
  }
  function cube(g,c,x,y,z,w,h,d,e=0){return primitive(g,box,c,x,y,z,w,h,d,e);}
  function post(g,c,x,y,z,r,h){return primitive(g,cyl,c,x,y,z,r,h,r);}
  function ball(g,c,x,y,z,w,h,d,e=0){return primitive(g,sphere,c,x,y,z,w,h,d,e);}
  function rim(g,c,x,y,z,r){return primitive(g,torus,c,x,y,z,r,r,r);}
  function bar(g,c,a,b,r=.035){
    const p=new T.Vector3(...a),q=new T.Vector3(...b),length=p.distanceTo(q),mesh=post(g,c,(p.x+q.x)/2,(p.y+q.y)/2,(p.z+q.z)/2,r,length);
    mesh.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),q.sub(p).normalize());return mesh;
  }
  function flat(g,x,y,z,w,h,texture){
    const m=new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({map:texture,transparent:true,side:T.DoubleSide}));
    m.position.set(x,y,z);g.add(m);return m;
  }
  function canvasTexture(key,width,height,draw){
    if(!textures.has(key)){
      const c=document.createElement("canvas");c.width=width;c.height=height;const ctx=c.getContext("2d");draw(ctx,width,height);
      const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=4;textures.set(key,texture);
    }
    return textures.get(key);
  }
  function panel(g,x,y,z,w,h,title,sub,ink="#f5d49c",bg="#243f36",style="classic"){
    const key=[title,sub,ink,bg,style].join("|");
    const texture=canvasTexture(key,768,256,(c,W,H)=>{
      c.fillStyle=bg;c.fillRect(0,0,W,H);c.strokeStyle=ink;c.globalAlpha=.55;c.lineWidth=3;c.strokeRect(10,10,W-20,H-20);
      c.lineWidth=1;c.strokeRect(17,17,W-34,H-34);c.globalAlpha=1;c.textAlign="center";c.textBaseline="middle";c.fillStyle=ink;
      let f=style==="modern"?"bold 84px Arial":"70px Georgia";c.font=f;
      const max=W*.89, ratio=Math.min(1,max/c.measureText(title).width);c.save();c.translate(W/2,sub?H*.44:H*.52);c.scale(ratio,1);c.fillText(title,0,0);c.restore();
      if(sub){c.font="26px Arial";c.fillText(sub,W/2,H*.73,max);}
    });
    cube(g,bg,x,y,z-.04,w+.055,h+.055,.065);return flat(g,x,y,z,w,h,texture);
  }
  function patternedFloor(g,c1,c2,oak=false){
    const tex=canvasTexture("floor"+c1+c2,768,768,(c,W,H)=>{
      c.fillStyle=c1;c.fillRect(0,0,W,H);let seed=19;
      const rand=()=>{seed=seed*48271%2147483647;return seed/2147483647;};
      for(let y=0;y<H;y+=64)for(let x=-130+(y%128?0:96);x<W;x+=192){
        c.fillStyle=rand()>.54?c2:c1;c.fillRect(x,y,191,63);c.fillStyle="rgba(25,18,20,.2)";c.fillRect(x,y,192,2);c.fillRect(x,y,2,64);
        if(oak){c.strokeStyle="rgba(250,215,155,.14)";for(let i=0;i<5;i++){let yy=y+rand()*56;c.beginPath();c.moveTo(x+6,yy);c.bezierCurveTo(x+80,yy-2,x+95,yy+7,x+182,yy);c.stroke();}}
      }
    });tex.wrapS=tex.wrapT=T.RepeatWrapping;tex.repeat.set(2.2,1.7);
    const pl=new T.Mesh(new T.PlaneGeometry(11,7.6),new T.MeshStandardMaterial({map:tex,roughness:.68}));
    pl.rotation.x=-Math.PI/2;pl.position.y=.004;pl.receiveShadow=true;g.add(pl);
    cube(g,"#453d39",0,-.18,0,11.25,.35,7.85);cube(g,"#a58457",0,-.32,3.88,11.05,.04,.06);
  }
  function lamplight(g,x,y,z,color,amount=11){
    const l=new T.PointLight(color,amount,9,2);l.position.set(x,y,z);g.add(l);
  }
  function wall(g,color,trim){
    cube(g,color,0,2.15,-3.57,11,4.3,.2);
    for(const y of [.12,1.03,1.13,3.83,4.08])cube(g,trim,0,y,-3.42,11,.09,.18);
    for(let x=-5.15;x<=5.2;x+=1.03)cube(g,trim,x,.61,-3.43,.045,.87,.10);
  }
  function windowPane(g,x,y,z,w,h,frame="#593c39",night=false){
    cube(g,frame,x,y,z,w+.14,h+.15,.11);cube(g,night?"#6c8d9c":"#b5d2c9",x,y,z+.07,w,h,.045,.23);
    cube(g,frame,x,y,z+.12,.045,h,.04);cube(g,frame,x,y,z+.12,w,.045,.04);
    for(const side of [-1,1])cube(g,frame,x+side*w*.47,y,z+.10,.045,h,.09);
    cube(g,frame,x,y-h/2-.08,z+.11,w+.25,.09,.27);
  }
  function clock(g,x,y,z,r=.31){
    const holder=group(g,x,y,z),ring=rim(holder,"#c39c5d",0,0,.10,r);ring.scale.z=r*.55;
    const face=post(holder,"#efe7cc",0,0,.095,r,.065);face.rotation.x=Math.PI/2;
    for(let i=0;i<12;i++){const a=i*Math.PI/6,xx=r*.77*Math.sin(a),yy=r*.77*Math.cos(a);
      const tick=cube(holder,"#766a53",xx,yy,.136,.014,r*.12,.012);tick.rotation.z=-a;}
    const hour=group(holder,0,0,.141),minute=group(holder,0,0,.149);
    bar(hour,"#342e32",[0,0,0],[0,r*.52,0],.014);bar(minute,"#342e32",[0,0,0],[0,r*.71,0],.011);
    ball(holder,"#43352d",0,0,.16,.026,.026,.014);
    return {set(phase){hour.visible=minute.visible=phase!=="afternoon";hour.rotation.z=-(phase==="dawn"?6:7)*Math.PI/6;}};
  }
  function sideWalls(g,shade,trim){
    for(const side of [-1,1]){
      const sideWall=group(g,5.52*side,0,.07);sideWall.rotation.y=-side*Math.PI/2;
      cube(sideWall,shade,0,2.12,0,7.40,4.24,.15);
      for(const yy of [.13,1.04,3.86,4.07])cube(sideWall,trim,0,yy,.096,7.40,.065,.09);
      for(let x=-3.4;x<3.6;x+=1.04)cube(sideWall,trim,x,.60,.104,.038,.80,.052);
      for(const x of [-2.03,.12,2.17]){
        cube(sideWall,trim,x,2.37,.095,1.41,1.38,.07);
        cube(sideWall,shade,x,2.37,.141,1.31,1.28,.043);
      }
    }
  }
  function bench(g,x,z,len=2.35){
    const b=group(g,x,0,z);for(let i=0;i<4;i++)cube(b,"#926247",0,.48,-.24+i*.14,len,.11,.12);
    for(let i=0;i<3;i++)cube(b,"#996948",0,.79+i*.16,-.30,len,.11,.10);
    for(const side of [-1,1]){for(const zz of [-.22,.22])cube(b,"#344748",side*(len*.39),.23,zz,.09,.46,.09);
      cube(b,"#344748",side*(len*.39),.7,-.31,.08,.85,.09);cube(b,"#344748",side*(len*.46),.66,.02,.07,.39,.07);
      cube(b,"#344748",side*(len*.46),.85,-.025,.075,.075,.55);}
    return b;
  }
  function curtain(g,x,y,z,w,h,base,edge){
    cube(g,base,x,y,z,w,h,.12);
    for(let i=0;i<Math.floor(w/.16);i++)ball(g,i%3===0?edge:base,x-w*.47+i*.16,y,z+.095,.126,h*.50,.12);
    cube(g,edge,x,y-h/2+.12,z+.09,w+.04,.075,.11);
  }
  function chandelier(g,x,y,z){
    bar(g,"#766146",[x,y+.7,z],[x,y,z],.032);
    const ring=rim(g,"#be985c",x,y-.03,z,.46);ring.rotation.x=Math.PI/2;
    for(let i=0;i<6;i++){const a=i*Math.PI/3,xx=x+.45*Math.cos(a),zz=z+.45*Math.sin(a);
      bar(g,"#c19a61",[x,y+.12,z],[xx,y-.016,zz],.028);ball(g,"#ffe0a6",xx,y+.09,zz,.075,.124,.075,.65);}
  }
  function piano(g,x,z){
    const p=group(g,x,0,z),wood="#342d31",brass="#c7a370";
    cube(p,wood,0,.78,-.15,2.25,1.51,.75);cube(p,"#4a3537",0,1.36,.235,2.06,.39,.09);
    for(const xx of [-.91,.91])cube(p,brass,xx,1.35,.292,.029,.31,.027);
    cube(p,brass,0,1.18,.293,1.91,.025,.03);cube(p,wood,0,1.55,-.16,2.34,.10,.88);
    cube(p,wood,0,.89,.39,2.26,.15,.59);cube(p,"#4b3531",0,.69,.44,2.15,.28,.12);
    const keys=[];for(let i=0;i<22;i++){const xx=(i-10.5)*.09;
      keys.push(cube(p,"#f1e8d7",xx,.987,.45,.083,.065,.37));
      if(![2,6].includes(i%7)&&i<21)cube(p,"#2a272c",xx+.045,1.043,.377,.050,.063,.205);}
    for(const xx of [-1.01,1.01]){cube(p,wood,xx,.46,.56,.10,.82,.13);cube(p,wood,xx,.12,.18,.20,.11,1.0);}
    for(const xx of [-.14,0,.14])cube(p,brass,xx,.115,.42,.06,.04,.23);
    cube(p,"#563d38",0,.52,1.28,1.12,.14,.43);for(const xx of [-.44,.44])for(const zz of [1.15,1.41])cube(p,wood,xx,.25,zz,.075,.49,.075);
    return {keys,p};
  }
  function ballroom(g){
    patternedFloor(g,"#a66d43","#b77b4d",true);wall(g,"#884c4b","#9f775b");sideWalls(g,"#7e514b","#9c765a");
    for(const x of [-4.72,-3.06,3.06,4.72]){windowPane(g,x,2.37,-3.37,1.02,1.53,"#795346");curtain(g,x-.60,2.37,-3.23,.25,2.02,"#843c43","#a44f4c");curtain(g,x+.60,2.37,-3.23,.25,2.02,"#843c43","#a44f4c");}
    panel(g,0,2.68,-3.25,3.4,.82,"BALLROOM","WINTER FESTIVAL","#fce2ae","#74473e");
    for(const x of [-1.8,1.8]){cube(g,"#c29d69",x,2.69,-3.23,.055,1.47,.045);ball(g,"#ffdc9a",x,2.7,-3.13,.10,.17,.075,.6);}
    for(const side of [-1,1]){
      const far=group(g,side*4.10,.0,-2.58);const cover=cube(far,"#6f4641",0,.85,0,.79,1.67,.46);
      for(const xx of [-.38,.38])cube(far,"#c69b68",xx,.86,.25,.038,1.55,.036);
      cube(far,"#bf9868",0,1.68,0,.96,.10,.55);ball(far,"#a59266",0,1.97,0,.17,.26,.14);
      for(const j of [-1,0,1]){const leaf=ball(far,"#6a7056",j*.11,2.16+(.1*(j===0)),.01,.071,.20,.075);leaf.rotation.z=-j*.38;}
    }
    const molding=group(g);for(let x=-4.8;x<4.9;x+=.34)cube(molding,"#c39768",x,3.77,-3.26,.1,.09,.12);
    for(const x of [-2.4,2.4])chandelier(g,x,3.34,-1.45);
    lamplight(g,0,3.3,-1.6,"#ffbd72",14);
    // Low trim in the floor around the dance area.
    for(const z of [-2.74,2.89])cube(g,"#dec18a",0,.015,z,9.9,.018,.046);
    for(const x of [-4.94,4.94])cube(g,"#dec18a",x,.015,.075,.046,.018,5.65);
    return {piano:piano(g,-1.5,-1.44)};
  }
  function sky(g,city=false){
    const bg=city?"#617383":"#708183";cube(g,bg,0,2.02,-4.0,37,5.0,.20);
    const skyline=group(g,0,0,-3.61);
    for(let i=0;i<34;i++){const x=-13+i*.80,h=.53+((i*47)%10)*.16;
      const building=cube(skyline,city?(i%2?"#697b88":"#607684"):(i%2?"#778681":"#73837e"),x,h/2,0,.86,h,.18);
      if(city&&i%3===0){post(skyline,"#526b77",x,h+.16,0,.035,.35);}
    }
    if(city){
      for(let i=0;i<16;i++){const h=1+(i*173%10)*.19,x=-5.15+i*.7;
        cube(g,i%2?"#607783":"#536977",x,h/2,-3.51,.64,h,.18);
        for(let row=0;row<Math.floor(h/.3)-1;row++)for(let col=0;col<2;col++)if((row+i+col)%3)
          cube(g,"#e3c690",x-.16+col*.27,.32+row*.32,-3.40,.075,.105,.02,.31);}
    }else{
      for(let i=0;i<25;i++){const h=1.2+(i*43%9)*.13,x=-5.2+i*.43;
        const con=new T.Mesh(new T.ConeGeometry(.48,h,6),material(i%2?"#647b72":"#526c64"));con.position.set(x,h*.5,-3.52);g.add(con);}
    }
  }
  function stationGable(g,x=0){
    for(const xx of [-3.97,3.97]){post(g,"#3b554e",x+xx,1.52,-1.37,.104,2.95);post(g,"#3b554e",x+xx,1.45,-2.66,.10,2.84);}
    cube(g,"#394d46",x,2.94,-2.02,8.81,.16,2.18);
    cube(g,"#e5dfca",x,3.05,-2.03,8.95,.075,2.22);
    cube(g,"#bf9e6a",x,2.79,-.94,8.7,.13,.12);for(const xx of [-3.6,-2.4,-1.2,0,1.2,2.4,3.6])cube(g,"#3b5147",x+xx,2.75,-1.98,.070,.32,2.02);
  }
  function lamp(g,x,z){
    post(g,"#344944",x,1.30,z,.06,2.6);post(g,"#344944",x,.14,z,.15,.28);
    cube(g,"#e7ca8e",x,2.66,z,.26,.37,.26,.54);cube(g,"#3c4e47",x,2.9,z,.36,.09,.36);
  }
  function platform(g,city=false){
    let timepiece;
    patternedFloor(g,city?"#7e8584":"#81847a",city?"#77807f":"#899083");
    sky(g,city);for(const z of [2.04,2.2])cube(g,city?"#dbc182":"#d7c99f",0,.021,z,10.95,.024,.035);
    if(city){
      for(let x=-4.9;x<=4.9;x+=1.24){cube(g,"#4b6268",x,1.61,-2.54,.12,3.22,.16);cube(g,"#9db2af",x+.55,1.56,-2.61,.98,2.72,.065);}
      for(const z of [-2.51,-.86])cube(g,"#55696b",0,3.09,z,10.52,.17,.18);
      panel(g,.1,2.72,-2.36,4.4,.67,"PITTSBURGH","INTERCITY COACHES","#f0dfb3","#344c51","modern");
      panel(g,-3.69,1.62,-2.4,.96,.74,"04","BAY","#f4d092","#314d52","modern");
      panel(g,3.76,1.60,-2.4,1.08,.78,"WEST","CONCOURSE","#e4d8af","#374f53","modern");
      bench(g,-1.12,-1.17,2.75);bench(g,2.24,-1.17,2.05);timepiece=clock(g,-2.82,2.60,-2.40);
      lamplight(g,-.4,2.91,-1.6,"#e9c999",10);
    }else{
      stationGable(g);panel(g,0,2.26,-2.63,2.6,.63,"TOWN DEPOT","LOCAL COACH STOP","#f3d8a1","#40584b");
      bench(g,0,-1.69,3.05);lamp(g,-3.66,.42);lamp(g,3.7,.42);timepiece=clock(g,2.84,2.14,-2.63,.24);
      for(const xx of [-4.55,4.55])cube(g,"#e8e0c8",xx,.09,-.95,1.46,.18,5.22);
      lamplight(g,-2.5,2.4,-.7,"#f5c888",12);
    }
    // Small platform furniture leaves the recorded empty bench unoccupied.
    if(city){
      const timetable=group(g,-4.16,0,-1.86);panel(timetable,0,1.5,0,.73,.81,"DEPARTURES","INTERCITY","#d6d7ba","#435a59","modern");
      post(timetable,"#4a5d5a",0,.57,0,.046,1.13);
      for(const b of [-.21,0,.21])cube(g,"#d8c6a0",-3.38+b,1.35,-2.36,.11,.14,.04);
    }else{
      for(const x of [-3.79,3.83]){const f=group(g,x,0,-2.77);post(f,"#444f45",0,.42,0,.17,.79);post(f,"#7f8873",0,.83,0,.18,.07);}
    }
    return {clock:timepiece};
  }
  function reel(g,x,y,z,r,c="#c1b8a8"){
    const rgroup=group(g,x,y,z),p=post(rgroup,c,0,0,0,r,.13);p.rotation.x=Math.PI/2;
    rim(rgroup,"#3d3d39",0,0,.072,r*.90);const core=post(rgroup,"#554c4b",0,0,.091,r*.16,.025);core.rotation.x=Math.PI/2;
    for(let i=0;i<5;i++){const a=i*Math.PI*.4;ball(rgroup,"#5f5d59",r*.53*Math.sin(a),r*.53*Math.cos(a),.080,r*.18,r*.18,.014);}
    return rgroup;
  }
  function booth(g){
    patternedFloor(g,"#785e50","#806455",true);wall(g,"#435653","#816951");sideWalls(g,"#45524d","#766a55");curtain(g,-4.83,2.07,-2.91,.91,3.88,"#783b44","#954e51");
    panel(g,.8,2.87,-3.23,3.18,.93,"RIALTO","PROJECTION ROOM","#f7d295","#6c3d41");
    for(const x of [-2.83,3.55])windowPane(g,x,2.43,-3.33,1.43,.8,"#654c44",true);
    for(const x of [-2.75,-2.16,-1.57,-.98]){const shelf=group(g,x,0,-2.89);cube(shelf,"#66554c",0,.87,0,.50,1.22,.43);for(let j=0;j<5;j++)cube(shelf,"#95938a",0,.49+j*.13,.08,.44,.07,.30);}
    const m=group(g,-2.4,0,-.78);cube(m,"#384b48",0,.45,0,.43,.87,.50);cube(m,"#364644",0,1.11,0,.95,.62,.61);
    cube(m,"#697267",.56,1.14,.10,.36,.19,.29);ball(m,"#a49981",.74,1.14,.10,.099,.143,.117);
    const reels=[reel(m,-.34,1.69,.035,.32),reel(m,.23,1.80,.035,.34)];cube(m,"#3d403c",-.04,.08,0,1.02,.14,.73);
    // The restored projection equipment is idle while the crew records Alma.
    bench(g,1.32,-1.00,1.22);lamplight(g,1.6,3,-.47,"#ffbc7b",14);return {reels};
  }
  function recordingDesk(g){
    patternedFloor(g,"#737870","#817e6f");wall(g,"#52706c","#7a8271");sideWalls(g,"#4b6863","#798174");
    for(const x of [-4.03,-2.5,3.65])windowPane(g,x,2.47,-3.38,1.14,1.16,"#5a695d",true);
    panel(g,.6,2.87,-3.27,3.35,.76,"REGIONAL LINE","PORTABLE STATION PATCH","#f2d9a5","#375c56","modern");
    const desk=group(g,.15,0,-1.25);cube(desk,"#715847",0,.96,0,3.35,.18,1.07);
    for(const xx of [-1.41,1.41])for(const zz of [-.41,.41])cube(desk,"#465451",xx,.46,zz,.11,.92,.11);
    const machine=group(desk,-.44,1.41,-.1);cube(machine,"#354a48",0,0,0,1.64,.72,.45);
    const reels=[reel(machine,-.43,.05,.24,.22),reel(machine,.43,.05,.24,.22)];
    cube(machine,"#aba894",0,-.24,.268,1.43,.07,.07);
    const meters=[];for(let i=0;i<8;i++)meters.push(cube(desk,i<6?"#c6cf83":"#e89f65",.54+i*.115,1.282,.28,.074,.19,.05,.32));
    cube(desk,"#3c504d",1.00,1.13,.12,1.1,.19,.54);
    for(let i=0;i<6;i++){cube(desk,"#b9b29c",.66+i*.13,1.24,.18,.04,.04,.23);cube(desk,"#e7c38b",.66+i*.13,1.27,.20-(i%3)*.05,.075,.04,.06);}
    const cable=new T.CatmullRomCurve3([new T.Vector3(-1.4,.99,-1.05),new T.Vector3(-1.7,.15,-.7),new T.Vector3(-2.42,.08,-1.68),new T.Vector3(-3.01,.82,-2.98)]);
    const tube=new T.Mesh(new T.TubeGeometry(cable,26,.027,8,false),material("#333e39"));g.add(tube);
    panel(g,-3.11,1.14,-3.33,.79,.39,"LINE 1","","#e5d5a6","#344c44","modern");
    const tray=group(g,-1.25,1.10,-1.00);cube(tray,"#a08062",0,.002,0,.58,.047,.45);
    for(const side of [-1,1])cube(tray,"#8a705a",side*.285,.04,0,.029,.08,.45);
    panel(g,-1.24,.85,-.68,.58,.19,"INTAKE","","#e8d3ab","#4c5a50","modern");
    const deliveryCan=reel(g,-1.25,1.17,-1.00,.16,"#b3b0a3");deliveryCan.rotation.x=-Math.PI/2;deliveryCan.visible=false;
    lamplight(g,.45,2.96,-.47,"#fbd594",13);return {reels,meters,deliveryCan};
  }
  function hotel(g){
    patternedFloor(g,"#986b4e","#a87452",true);wall(g,"#b58d76","#89644d");sideWalls(g,"#9a7967","#8b6a50");
    for(const x of [-4.27,3.83]){windowPane(g,x,2.54,-3.36,1.32,1.87,"#725347");curtain(g,x-.73,2.46,-3.25,.32,2.39,"#91615a","#b07b69");}
    panel(g,0,2.78,-3.25,3.42,.81,"HEARTHSIDE","HOTEL  ·  FRONT DESK","#f3d9a3","#655245");
    const desk=group(g,0,0,-1.00);cube(desk,"#845c47",0,.60,0,3.92,1.18,1.02);cube(desk,"#6b5041",0,1.21,0,4.08,.12,1.14);
    for(let i=-1;i<=1;i++){cube(desk,"#a57853",i*1.23,.64,.53,1.09,.87,.038);cube(desk,"#88644b",i*1.23,.64,.555,.93,.73,.02);}
    cube(desk,"#426354",0,1.29,.08,2.38,.024,.62);
    const env=group(desk,-.06,1.318,.13);cube(env,"#efe1bf",0,.015,0,.77,.035,.42);
    for(const sign of [-1,1])bar(env,"#b08c6d",[sign*.375,.036,-.174],[0,.036,.055],.009);
    const seal=post(env,"#a65445",0,.037,.047,.049,.012);
    const bell=ball(desk,"#c2a260",1.45,1.36,.12,.15,.09,.15);post(desk,"#6b5a44",1.45,1.28,.12,.17,.034);
    const timepiece=clock(g,-2.44,2.69,-3.25,.34);lamplight(g,-.68,3,-.42,"#ffbd87",11);const slots=group(g,2.28,1.91,-3.20);cube(slots,"#715543",0,0,0,1.28,.80,.24);
    for(let ix=0;ix<4;ix++)for(let iy=0;iy<3;iy++){const xx=-.45+ix*.30,yy=-.22+iy*.22;
      cube(slots,"#493f36",xx,yy,.133,.25,.165,.029);cube(slots,"#c59a66",xx,yy-.042,.16,.065,.032,.016);}
    const postage=canvasTexture("postage",256,128,(c,w,h)=>{c.fillStyle="#e8d9b3";c.fillRect(0,0,w,h);
      c.strokeStyle="#8c6553";c.lineWidth=5;c.strokeRect(8,8,w-16,h-16);c.fillStyle="#815846";c.textAlign="center";c.font="bold 29px Georgia";c.fillText("PITTSBURGH",w/2,56);c.font="23px Georgia";c.fillText("POST",w/2,88);});
    const stamp=flat(env,.222,.039,-.075,.192,.098,postage);stamp.rotation.x=-Math.PI/2;
    return {env,bell,seal,clock:timepiece};
  }
  function coach(g){
    const c=group(g);cube(c,"#d3b490",0,.85,0,3.32,1.34,1.28);cube(c,"#526962",0,.50,.651,3.34,.28,.035);
    cube(c,"#e9c7a0",0,1.56,0,3.35,.19,1.29);for(let i=0;i<5;i++)cube(c,"#728f93",-1.33+i*.54,1.16,.654,.45,.49,.04);
    cube(c,"#5d786e",1.36,.99,.655,.42,.78,.045);cube(c,"#a7bdba",1.36,1.17,.685,.32,.35,.021);
    for(const x of [-1.03,1.01])for(const z of [-.62,.62]){const wheel=post(c,"#3a3c3b",x,.36,z,.33,.15);wheel.rotation.x=Math.PI/2;const hub=post(c,"#9a9c8d",x,.36,z*1.13,.17,.06);hub.rotation.x=Math.PI/2;}
    for(const z of [-.47,.47])ball(c,"#eed49d",1.68,.62,z,.035,.10,.086,.53);
    return c;
  }
  const config={
    ballroom:{build:ballroom,bg:"#706357",lit:"#ffe3b8",ground:"#625449",offset:[0,0]},
    depot:{build:g=>platform(g,false),bg:"#77888a",lit:"#e5e3cd",ground:"#6a7877",offset:[24,0]},
    terminal:{build:g=>platform(g,true),bg:"#637b88",lit:"#e2e9dd",ground:"#586b71",offset:[48,0]},
    rialto:{build:booth,bg:"#5e6056",lit:"#fcdfbc",ground:"#52584e",offset:[0,24]},
    station:{build:recordingDesk,bg:"#6b7a71",lit:"#f3e2bc",ground:"#52675e",offset:[24,24]},
    hotel:{build:hotel,bg:"#917963",lit:"#ffe2be",ground:"#746752",offset:[48,24]}
  };
  const clothes={
    Phil:{coat:"#a6654f",pants:"#4b4d50",skin:"#c89272",hair:"#65483c",accent:"#d8bc7f"},
    Rita:{coat:"#658c83",pants:"#48474f",skin:"#b57f62",hair:"#4b3934",accent:"#d6c299"},
    Larry:{coat:"#546e81",pants:"#494c4f",skin:"#af8267",hair:"#513d33",accent:"#9ca9a4"},
    Alma:{coat:"#856b82",pants:"#544d56",skin:"#bb8d77",hair:"#b5b8af",accent:"#cbb4a0"}
  };
  function figure(parent,name){
    const g=group(parent),c=clothes[name],hips=group(g,0,.85,0),body=group(hips);
    const torso=ball(body,c.coat,0,.31,0,.288,.422,.196);
    cube(body,c.accent,0,.50,.152,.064,.29,.068);ball(body,c.accent,0,.59,0,.22,.083,.18);
    for(let i=0;i<3;i++)ball(body,"#423e3b",.08,.18+i*.13,.167,.016,.016,.012);
    const hem=new T.Mesh(new T.CylinderGeometry(.237,.268,.23,12),material(c.coat));hem.scale.z=.65;hem.position.set(0,.079,0);body.add(hem);
    for(const side of [-1,1]){
      const lapel=cube(body,c.accent,side*.076,.49,.151,.058,.199,.04);lapel.rotation.z=-side*.29;
      const pocket=cube(body,c.hair,side*.169,.138,.145,.089,.014,.019);pocket.rotation.z=-side*.14;
    }
    const neck=group(body,0,.66,0);ball(neck,c.skin,0,.178,0,.186,.229,.163);
    ball(neck,c.hair,0,.303,-.03,.196,.133,.171);ball(neck,c.hair,-.141,.229,-.056,.056,.106,.11);
    ball(neck,c.skin,0,.161,.155,.044,.049,.039);const eyes=[],lids=[];
    for(const s of [-1,1]){eyes.push(ball(neck,"#49403a",s*.068,.209,.14,.014,.012,.012));
      const lid=ball(neck,"#533e34",s*.068,.205,.146,.029,.004,.005);lid.visible=false;lids.push(lid);}
    for(const sign of [-1,1]){
      ball(neck,c.skin,sign*.174,.168,-.013,.037,.057,.033);
      const brow=ball(neck,c.hair,sign*.069,.245,.143,.039,.009,.009);brow.rotation.z=sign*.08;
    }
    if(name==="Phil"){const fringe=ball(neck,c.hair,-.044,.307,.087,.147,.058,.091);fringe.rotation.z=.17;
      const scarf=ball(body,c.accent,-.083,.38,.16,.058,.119,.031);scarf.rotation.z=-.11;}
    if(name==="Rita"){ball(neck,c.hair,.014,.167,-.147,.157,.153,.114);const fringe=ball(neck,c.hair,.073,.257,.085,.087,.116,.073);fringe.rotation.z=.45;}
    if(name==="Alma"){ball(neck,c.hair,0,.255,-.17,.113,.098,.081);for(const s of [-1,1]){const lens=rim(neck,"#6a5a52",s*.070,.204,.158,.041);lens.scale.z=.023;}}
    if(name==="Larry"){ball(neck,"#435767",0,.335,-.03,.205,.073,.177);cube(neck,"#435767",0,.317,.12,.29,.033,.16);}
    const waist=ball(hips,c.pants,0,-.012,0,.236,.109,.140);
    const limbs={};for(const side of [-1,1]){
      const arm=group(body,side*.263,.51,0),elbow=group(arm,0,-.30,0);
      ball(arm,c.coat,0,-.14,0,.086,.187,.094);ball(elbow,c.coat,0,-.11,0,.074,.154,.077);ball(elbow,c.skin,0,-.266,.005,.063,.075,.065);
      ball(elbow,c.coat,0,.005,0,.073,.081,.082);
      const leg=group(hips,side*.125,-.01,0),knee=group(leg,0,-.39,0);ball(leg,c.pants,0,-.18,0,.103,.234,.116);
      ball(knee,c.pants,0,.012,0,.082,.096,.091);
      ball(knee,c.pants,0,-.176,0,.091,.216,.095);
      ball(knee,"#453d37",0,-.311,.012,.090,.111,.096);ball(knee,"#453d37",0,-.357,.051,.103,.083,.160);
      limbs[side<0?"l":"r"]={arm,elbow,leg,knee};
    }
    const held=group(limbs.r.elbow,0,-.26,.055);
    return {name,root:g,hips,body,neck,limbs,held,torso,eyes,lids};
  }
  function handheld(c,name){
    const g=group(c.held);if(name==="camera"){
      cube(g,"#424b49",0,.01,.025,.25,.17,.28);const l=post(g,"#393e40",0,.02,.185,.075,.09);l.rotation.x=Math.PI/2;
      ball(g,"#93a7a4",0,.019,.232,.06,.06,.015);cube(g,"#454b49",0,.115,.03,.16,.065,.08);
      const tally=ball(g,"#f37763",.102,.063,.162,.020,.020,.009,.68);g.userData.tally=tally;
    }else if(name==="mic"){post(g,"#555959",0,.105,0,.028,.23);ball(g,"#979996",0,.246,0,.065,.089,.067);}
    else if(name==="reel"){reel(g,0,.025,0,.16,"#b3b0a3");}return g;
  }
  function buildSet(parent,id){
    const cfg=config[id],root=group(parent,...[cfg.offset[0],0,cfg.offset[1]]);root.name="Editorial_"+id;const props=cfg.build(root);
    const under=cube(root,cfg.ground,0,-.49,0,180,.35,130);under.receiveShadow=true;under.castShadow=false;
    return {root,props,cfg};
  }
  window.RialtoSets={buildSet,config,figure,handheld,coach};
})();
