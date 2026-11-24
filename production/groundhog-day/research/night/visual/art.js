"use strict";
window.WinterArt = (() => {
  const W=window.WinterMap, P=(x,y,z=0)=>W.iso({x,y},z);
  const sceneNames={town:"Mill Creek",city:"Pittsburgh"};
  function color(hex,d){const n=parseInt(hex.slice(1),16),clamp=v=>Math.max(0,Math.min(255,v+d));return `rgb(${clamp(n>>16)},${clamp((n>>8)&255)},${clamp(n&255)})`;}
  function random(seed){let t=seed|0;return ()=>{t=(t+0x6D2B79F5)|0;let n=Math.imul(t^t>>>15,1|t);n^=n+Math.imul(n^n>>>7,61|n);return ((n^n>>>14)>>>0)/4294967296;};}
  function poly(c,pts,fill,stroke=null,width=1){c.beginPath();pts.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}}
  function line(c,pts,fill,width=1){c.beginPath();pts.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.strokeStyle=fill;c.lineWidth=width;c.stroke();}
  function tile(c,x,y,w,d,z,fill){poly(c,[P(x,y,z),P(x+w,y,z),P(x+w,y+d,z),P(x,y+d,z)],fill);}
  function box(c,x,y,w,d,b,h,front,side,top){
    poly(c,[P(x,y+d,b),P(x+w,y+d,b),P(x+w,y+d,b+h),P(x,y+d,b+h)],front);
    poly(c,[P(x+w,y,b),P(x+w,y+d,b),P(x+w,y+d,b+h),P(x+w,y,b+h)],side);
    tile(c,x,y,w,d,b+h,top);
  }
  function oval(c,x,y,rx,ry,fill){c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();}
  function frontRect(c,x,y,z,w,h,fill){poly(c,[P(x,y,z),P(x+w,y,z),P(x+w,y,z+h),P(x,y,z+h)],fill);}
  function sideRect(c,x,y,z,w,h,fill){poly(c,[P(x,y,z),P(x,y+w,z),P(x,y+w,z+h),P(x,y,z+h)],fill);}
  function faceText(c,text,x,y,z,maxWidth,fg,fontSize=11){
    const at=P(x,y,z);c.save();c.transform(1,18/37,0,1,at.x,at.y);c.font=`bold ${fontSize}px Georgia, serif`;c.textAlign="center";c.textBaseline="middle";c.fillStyle=fg;c.fillText(text,0,0,maxWidth);c.restore();
  }
  function ground(seed,scene){
    const c=document.createElement("canvas");c.width=2100;c.height=1500;const g=c.getContext("2d");
    const ox=1050,oy=270;g.translate(ox,oy);g.fillStyle="#e0e4dc";g.fillRect(-ox,-oy,c.width,c.height);
    const rng=random(seed);
    for(let i=0;i<750;i++){
      const u=-13+rng()*51,v=-13+rng()*51,sz=.1+rng()*2.5;
      tile(g,u,v,sz,sz*.59,0,["#dce1d8","#e5e8e0","#e8ebe3","#d9e0d9","#e4e7dc"][i%5]);
    }
    // Snowbanks and ploughed carriageways. Width is physical, so all cameras share one map.
    for(const [a,b,r] of W.roads[scene]){
      const horizontal=a[1]===b[1],len=horizontal?b[0]-a[0]:b[1]-a[1];
      function stripe(offset,width,fill){
        if(horizontal)tile(g,a[0],a[1]+offset-width/2,len,width,0,fill);
        else tile(g,a[0]+offset-width/2,a[1],width,len,0,fill);
      }
      stripe(0,r+1.15,"#cbd0c8");stripe(0,r+.85,"#d7d8cb");stripe(0,r+.36,"#b4b9b0");stripe(0,r,"#9ba8a3");
      stripe(-r*.26,.055,"#aebbaf");stripe(r*.27,.06,"#adb6ad");
      for(let i=.35;i<len;i+=1.1){
        if(horizontal)tile(g,a[0]+i,a[1]-.024,.48,.048,0,"#dcd6b7");
        else tile(g,a[0]-.024,a[1]+i,.048,.48,0,"#dcd6b7");
      }
      for(let i=0;i<len;i+=.57){
        const s=r/2+.3;
        if(horizontal)line(g,[P(a[0]+i,a[1]+s),P(a[0]+i,a[1]+s+.29)],"#bbc3ba",.7);
        else line(g,[P(a[0]+s,a[1]+i),P(a[0]+s+.29,a[1]+i)],"#bbc3ba",.7);
      }
    }
    if(scene==="town"){
      tile(g,10.7,11.55,4.6,3.3,0,"#c6cabe");
      for(let u=10.75;u<15.26;u+=.38)for(let v=11.58;v<14.8;v+=.36){
        tile(g,u,v,.36,.34,0,["#c8c6b7","#cecdba","#c9cbbb","#d6d2c0"][Math.floor(rng()*4)]);
      }
      // A dated, usable coach platform beside the road.
      tile(g,15.7,12.55,4.05,1.30,0,"#cbcbba");tile(g,15.73,13.78,3.99,.085,0,"#d0b768");
      for(const [ix,iy] of [[9.45,10.35],[9.45,16.7]]){
        for(let i=0;i<6;i++){
          tile(g,ix-1.43,iy-.7+i*.255,.33,.13,0,"#e5e6d8");
          tile(g,ix-.69+i*.255,iy+1.06,.13,.33,0,"#e5e6d8");
        }
      }
    }else{
      tile(g,5.65,9.45,7.9,1.0,0,"#b5bcb2");tile(g,5.65,10.37,7.9,.075,0,"#c7b26b");
      for(let i=0;i<7;i++)tile(g,14.5-.82+i*.26,12.0+.99,.13,.38,0,"#e7e8db");
    }
    for(let i=0;i<3800;i++){
      const x=rng()*2050-1025,y=rng()*1350-210;
      g.fillStyle=rng()>.48?"rgba(253,250,232,.15)":"rgba(88,114,111,.065)";
      g.fillRect(x,y,.7+rng()*2.2,.55+rng()*.7);
    }
    return {img:c,ox,oy};
  }
  function roof(c,b){
    const e=.20,x=b.x-e,y=b.y-e,w=b.w+2*e,d=b.d+2*e,h=b.h,r=h+(b.kind==="hotel"?.85:.58);
    poly(c,[P(x,y,h),P(x+w,y,h),P(x+w,y+d/2,r),P(x,y+d/2,r)],"#d6dedb");
    poly(c,[P(x,y+d/2,r),P(x+w,y+d/2,r),P(x+w,y+d,h),P(x,y+d,h)],"#fbf8e9");
    poly(c,[P(x+w,y,h),P(x+w,y+d,h),P(x+w,y+d/2,r)],color(b.side,9));
    line(c,[P(x+.04,y+d/2,r+.025),P(x+w-.04,y+d/2,r+.025)],"#f7f6e6",2.1);
    line(c,[P(x,y+d,h-.045),P(x+w,y+d,h-.045)],b.roof,3.3);
    line(c,[P(x+w,y,h),P(x+w,y+d/2,r),P(x+w,y+d,h)],b.roof,2);
    for(let i=.1;i<w-.1;i+=.35){
      const v=((Math.sin(i*17+b.x)+1)*.5);if(v>.2)line(c,[P(x+i,y+d-.1,h+.04),P(x+i+.15,y+d-.1,h+.04)],"#dedfd1",1.1);
    }
    if(b.kind==="hotel"){
      for(let i=1;i<=2;i++){
        const dx=x+w*(i/3);box(c,dx-.19,y+d*.63,.38,.34,r-.35,.44,"#b48368","#a17c69","#f5f0df");
        frontRect(c,dx-.115,y+d*.63+.35,r-.23,.22,.25,"#566a70");
      }
    }
    if(["hotel","house","shop","radio"].includes(b.kind))box(c,x+w*.72,y+d*.31,.29,.28,r-.2,.66,"#ad7d68","#967368","#f0ece0");
  }
  function windowFront(c,x,y,z,w,h,lit=true){
    frontRect(c,x-.04,y+.018,z-.03,w+.08,h+.08,"#ece1c8");
    frontRect(c,x,y+.027,z,w,h,lit?"#ceb88d":"#749298");
    frontRect(c,x+.025,y+.04,z+.03,w-.05,h*.49,lit?"#edce91":"#90a6a7");
    frontRect(c,x+w*.48,y+.046,z,.029,h,"#637773");frontRect(c,x,y+.052,z+h*.52,w,.025,"#737e75");
    frontRect(c,x-.07,y+.06,z-.045,w+.13,.05,"#f1ecd9");
  }
  function windowSide(c,x,y,z,w,h){
    sideRect(c,x+.016,y-.025,z-.03,w+.05,h+.06,"#bec7b9");
    sideRect(c,x+.026,y,z,w,h,"#738b8b");
    sideRect(c,x+.035,y+.03,z+.03,w-.06,h*.42,"#8da19b");
    sideRect(c,x+.046,y+w*.48,z,.035,h,"#627a7a");
  }
  function canopy(c,b,colA,colB){
    const n=Math.ceil(b.w/.29),y=b.y+b.d+.05,z=b.h*.69;
    for(let i=0;i<n;i++){
      const x=b.x+i*b.w/n,ww=b.w/n;
      poly(c,[P(x,y,z+.12),P(x+ww,y,z+.12),P(x+ww,y+.48,z-.04),P(x,y+.48,z-.04)],i%2?colA:colB);
      frontRect(c,x,y+.48,z-.15,ww,.11,i%2?colA:colB);
    }
  }
  function building(c,b){
    const {x,y,w,d,h}=b;let rng=random(Math.floor(x*1000+y*7));
    box(c,x-.06,y-.06,w+.12,d+.12,0,.10,"#9faca2","#96a59c","#c5c9bb");
    box(c,x,y,w,d,.09,h-.09,b.wall,b.side,"#d5d9cf");
    // Brick courses and siding are fixed to the facade, never painted over the windows.
    for(let z=.19;z<h-.08;z+=b.kind==="hotel"?.115:.19){
      line(c,[P(x+.03,y+d+.006,z),P(x+w-.03,y+d+.006,z)],"rgba(85,80,67,.13)",.72);
      if(b.kind==="hotel")for(let tx=.1+rng()*.42;tx<w;tx+=.45)line(c,[P(x+tx,y+d+.011,z),P(x+tx,y+d+.011,z+.10)],"rgba(77,73,67,.14)",.65);
    }
    frontRect(c,x+.02,y+d+.018,.08,w-.04,.105,color(b.wall,-18));
    if(b.kind==="tower"){
      for(let z=.45;z<h-.27;z+=.67){
        for(let i=.23;i<w-.33;i+=.48)windowFront(c,x+i,y+d,z,.24,.35,false);
        for(let i=.2;i<d-.33;i+=.52)windowSide(c,x+w,y+i,z,.25,.35);
      }
    }else{
      const floors=h>2.5?3:h>1.6?2:1,doorX=x+w*.69;
      for(let j=0;j<floors;j++){
        const z=.30+j*(h-.45)/floors,ww=w/(b.kind==="terminal"?9:6);
        const count=Math.max(2,Math.floor(w/(ww+.27)));
        for(let i=0;i<count;i++){
          const px=x+.20+i*(w-.23)/count;
          if(j===0 && px<doorX+.48&&px+ww>doorX-.12)continue;
          windowFront(c,px,y+d,z,ww*.70,Math.min(.49,(h*.54)/floors),i%3!==0);
        }
        for(let i=.30;i<d-.2;i+=.73)windowSide(c,x+w,y+i,z,.34,Math.min(.42,h*.23));
      }
      frontRect(c,doorX,y+d+.05,.10,.43,.86,"#596c66");frontRect(c,doorX+.06,y+d+.075,.48,.30,.37,"#d3b787");
      box(c,doorX-.12,y+d+.09,.69,.29,0,.12,"#aaa99a","#a3a799","#d5d4bf");
      if(b.label){
        const sz=b.kind==="terminal"?.47:.33,z=b.kind==="hotel"?1.01:h-.43;
        frontRect(c,x+.13,y+d+.072,z,w-.26,sz,"#384d48");
        frontRect(c,x+.17,y+d+.083,z+.031,w-.34,.026,"#c7b487");
        faceText(c,b.label,x+w/2,y+d+.095,z+sz*.55,(w-.43)*35,"#f4e6bc",b.kind==="terminal"?14:b.kind==="hotel"?11:10);
      }
      if(b.kind==="diner")canopy(c,b,"#d88c72","#e9dfc7");
      if(b.kind==="depot")canopy(c,b,"#768e7f","#a5ad8e");
    }
    if(["tower","terminal","depot","diner"].includes(b.kind)){
      box(c,x-.14,y-.14,w+.28,d+.28,h-.02,.135,"#637873","#657a74","#eaece0");
      box(c,x+.18,y+.17,w-.36,d-.34,h+.09,.09,"#b4c1b7","#a8b6b0","#d7dfd8");
      if(b.kind==="terminal"){box(c,x+w*.38,y+d*.30,1.2,.7,h+.13,.5,"#96a79f","#82968f","#eef0e6");}
      if(b.kind==="tower")box(c,x+w*.22,y+d*.25,w*.54,d*.4,h+.17,.38,"#889892","#738780","#d5dbd2");
      if(b.kind==="diner")box(c,x+w*.18,y+.35,.65,.4,h+.14,.18,"#a9b4ac","#91a099","#e7e8da");
    }else roof(c,b);
    if(b.kind==="radio"){
      const ax=x+w*.51,ay=y+d*.38;
      line(c,[P(ax,ay,h+.29),P(ax,ay,h+2.85)],"#667b7a",2.0);
      line(c,[P(ax-.43,ay,h+.47),P(ax,ay,h+2.46),P(ax+.47,ay,h+.47)],"#7d8d87",1.1);
      for(let i=0;i<3;i++)line(c,[P(ax-.3+i*.055,ay,h+1.64+i*.38),P(ax+.3-i*.055,ay,h+1.64+i*.38)],"#6a7c78",1.6);
      const light=P(ax,ay,h+2.91);oval(c,light.x,light.y,2.3,2.1,"#b57961");
    }
  }
  function evergreen(c,o){
    const a=P(o.x,o.y),s=o.s;oval(c,a.x+4*s,a.y+1*s,14*s,5*s,"rgba(89,115,111,.17)");
    c.fillStyle="#776e5d";c.fillRect(a.x-2*s,a.y-19*s,4*s,19*s);
    for(let i=0;i<3;i++){
      const y=a.y-(7+i*10)*s,rad=(15.3-i*3.0)*s,h=(26-i*3)*s;
      poly(c,[{x:a.x-rad,y},{x:a.x-3*s,y:y-h},{x:a.x+rad*.93,y:y+.7*s}],["#718a7b","#819789","#8b9e8f"][i]);
      poly(c,[{x:a.x-3*s,y:y-h},{x:a.x+rad*.93,y:y+.7*s},{x:a.x+rad*.12,y:y-3*s}],"#667f72");
      poly(c,[{x:a.x-rad*.71,y:y-h*.24},{x:a.x-3*s,y:y-h-1*s},{x:a.x+rad*.60,y:y-h*.32},
              {x:a.x+rad*.12,y:y-h*.35},{x:a.x-rad*.12,y:y-h*.26},{x:a.x-rad*.21,y:y-h*.33}],"#e5eade");
    }
  }
  function bare(c,o){
    const {x,y,s}=o,a=P(x,y);oval(c,a.x+5*s,a.y+1,11*s,4*s,"rgba(94,107,94,.17)");
    const draw=(x1,y1,x2,y2,w)=>line(c,[{x:a.x+x1*s,y:a.y+y1*s},{x:a.x+x2*s,y:a.y+y2*s}],"#79786a",w*s);
    draw(0,0,1,-30,3.4);draw(1,-15,-8,-28,2.2);draw(-8,-28,-13,-34,1);draw(-8,-28,-6,-36,1.1);
    draw(1,-22,12,-36,2);draw(12,-36,10,-40,1);draw(1,-27,-2,-42,1.6);draw(-2,-37,-8,-44,1);
  }
  function lamp(c,o){
    const a=P(o.x,o.y);oval(c,a.x+3,a.y+2,6,2.7,"rgba(69,81,72,.2)");
    box(c,o.x-.065,o.y-.065,.13,.13,0,.14,"#64756c","#55685e","#87948b");
    line(c,[a,P(o.x,o.y,.95)],"#53695e",2.2);const t=P(o.x,o.y,1.03);
    poly(c,[{x:t.x-3.8,y:t.y-2.3},{x:t.x+3.8,y:t.y-2.3},{x:t.x+2.3,y:t.y+5.1},{x:t.x-2.3,y:t.y+5.1}],"#f1d69c","#617469",.75);
    poly(c,[{x:t.x-5,y:t.y-2.2},{x:t.x,y:t.y-6},{x:t.x+5,y:t.y-2.2}],"#5a7064");
  }
  function bench(c,o){
    box(c,o.x,o.y,.76,.24,.14,.10,"#9f8061","#89765e","#b69d77");
    box(c,o.x,o.y+.02,.76,.045,.24,.19,"#a78b69","#88765e","#c2ae88");
    for(const dx of [.09,.62])box(c,o.x+dx,o.y+.10,.06,.08,0,.16,"#617468","#52685b","#70816f");
  }
  function gazebo(c){
    const x=11.35,y=11.95,w=1.77,d=1.55;
    box(c,x-.12,y-.12,w+.24,d+.24,0,.16,"#9e9f8e","#9fa69a","#d6d3ba");
    box(c,x,y,w,d,.15,.14,"#aeaa92","#9da791","#d4c7a6");
    for(const dx of [.06,w-.14])for(const dy of [.06,d-.14])box(c,x+dx,y+dy,.075,.075,.27,1.04,"#899b83","#718873","#d7d6bd");
    for(const dy of [.10,d-.09])box(c,x+.1,y+dy,w-.2,.035,.56,.065,"#81967e","#758c73","#c3c6aa");
    const a=P(x-.25,y-.25,1.32),b=P(x+w+.25,y-.25,1.32),e=P(x+w+.25,y+d+.25,1.32),f=P(x-.25,y+d+.25,1.32),t=P(x+w/2,y+d/2,2.0);
    poly(c,[a,b,t],"#a0afa0");poly(c,[b,e,t],"#8a9f8d");poly(c,[e,f,t],"#d8dfcc");poly(c,[f,a,t],"#b8c6b4");
    poly(c,[{x:t.x,y:t.y-2},W.mix(f,t,.6),W.mix(e,t,.66)],"#eff0e2");line(c,[e,f,a],"#728974",2);
    const top=P(x+w/2,y+d/2,2.35);line(c,[t,top],"#7c8a71",1.4);poly(c,[top,{x:top.x+12,y:top.y+2},{x:top.x,y:top.y+5}],"#ae6d53");
  }
  function sign(c,o){
    const {x,y}=o;box(c,x,y,.065,.065,0,.67,"#786f5c","#667969","#bdad90");
    const a=P(x,y,.67);c.save();c.translate(a.x,a.y);c.fillStyle="#294d50";c.fillRect(-11,-8,22,11);c.fillStyle="#efdfaf";c.font="bold 7px Arial";c.textAlign="center";c.fillText("BUS",0,0);c.restore();
  }
  function bunting(c){
    const a=P(10.64,11.5,1.32),b=P(14.85,11.5,1.32);line(c,[P(10.64,11.5),a],"#6e8073",1.8);line(c,[P(14.85,11.5),b],"#6e8073",1.8);
    const pts=[];for(let i=0;i<=16;i++){const t=i/16;pts.push({x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t+5*Math.sin(Math.PI*t)});}line(c,pts,"#8b8b76",1);
    for(let i=1;i<16;i+=2){const p=pts[i],q=pts[i+1];poly(c,[p,q,{x:(p.x+q.x)/2,y:(p.y+q.y)/2+6}],["#b97c62","#ddc17e","#839d88"][i%3]);}
  }
  const propLists={};
  for(const scene of ["town","city"]){
    const arr=[],rng=random(scene==="town"?44:91);
    const add=(type,x,y,extra={})=>arr.push({type,x,y,order:x+y,...extra});
    const bs=scene==="town"?W.buildings:W.cityBuildings;
    for(const b of bs)add("building",b.x+b.w,b.y+b.d,{b,order:b.x+b.y+b.w+b.d-.08});
    for(let i=0;i<(scene==="town"?152:55);i++){
      let x,y;
      if(i%3===0){x=-4+rng()*29;y=-5+rng()*3.6;}
      else if(i%3===1){x=-4.8+rng()*4;y=-3+rng()*26;}
      else{x=21.6+rng()*4;y=-4+rng()*29;}
      add(i%7===0?"bare":"pine",x,y,{s:.72+rng()*.71});
    }
    const trees=scene==="town"?[[1.1,7.1],[2.1,15.9],[5.0,1.4],[11,3.3],[15.7,3.55],[18.9,6.9],[15.5,14.65],[10.65,14.9],[5.0,18.8],[1.1,18.9],[19.8,15.55],[12.4,3.25],[2.8,3.35]]:[[3.6,6.7],[3.45,8.7],[13.2,9.9],[15.8,13.9],[12.4,15.5],[7.4,15.3]];
    for(const [i,p] of trees.entries())add(i%3?"bare":"pine",p[0],p[1],{s:1.02+rng()*.30});
    const lamps=scene==="town"?[[3.0,8.98],[7.6,8.99],[10.7,8.99],[15.65,8.99],[10.7,14.9],[15.3,15.43],[4.1,15.44],[18.95,14.1],[8.2,5.05]]:[[6.2,10.7],[9.65,10.7],[12.95,10.7],[17.85,13.45],[3.55,14.25]];
    for(const p of lamps)add("lamp",...p);
    for(const p of scene==="town"?[[13.1,14.55],[10.92,13.3],[16.32,13.19],[4.21,8.3]]:[[6.8,10.12],[8.45,10.1],[11.7,10.12]])add("bench",...p);
    if(scene==="town"){add("gazebo",13.12,13.48);add("bunting",13.1,11.58);add("sign",17.88,13.48);}else add("sign",10.85,11.35);
    propLists[scene]=arr.sort((a,b)=>a.order-b.order);
  }
  function prop(c,o){
    switch(o.type){case "building":building(c,o.b);break;case "pine":evergreen(c,o);break;case "bare":bare(c,o);break;case "lamp":lamp(c,o);break;case "bench":bench(c,o);break;case "gazebo":gazebo(c);break;case "bunting":bunting(c);break;case "sign":sign(c,o);break;}
  }
  const propSprites=new Map();
  function sprite(o){
    if(propSprites.has(o))return propSprites.get(o);
    const b=o.b, hw=b?Math.ceil((b.w+b.d)*23+34):o.type==="bunting"?100:o.type==="gazebo"?105:34;
    const height=b?Math.ceil((b.w+b.d)*22+(b.h+3.2)*34+24):o.type==="gazebo"?155:o.type==="bunting"?145:90;
    const img=document.createElement("canvas"),scale=1.65;img.width=Math.ceil(hw*2*scale);img.height=Math.ceil(height*scale);
    const a=P(o.x,o.y),x=o.type==="bunting"?a.x-hw:b?(P(b.x,b.y).x+P(b.x+b.w,b.y+b.d).x)/2-hw:a.x-hw;
    const y=a.y-height+12;
    const ctx=img.getContext("2d");ctx.scale(scale,scale);ctx.translate(-x,-y);prop(ctx,o);
    const data={img,x,y,w:img.width/scale,h:img.height/scale};propSprites.set(o,data);return data;
  }
  function person(c,actor,t,palette){
    const {skin:who,pos,moving,main:active,role,action=""}=actor;
    const a=P(pos.x,pos.y);const walk=moving?Math.sin(t*13):0, gait=walk*2.8;
    c.save();c.translate(a.x,a.y);oval(c,1,1,7.8,3.7,"rgba(68,80,76,.28)");
    if(active){c.beginPath();c.ellipse(0,.5,10.3,4.7,0,0,Math.PI*2);c.strokeStyle="#f0b85f";c.lineWidth=1.65;c.stroke();}
    const back=(pos.dx||0)+(pos.dy||0)<-.02,faceRight=(pos.dx||0)-(pos.dy||0)>=0;
    c.scale(faceRight?1:-1,1);c.translate(0,-Math.abs(walk)*.7);
    c.fillStyle="#3d4e51";c.fillRect(-4+gait,-8,3.35,7.1);c.fillRect(.9-gait,-8,3.2,7.0);
    c.fillStyle="#403e35";c.fillRect(-4.3+gait,-2.6,4.5,2.6);c.fillRect(.45-gait,-2.55,4.7,2.55);
    const coat=palette.coat,trim=palette.trim;
    poly(c,[{x:-4.0,y:-19},{x:3.7,y:-19.1},{x:5.2,y:-8},{x:3.7,y:-6.4},{x:-5.4,y:-6.8}],coat);
    poly(c,[{x:-4.0,y:-17.7},{x:-1.15,y:-18.6},{x:-1.1,y:-7.2},{x:-5.1,y:-7}],palette.shade);
    line(c,[{x:-4.15,y:-17},{x:-5.8+gait*.27,y:-11.0},{x:-5+gait*.34,y:-9.05}],palette.shade,2.7);
    line(c,[{x:3.45,y:-17.2},{x:5.5-gait*.26,y:-11.35}],coat,2.7);
    c.fillStyle=palette.skin;c.fillRect(4.45-gait*.26,-12,2.35,3.05);
    if(!back){line(c,[{x:.8,y:-16},{x:1.6,y:-7.8}],"rgba(235,218,172,.5)",.65);c.fillStyle=trim;c.fillRect(.75,-15,2,5);}
    c.fillStyle=trim;c.fillRect(-3.8,-19.5,7.8,2.8);
    poly(c,[{x:-3.4,y:-25.1},{x:3.25,y:-25.0},{x:4.2,y:-22.0},{x:3.2,y:-19.4},{x:-1.7,y:-19.25},{x:-3.7,y:-21.4}],back?palette.hair:palette.skin);
    c.fillStyle=palette.hair;c.fillRect(-3.65,-24.6,2.4,4.2);
    if(!back){c.fillStyle="#544d43";c.fillRect(2.8,-22.8,.95,1.0);}
    c.fillStyle=palette.hat;c.fillRect(-3.7,-27.4,6.5,3);c.fillRect(-4.5,-25.55,8.8,2.45);
    if(who==="Lou"){c.fillStyle=trim;c.fillRect(-5,-24.6,10,1.5);}else if(who==="Bea"){oval(c,-.6,-27.7,2.1,2.1,trim);}else{c.fillStyle=trim;c.fillRect(-3.9,-25.1,7.9,1.25);}
    if(role==="camera"){
      const cy=/film_|shoot_|record_band/.test(action)?-22:-13;
      c.fillStyle="#354e50";c.fillRect(2,cy,8.1,4.5);c.fillRect(8.7,cy+.6,3.8,3.2);
      if(cy===-22){c.fillStyle="#fdc491";c.fillRect(7,cy+1,.95,.95);}
    }else if(role==="producer"){
      c.fillStyle="#7e6c51";c.fillRect(-6.1,-16.0,4.4,5.8);c.fillStyle="#dfd8b5";c.fillRect(-5.6,-15.5,3.4,4.3);
    }else if(role==="reporter"&&/talk_to_|forecast|report/.test(action)){
      line(c,[{x:5.1,y:-12},{x:8.2,y:-17.2}],"#465e5c",1.4);oval(c,8.4,-17.7,1.65,1.85,"#394f52");
    }
    c.restore();
  }
  const palettes={
    Phil:{coat:"#a95743",shade:"#874c42",trim:"#f1c16d",hat:"#444f52",hair:"#564a3d",skin:"#c99977"},
    Lou:{coat:"#6b8096",shade:"#536579",trim:"#cfb69a",hat:"#63576d",hair:"#53483e",skin:"#aa785a"},
    Bea:{coat:"#718b65",shade:"#557460",trim:"#e4b979",hat:"#9e7a5d",hair:"#614a3b",skin:"#d3a480"}
  };
  function coach(c,pos){
    const {x,y}=pos,wide=2.35,deep=.91;
    // axles on the visible long face
    const l=x-wide/2,v=y-deep/2;
    for(const i of [.46,1.9]){const p=P(l+i,v+deep,.12);oval(c,p.x,p.y,4.3,5.8,"#45504b");oval(c,p.x,p.y,2.1,3.0,"#a8aea0");}
    box(c,l,v,wide,deep,.17,.73,"#c9a16e","#a58059","#d9c7a3");
    frontRect(c,l+.05,v+deep+.015,.37,wide-.1,.125,"#396666");
    for(let i=0;i<5;i++)frontRect(c,l+.09+i*.43,v+deep+.021,.56,.34,.265,"#547272");
    sideRect(c,l+wide+.02,v+.09,.54,deep-.18,.27,"#78908a");
    frontRect(c,l+wide-.32,v+deep+.032,.21,.26,.58,"#6f7767");frontRect(c,l+wide-.29,v+deep+.039,.55,.19,.20,"#adc0a9");
    box(c,l+.06,v+.04,wide-.12,deep-.08,.9,.07,"#b9b8a0","#9caa99","#e9e6d5");
    faceText(c,"INTERCITY",l+wide*.42,v+deep+.052,.30,42,"#f2e4c3",5.6);
  }
  const lands={};
  function draw(canvas,world,view){
    const {width,height,dpr}=view,c=canvas.getContext("2d");if(!width||!height)return;
    const scene=world.scene,cent=P(view.focus.x,view.focus.y),z=view.zoom;
    const ox=width*.5-cent.x*z,oy=height*(view.overview?.50:.56)-cent.y*z+(view.overview?4:0);
    c.setTransform(dpr,0,0,dpr,0,0);c.fillStyle="#dce2d9";c.fillRect(0,0,width,height);
    c.translate(ox,oy);c.scale(z,z);
    if(!lands[scene])lands[scene]=ground(scene==="town"?130:839,scene);
    const land=lands[scene];c.drawImage(land.img,-land.ox,-land.oy);
    // Cast soft shadows onto the ground, before people or architecture.
    const bs=scene==="town"?W.buildings:W.cityBuildings;
    for(const b of bs){
      const sh=.56+b.h*.18;poly(c,[P(b.x,b.y+b.d),P(b.x+b.w,b.y+b.d),P(b.x+b.w+sh,b.y+b.d-.20),P(b.x+b.w+sh,b.y-.17),P(b.x+b.w,b.y)],"rgba(74,99,99,.16)");
    }
    if(world.path?.length>1){
      const pts=world.path.map(p=>P(p.x,p.y));c.save();c.setLineDash([2,5]);line(c,pts,"rgba(124,91,48,.72)",2.1/z);c.restore();
      const e=pts.at(-1);oval(c,e.x,e.y,5.5,2.9,"#eecc88");
    }
    const actors=world.people.filter(p=>p.scene===scene && p.visible!==false);
    const sorted=propLists[scene].slice();
    for(const p of actors)sorted.push({type:"person",order:p.pos.x+p.pos.y+.045,p});
    if(world.bus&&world.bus.scene===scene)sorted.push({type:"bus",order:world.bus.pos.x+world.bus.pos.y+1.17,p:world.bus});
    sorted.sort((a,b)=>a.order-b.order);
    const left=-ox/z,right=(width-ox)/z,top=-oy/z,bottom=(height-oy)/z;
    const hero=actors.find(p=>p.main),heroPx=hero?P(hero.pos.x,hero.pos.y):null;
    for(const o of sorted){
      if(o.type==="person"){person(c,o.p,world.t,palettes[o.p.skin||o.p.name]||palettes.Lou);continue;}
      if(o.type==="bus"){coach(c,o.p.pos);continue;}
      const at=P(o.x,o.y);if(at.x<left-430||at.x>right+430||at.y<top-40||at.y>bottom+360)continue;
      const s=sprite(o);
      if(s.x>right||s.x+s.w<left||s.y>bottom||s.y+s.h<top)continue;
      const fade=o.type==="building"&&heroPx&&o.order>hero.pos.x+hero.pos.y&&heroPx.x>s.x+10&&heroPx.x<s.x+s.w-10&&heroPx.y-10>s.y+35&&heroPx.y-10<s.y+s.h-15;
      if(fade)c.globalAlpha=.55;c.drawImage(s.img,s.x,s.y,s.w,s.h);c.globalAlpha=1;
    }
    // Environmental time is visual only. No simulation events are generated here.
    c.setTransform(dpr,0,0,dpr,0,0);
    const night=world.slot===3,morning=world.slot===0;
    c.fillStyle=night?"rgba(34,54,90,.24)":morning?"rgba(248,217,154,.075)":"rgba(236,242,228,.015)";c.fillRect(0,0,width,height);
    if(night){for(const o of propLists[scene].filter(p=>p.type==="lamp")){const a=P(o.x,o.y,1.0),x=ox+a.x*z,y=oy+a.y*z,rad=13*z;
      const gl=c.createRadialGradient(x,y,0,x,y,rad);gl.addColorStop(0,"rgba(255,224,151,.83)");gl.addColorStop(1,"rgba(255,223,154,0)");c.fillStyle=gl;c.fillRect(x-rad,y-rad,rad*2,rad*2);}}
    for(let i=0;i<Math.min(70,width/10);i++){const x=((i*79.9+world.t*(1.9+i%4)*.9)% (width+3)+width+3)%(width+3),y=((i*127.3+world.t*(4+i%5))%(height+3)+height+3)%(height+3);c.fillStyle=i%3===0?"rgba(255,255,247,.87)":"rgba(255,255,247,.53)";c.fillRect(x,y,i%3===0?1.8:1.2,i%3===0?1.8:1.2);}
    const labels=[];
    for(const p of actors){
      const a=P(p.pos.x,p.pos.y);labels.push({name:p.name,main:p.main,x:ox+a.x*z,y:oy+(a.y-34)*z});
    }
    for(const tag of labels.sort((a,b)=>Number(a.main)-Number(b.main))){
      let {x,y}=tag;if(x<22||y<22||x>width-22||y>height-20)continue;
      const txt=tag.name.toUpperCase();c.font="bold 9px ui-monospace, Menlo, monospace";const tw=c.measureText(txt).width+13;
      // Move nearby labels apart in screen space so a conversation remains legible.
      const prior=labels.find(a=>a!==tag&&a.y>=y-6&&a.y<=y+6&&Math.abs(a.x-x)<33&&!a.main);
      if(tag.main&&prior)y-=16;
      c.fillStyle=tag.main?"#f4cf89":"rgba(38,62,60,.83)";c.fillRect(x-tw/2,y-12,tw,14);
      c.fillStyle=tag.main?"#3c352a":"#f0eee0";c.textAlign="center";c.textBaseline="middle";c.fillText(txt,x,y-4.3);
    }
    const fog=c.createLinearGradient(0,0,0,height);fog.addColorStop(0,"rgba(226,232,222,.28)");fog.addColorStop(.16,"rgba(226,232,222,0)");fog.addColorStop(.86,"rgba(226,232,222,0)");fog.addColorStop(1,"rgba(82,100,84,.09)");c.fillStyle=fog;c.fillRect(0,0,width,height);
    return {ox,oy,z,sceneNames};
  }
  function contains(point,polygon){
    let inside=false;
    for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
      const a=polygon[i],b=polygon[j];
      if((a.y>point.y)!==(b.y>point.y)&&point.x<(b.x-a.x)*(point.y-a.y)/(b.y-a.y)+a.x)inside=!inside;
    }
    return inside;
  }
  function landmarkAt(point,scene){
    // Pick against visible facades and roofs; a screen tap on the hotel roof
    // should route to the lobby entrance instead of unprojecting behind it.
    const structures=propLists[scene].filter(x=>x.type==="building"||x.type==="gazebo").sort((a,b)=>b.order-a.order);
    for(const obj of structures){
      const b=obj.b||{id:"square",x:11.4,y:11.95,w:1.6,d:1.5,h:1.2};
      const x=b.x,y=b.y,X=x+b.w,Y=y+b.d,roof=b.h+.15;
      const polygon=[P(x,y,roof),P(X,y,roof),P(X,y),P(X,Y),P(x,Y),P(x,Y,roof)];
      if(contains(point,polygon))return b.id || (b.kind==="terminal"?"Pittsburgh":null);
    }
    return null;
  }
  return {draw,sceneNames,landmarkAt};
})();
