"use strict";
window.WinterInterior=(()=>{
  // Location shots are optional presentation layers. All persistent prop values come from the receipt.
  const tau=Math.PI*2;
  const paints={reporter:{coat:"#a85c49",lit:"#bd7057",dark:"#793f39",skin:"#d3a083",shadow:"#ba846b",hair:"#53463e",hat:"#405052",trim:"#edbd69"},
    producer:{coat:"#617b89",lit:"#829ba1",dark:"#475e6d",skin:"#a87354",shadow:"#875b46",hair:"#473c34",hat:"#655c70",trim:"#d3b38e"},
    camera:{coat:"#6d8169",lit:"#849b78",dark:"#536b59",skin:"#d0a380",shadow:"#ac8064",hair:"#715445",hat:"#8a7050",trim:"#ddbd89"}};
  const rect=(c,x,y,w,h,col)=>{c.fillStyle=col;c.fillRect(x,y,w,h);};
  const ellipse=(c,x,y,rx,ry,col)=>{c.fillStyle=col;c.beginPath();c.ellipse(x,y,rx,ry,0,0,tau);c.fill();};
  function poly(c,pts,col){c.fillStyle=col;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fill();}
  function stroke(c,pts,col,w){c.strokeStyle=col;c.lineWidth=w;c.lineCap="round";c.lineJoin="round";c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();}
  function text(c,t,x,y,size,col,face="Georgia",align="center",max=1000){c.fillStyle=col;c.font="bold "+size+"px "+face;c.textAlign=align;c.textBaseline="middle";c.fillText(t,x,y,max);}
  function glow(c,x,y,r,col){const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,col);g.addColorStop(1,"rgba(255,216,130,0)");c.fillStyle=g;c.fillRect(x-r,y-r,2*r,2*r);}
  function framed(c,x,y,w,h,outer,inside){rect(c,x-4,y-4,w+8,h+8,outer);rect(c,x,y,w,h,inside);}
  function windowView(c,x,y,w,h,night,city=false,t=0){
    framed(c,x,y,w,h,"#4c5a53",night?"#667987":"#b6cac6");
    c.save();c.beginPath();c.rect(x,y,w,h);c.clip();
    for(let i=-1;i<w/34+2;i++){
      const left=x+i*36,high=25+Math.abs(Math.sin(i*2.9+1))*35;
      if(city){rect(c,left,y+h-high,32,high,["#849997","#8d9a96","#9baca2"][(i+4)%3]);for(let j=0;j<3;j++)for(let k=0;k<3;k++)rect(c,left+4+j*8,y+h-high+6+k*11,4,6,night?"#d8bd87":"#748b8c");}
      else{rect(c,left,y+h-high*.58,34,high*.65,"#a0aaa0");poly(c,[[left-5,y+h-high*.55],[left+14,y+h-high*.92],[left+38,y+h-high*.58]],"#e5e7d8");}
    }
    for(let i=0;i<22;i++){const xx=x+(((i*36.77+t*2)%w)+w)%w,yy=y+((i*14.21+t*3)%h);rect(c,xx,yy,1.7,1.7,"#edf0e2");}
    rect(c,x,y+h-7,w,7,"#e2e4d6");
    c.restore();rect(c,x+w*.48,y,4,h,"#62726b");rect(c,x,y+h*.53,w,4,"#62726b");rect(c,x-6,y+h,w+12,7,"#c5b49b");
  }
  function floor(c,w,at,base,accent,check=false){
    rect(c,0,at,w,540-at,base);const van=w*.49;
    for(let j=0;j<22;j++){
      const x=(j-7)*w/7.4,tx=van+(x-van)*.31;
      stroke(c,[[tx,at],[x,540]],accent,.8);
      if(check){
        const right=x+w/7.4,rr=van+(right-van)*.31;
        const atp=(a,b,f)=>a+(b-a)*f,ys=[0,.13,.32,.59,1];
        for(let k=0;k<4;k++)if((j+k)%2===0){const p=ys[k],q=ys[k+1];poly(c,[[atp(tx,x,p),atp(at,540,p)],[atp(rr,right,p),atp(at,540,p)],[atp(rr,right,q),atp(at,540,q)],[atp(tx,x,q),atp(at,540,q)]],"rgba(61,81,75,.20)");}
      }
    }
    for(const f of [.13,.32,.59])stroke(c,[[0,at+(540-at)*f],[w,at+(540-at)*f]],accent,1);
  }
  function pendant(c,x,y,shade){
    stroke(c,[[x,-3],[x,y]],"#555b52",2);
    poly(c,[[x-5,y],[x+6,y],[x+24,y+19],[x+31,y+24],[x-31,y+24],[x-22,y+18]],shade);
    ellipse(c,x,y+24,31,3,"#d8c38c");ellipse(c,x,y+25,6,4.5,"#f8dea1");glow(c,x,y+30,43,"rgba(247,217,149,.18)");
  }
  function clock(c,x,y,r,slot){
    ellipse(c,x+2,y+3,r+4,r+4,"rgba(52,57,46,.20)");ellipse(c,x,y,r+3,r+3,"#52665c");ellipse(c,x,y,r,r,"#e8dec6");
    for(let i=0;i<12;i++){const a=i*Math.PI/6;stroke(c,[[x+Math.sin(a)*r*.79,y-Math.cos(a)*r*.79],[x+Math.sin(a)*r*.91,y-Math.cos(a)*r*.91]],"#59655b",i%3?1:2);}
    const h=[6,9.5,13,19][slot]*Math.PI/6,m=slot===1?Math.PI:0.0;
    stroke(c,[[x+Math.sin(h)*r*.47,y-Math.cos(h)*r*.47],[x,y],[x+Math.sin(m)*r*.68,y-Math.cos(m)*r*.68]],"#47564e",2.3);
    ellipse(c,x,y,2,2,"#a06b49");
  }
  function planted(c,x,y,s){
    c.save();c.translate(x,y);c.scale(s,s);
    poly(c,[[-12,-18],[13,-18],[9,2],[-9,2]],"#927c62");rect(c,-14,-22,29,5,"#b69b77");
    for(let i=0;i<7;i++){const a=(i-3)*.23,xx=Math.sin(a)*33,yy=-25-Math.cos(a)*28;
      stroke(c,[[0,-20],[xx,yy]],"#586e58",2);poly(c,[[0,-22],[xx-6,yy+10],[xx,yy],[xx+5,yy+10]],i%2?"#879373":"#6c856c");}
    c.restore();
  }
  function phoneBox(c,x,y){
    framed(c,x-20,y-58,40,72,"#52665b","#7c9382");rect(c,x-15,y-52,30,18,"#d6d3ae");
    for(let j=0;j<3;j++)for(let i=0;i<3;i++)rect(c,x-7+i*6,y-23+j*7,3.5,3.5,"#465c54");
    stroke(c,[[x-14,y-35],[x-17,y-29],[x-17,y-9],[x-12,y-5]],"#324d48",5);rect(c,x+4,y+5,7,2,"#4e6659");
  }
  function hotel(c,w,s){
    rect(c,0,0,w,340,"#c9b88e");
    for(let x=4;x<w;x+=22){rect(c,x,0,1,270,"rgba(100,102,70,.18)");for(let y=17;y<235;y+=36)poly(c,[[x-3,y],[x,y-5],[x+3,y],[x,y+5]],"rgba(146,139,95,.22)");}
    rect(c,0,238,w,104,"#77856c");rect(c,0,234,w,8,"#a1a483");rect(c,0,243,w,2,"#637861");
    for(let x=0;x<w;x+=58){rect(c,x,248,2,86,"#687d65");rect(c,x+3,250,44,1,"#96a088");}floor(c,w,341,"#928e77","#7e826d");
    const winW=Math.max(114,w*.24);windowView(c,w*.13,86,winW,125,s.slot===3,false,s.t);
    poly(c,[[w*.13-8,74],[w*.13+22,74],[w*.13+10,202],[w*.13-5,226]],"#9c735d");
    poly(c,[[w*.13+winW-15,75],[w*.13+winW+12,75],[w*.13+winW+14,224],[w*.13+winW+1,205]],"#ad8067");
    const x=w*.70;framed(c,x-35,91,70,81,"#8d7d61","#efe9d6");rect(c,x-35,91,70,20,"#a35e4c");text(c,"FEB",x,102,11,"#f4ecd9","Menlo");text(c,"2",x,142,38,"#49594e");
    // Lobby counter and brass key rack.
    const desk=w*.60;rect(c,desk,271,w*.39,85,"#927356");rect(c,desk-5,268,w*.40,9,"#594f41");rect(c,desk+8,288,w*.374,52,"#a88b63");rect(c,desk+16,295,w*.35,3,"#bc9b72");
    for(let i=0;i<5;i++){rect(c,w*.83+i*9,193,3,26,"#9a7957");ellipse(c,w*.83+i*9+1.5,194,2.5,2.5,"#d9be87");}
    const radio=desk+w*.09;rect(c,radio-27,245,56,23,"#a47855");rect(c,radio-22,249,29,13,"#6d6855");for(let i=0;i<6;i++)rect(c,radio-20+i*4.3,250,1.5,10,"#9c9173");
    ellipse(c,radio+18,257,5,5,"#d3ba89");stroke(c,[[radio+21,245],[radio+28,219]],"#6f7768",1.2);
    if(s.facts?.marked){const xx=w*.13+winW*.60;stroke(c,[[xx-4,215],[xx+4,221]],"#51483b",2.1);stroke(c,[[xx+4,215],[xx-4,221]],"#51483b",2.1);}
    planted(c,w*.10,359,.9);pendant(c,w*.50,61,"#677d6c");
  }
  function diner(c,w,s){
    rect(c,0,0,w,334,"#b6c6b1");for(let x=0;x<w;x+=25)rect(c,x,204,1.2,111,"#99ad97");
    rect(c,0,203,w,4,"#e9d6ad");rect(c,0,211,w,6,"#a87b61");floor(c,w,331,"#dbd5bf","#aeafa0",true);
    windowView(c,w*.10,72,w*.35,119,s.slot===3,false,s.t);windowView(c,w*.64,73,w*.26,114,s.slot===3,false,s.t);
    for(const x of [w*.17,w*.36]){rect(c,x-33,256,66,61,"#887b68");rect(c,x-38,258,75,14,"#be876d");rect(c,x-33,227,66,33,"#b87e66");rect(c,x-34,227,68,5,"#d59d7c");}
    const cx=w*.68;rect(c,cx-65,244,64,41,"#899a85");rect(c,cx-62,239,56,9,"#c9bd9c");rect(c,cx-58,247,47,13,"#5a7265");
    ellipse(c,cx-46,266,7,10,"#c0b098");ellipse(c,cx-27,266,7,10,"#bcb59a");
    rect(c,w*.54,291,w*.45,69,"#99a997");rect(c,w*.53,284,w*.48,9,"#f1dfbc");rect(c,w*.53,293,w*.48,4,"#8a7f67");
    for(let x=w*.54;x<w;x+=29)rect(c,x,304,2,49,"#889d88");
    const count=s.facts?.dishes;
    if(Number.isFinite(count))for(let i=0;i<count;i++){
      const px=w*.67+i*37,py=283;
      for(let j=0;j<4;j++){ellipse(c,px-10+j*6,py-10,4.8,9.2,"#aab8a9");ellipse(c,px-9+j*6,py-10,3.65,8.2,"#eee8cf");}
      rect(c,px-16,py-7,34,6,"#8b9f91");stroke(c,[[px-17,py-9],[px-14,py-2],[px+17,py-2],[px+19,py-9]],"#637d75",1.6);
    }
    rect(c,w*.86,264,4,18,"#a66550");rect(c,w*.86-1,260,6,4,"#bdb59f");rect(c,w*.86+11,269,7,13,"#ded6b8");
    pendant(c,w*.40,54,"#8e6a53");pendant(c,w*.74,56,"#8e6a53");
    text(c,"BEA’S DINER",w*.52,129,17,"#697d68","Georgia","center",w*.16);
  }
  const channelNames={live_report:"LIVE REPORT",silent_live_reporter_line:"SILENT LINE",camera_take:"CAMERA TAPE",producer_live:"PRODUCER MIC",silent_producer_mic:"SILENT MIC",filed_forecast:"FILED REEL",empty_selected_return:"EMPTY RETURN",station_ident:"STATION ID"};
  function studio(c,w,s){
    rect(c,0,0,w,339,"#839b90");for(let x=3;x<w;x+=17)for(let y=40;y<219;y+=16)ellipse(c,x,y,1,1,"#719081");
    floor(c,w,337,"#82897b","#6f7c6d");rect(c,0,243,w,93,"#63796d");
    windowView(c,w*.11,87,w*.31,114,s.slot===3,false,s.t);
    const bulletin=s.facts?.bulletin;const aired=!!s.facts?.aired||!!bulletin?.channel,signX=w*.64;
    framed(c,signX-44,102,88,29,"#485b50",aired?"#ad6049":"#6b7768");text(c,"ON AIR",signX,117,15,aired?"#f8dfb3":"#a4ab92","Menlo");
    if(bulletin?.channel){
      const ch=channelNames[bulletin.channel]||bulletin.channel.replaceAll("_"," ").toUpperCase();framed(c,signX-57,148,114,29,"#58695c","#3f584e");
      text(c,ch,signX,162,10,"#d4dbad","Menlo","center",108);
    }
    const dx=w*.54;rect(c,dx,267,w*.39,83,"#766d59");poly(c,[[dx,265],[dx+13,238],[w*.91,238],[w*.94,265]],"#9d9f87");
    for(let i=0;i<8;i++){let xx=dx+15+i*(w*.30/8);stroke(c,[[xx,245],[xx-3,259]],"#607367",1.5);rect(c,xx-4,247+(i%3)*3,5,3,"#ded3ac");}
    stroke(c,[[dx+w*.08,241],[dx+w*.09,205],[dx+w*.02,186]],"#445951",4);
    ellipse(c,dx+w*.015,184,7,12,"#485d55");stroke(c,[[dx+w*.01,180],[dx+w*.02,184]],"#a5b29f",1);
    rect(c,w*.14,274,w*.28,25,"#6d6b59");rect(c,w*.15,264,w*.26,11,"#e2d9bc");
    for(let i=1;i<16;i++){const xx=w*.15+i*w*.26/16;rect(c,xx,264,1,11,"#817d6c");if(i%4)rect(c,xx-1,264,3,6,"#495b52");}
    for(const xx of [.16,.38])rect(c,w*xx,298,7,46,"#675f4e");
    clock(c,w*.83,165,22,s.slot);pendant(c,w*.52,50,"#5e7669");
  }
  function terminal(c,w,s,city){
    rect(c,0,0,w,337,city?"#a8b8ae":"#b5bca1");for(let x=0;x<w;x+=49)for(let y=33;y<330;y+=31){rect(c,x+(y%2?8:0),y,46,1,"rgba(87,112,98,.18)");}
    floor(c,w,334,"#c0c1ad","#a8b09e");rect(c,0,300,w,8,"#8f9c8d");
    windowView(c,w*.10,117,w*.39,125,s.slot===3,city,s.t);
    const tx=w*.62;framed(c,tx-58,101,116,49,"#587367","#344f4b");text(c,"PITTSBURGH",tx,113,12,"#e3dcc2","Menlo");
    text(c,city?"ARRIVALS":"1:00 PM  →",tx,135,14,"#e6d198","Menlo");
    clock(c,w*.82,w<430?65:112,w<430?15:20,s.slot);phoneBox(c,w*.72,237);
    for(let i=0;i<2;i++){const xx=w*(.15+i*.16);rect(c,xx,274,w*.13,14,"#9e9d7c");rect(c,xx+2,244,w*.13-4,28,"#9f9c7d");rect(c,xx+4,287,4,34,"#657b69");rect(c,xx+w*.13-8,287,4,34,"#657b69");}
    pendant(c,w*.49,45,"#7b8972");planted(c,w*.90,350,.78);
  }
  function square(c,w,s){
    const evening=s.slot===3;rect(c,0,0,w,540,evening?"#84969a":"#c4d3ca");
    for(let i=0;i<15;i++){const x=i*w/12-w*.08,h=47+(i%3)*12;rect(c,x,203-h,w*.09,h+44,"#a0aaa0");
      poly(c,[[x-6,203-h],[x+w*.04,174-h],[x+w*.10,203-h]],"#e3e5d5");}
    rect(c,0,238,w,302,"#d9ddce");for(let j=0;j<30;j++){const x=((j*87)%Math.ceil(w));stroke(c,[[x,285+j%4*20],[x+13,283+j%4*20]],"#c4cebf",2);}
    let cx=w*.62;
    poly(c,[[cx-105,183],[cx,114],[cx+105,183]],"#8ba18b");poly(c,[[cx-101,181],[cx,112],[cx+83,167],[cx+41,151],[cx+25,153],[cx-2,132],[cx-42,157],[cx-54,156]],"#e5e9d9");
    rect(c,cx-87,183,7,99,"#7d9683");rect(c,cx+80,183,7,99,"#7d9683");rect(c,cx-90,268,180,13,"#8a9b81");rect(c,cx-98,280,196,8,"#9daa92");
    rect(c,cx-32,245,57,20,"#8c7d61");ellipse(c,cx-4,237,12.0,12.8,"#95755c");ellipse(c,cx-4,225,8,7.2,"#a48769");ellipse(c,cx-10,221,3.1,3.2,"#9c8063");ellipse(c,cx+1,221,3.3,3.2,"#9c8063");
    const pts=[];for(let i=0;i<=18;i++){const x=i*w/18;pts.push([x,70+19*Math.sin(Math.PI*i/18)]);}stroke(c,pts,"#879783",1.1);
    for(let i=1;i<18;i+=2){const [a,b]=[pts[i],pts[i+1]];poly(c,[a,b,[(a[0]+b[0])/2,a[1]+12]],["#b97e63","#c3ab74","#83a28c"][i%3]);}
  }
  function hand(c,x,y,p){ellipse(c,x,y,4.8,5.3,p.skin);}
  function actor(c,p,x,y,size,t,facing,progress){
    const role=p.role,pal=paints[role]||paints[p.skin==="Bea"?"camera":"producer"],act=p.action||"";
    const talk=act.startsWith("talk_to_")||act==="file_forecast"||act==="record_forecast";
    const calling=/call_(sister|home|live_report)|send_camera_take/.test(act),clearing=/clear.*table/.test(act),marking=act==="leave_pencil_mark",filming=/film_|shoot_|record_band/.test(act);
    const pulse=Math.sin(t*4.6),bend=clearing?Math.sin(Math.PI*progress)*4:0;
    c.save();c.translate(x,y);c.scale(size,size);ellipse(c,1,0,27,5,"rgba(57,75,65,.18)");c.scale(facing,1);
    // Practical winter clothing, role equipment and small action-specific gestures.
    poly(c,[[-13,-44],[-1,-44],[-3,-3],[-11,-3]],"#46565a");poly(c,[[-1,-45],[12,-44],[15,-3],[6,-3]],"#515c5b");
    poly(c,[[-13,-6],[-3,-6],[0,-3],[0,-1],[-16,-1]],"#433e36");poly(c,[[5,-6],[15,-6],[20,-3],[20,0],[3,0]],"#433e36");
    c.save();c.translate(bend,0);
    poly(c,[[-12,-95],[-3,-99],[9,-96],[14,-90],[18,-47],[13,-39],[-17,-40],[-18,-48]],pal.coat);
    poly(c,[[-13,-93],[-3,-97],[-1,-43],[-15,-41],[-17,-51]],pal.dark);
    stroke(c,[[5,-91],[6,-66],[9,-44]],pal.lit,1.4);
    for(let i=0;i<3;i++)ellipse(c,8,-80+i*13,1.1,1.3,"#dec39b");
    stroke(c,[[-9,-91],[-17,-73],[-17,-59]],pal.dark,8);
    if(clearing){stroke(c,[[10,-89],[19,-73],[28+bend,-73]],pal.lit,8);ellipse(c,27+bend,-74,11,2.5,"#e5e0c7");hand(c,28+bend,-72,pal);}
    else if(marking){stroke(c,[[10,-89],[25,-93],[32,-107+pulse*1.5]],pal.lit,7.6);hand(c,32,-107+pulse*1.5,pal);stroke(c,[[32,-109+pulse],[38,-111+pulse]],"#645443",2.0);}
    else if(calling){stroke(c,[[10,-88],[24,-83],[13,-109]],pal.lit,7.7);hand(c,13,-109,pal);stroke(c,[[11,-117],[15,-113],[17,-104],[13,-100]],"#3e5952",4);}
    else if(role==="camera"&&filming){stroke(c,[[10,-88],[19,-82],[24,-103]],pal.lit,7.5);hand(c,24,-103,pal);}
    else{let v=talk?pulse*2.3:0;stroke(c,[[10,-89],[17,-74],[talk?25:16,-66+v]],pal.lit,8);hand(c,talk?26:16,-64+v,pal);}
    hand(c,-17,-56,pal);
    if(role==="producer"){poly(c,[[-20,-82],[-6,-80],[-9,-57],[-23,-60]],"#8e7960");poly(c,[[-18,-80],[-8,-78],[-11,-60],[-21,-62]],"#e6dec0");}
    if(role==="camera"){
      const cy=filming?-113:-72,cx=filming?10:-4;
      rect(c,cx,cy,25,14,"#405254");rect(c,cx+4,cy-3,9,3,"#5d6963");poly(c,[[cx+23,cy+3],[cx+32,cy],[cx+32,cy+13],[cx+23,cy+10]],"#3d4f4f");
      if(filming)ellipse(c,cx+19,cy+4,1.6,1.6,"#f69e78");stroke(c,[[cx+2,cy+4],[cx-4,cy+1]],"#4c5d58",3);
    }
    rect(c,-5,-106,11,12,pal.shadow);
    poly(c,[[-7,-127],[1,-132],[11,-128],[14,-118],[18,-113],[14,-111],[13,-105],[7,-101],[-3,-104],[-8,-115]],pal.skin);
    poly(c,[[-8,-125],[-2,-130],[2,-124],[-1,-117],[-2,-111],[-5,-108],[-9,-116]],pal.hair);
    ellipse(c,-2,-115,2.9,4,pal.shadow);stroke(c,[[8,-120],[12,-119]],pal.hair,1.35);ellipse(c,11,-117,1.0,1.15,"#47473c");
    stroke(c,[[8,-107],[13,-107+(talk?pulse*.7:0)]],pal.shadow,1.0);
    poly(c,[[-11,-128],[-9,-133],[-3,-137],[6,-136],[12,-132],[12,-126],[-10,-125]],pal.hat);rect(c,-11,-128,24,3,pal.trim);
    if(role==="reporter")poly(c,[[-12,-125],[15,-126],[20,-124],[10,-122]],pal.hat);
    else if(role==="camera")ellipse(c,0,-137,3.4,3.4,pal.trim);
    poly(c,[[-9,-99],[0,-103],[10,-99],[11,-95],[3,-92],[-7,-95]],pal.trim);poly(c,[[4,-95],[10,-94],[11,-76],[6,-78]],pal.trim);
    if(role==="reporter"&&/record|forecast|talk_to/.test(act)&&!calling){rect(c,22,-74,5,12,"#536561");ellipse(c,24.5,-76,4.2,5,"#43595b");}
    c.restore();c.restore();
  }
  function badge(c,name,x,y){
    c.font="bold 10px Menlo,monospace";const w=c.measureText(name.toUpperCase()).width+12;
    rect(c,x-w/2,y-6,w,14,"rgba(45,65,56,.82)");text(c,name.toUpperCase(),x,y+1,10,"#f0e5c6","Menlo");
  }
  const bg={inn:hotel,diner,studio,square,depot:(c,w,s)=>terminal(c,w,s,false),Pittsburgh:(c,w,s)=>terminal(c,w,s,true)};
  function draw(canvas,s,place,v){
    const c=canvas.getContext("2d"),scale=v.height/540,w=v.width/scale;
    c.setTransform(scale*v.dpr,0,0,scale*v.dpr,0,0);bg[place](c,w,s);
    const focus=s.cameraSubject,here=s.people.filter(p=>p.name!==focus.name&&p.scene===focus.scene&&p.at===place&&!p.moving&&p.visible!==false);
    const glyphScale=Math.max(.84,Math.min(1.20,w/490));
    // The selected character is in the foreground. Others only appear if the receipt places them here.
    if(here.length){here.forEach((p,i)=>{const x=w*(i===0?.66:.27),y=365+i*7;actor(c,p,x,y,glyphScale*.87,s.t,-1,s.actionProgress||0);badge(c,p.name,x,y+14);});}
    let focusX=w*(here.length?.42:.49),fy=406;
    if(place==="Pittsburgh"&&/call_(sister|home|live_report)|send_camera_take/.test(focus.action||"")){focusX=w*.72-36*glyphScale;fy=237+105*glyphScale*1.19;}
    if(place==="diner"&&/clear.*table/.test(focus.action||"")){focusX=w*.60-12*glyphScale;fy=283+74*glyphScale*1.19;}
    if(place==="inn"&&focus.action==="leave_pencil_mark"){focusX=w*.13+Math.max(114,w*.24)*.60-36*glyphScale*1.19;fy=217+108*glyphScale*1.19;}
    actor(c,focus,focusX,fy,glyphScale*1.19,s.t,1,s.actionProgress||0);
    if(/call_(home|sister|live_report)|send_camera_take/.test(focus.action||"")&&place==="Pittsburgh"){
      const x=focusX+16*glyphScale*1.19,y=fy-107*glyphScale*1.19;stroke(c,[[x,y],[x+10,y+37],[x+32,y+42],[w*.72-14,232]],"#53675c",1.4);
    }
    if(focus.role==="producer"&&/^(patch_reporter_line|patch_camera_line|host_bulletin|play_filed_forecast)$/.test(focus.action||"")){
      const x=Math.min(w-69,focusX+35*glyphScale),y=fy-62*glyphScale;
      rect(c,x,y+33,5,37,"#5b685c");rect(c,x+63,y+33,5,37,"#5b685c");
      poly(c,[[x-4,y+5],[x+5,y-2],[x+64,y-2],[x+70,y+5],[x+70,y+34],[x-4,y+34]],"#566b60");
      framed(c,x+3,y+6,60,12,"#3f514a","#304a42");
      const channel=s.facts?.bulletin?.channel;
      text(c,channelNames[channel]||"RETURN",x+33,y+12,6.6,channel?"#ead29a":"#b1c1a2","Menlo","center",56);
      for(let i=0;i<4;i++){rect(c,x+7+i*11,y+22,7,5,"#90a58a");}
      ellipse(c,x+58,y+25,2,2,channel?"#edb57b":"#78897b");
    }
    badge(c,focus.name,focusX,fy+15);
    if(s.slot===3){rect(c,0,0,w,540,"rgba(44,64,84,.15)");}
    const light=c.createLinearGradient(0,0,w,540);light.addColorStop(0,"rgba(248,224,163,.12)");light.addColorStop(.50,"rgba(246,217,142,0)");light.addColorStop(1,"rgba(50,73,64,.12)");c.fillStyle=light;c.fillRect(0,0,w,540);
    c.setTransform(v.dpr,0,0,v.dpr,0,0);
  }
  return {draw};
})();
