"use strict";
(() => {
  const data=window.CoachFork, $=id=>document.getElementById(id);
  if(!data){$("screens").textContent="The recording for this branch is unavailable.";return;}
  if(data.identical){
    $("screens").textContent="Phil chose the coach in all "+data.candidate_count+" new draws from this checkpoint.";
    document.querySelector(".transport").hidden=true;
    $("method").textContent="Each draw had the original messages, legal actions and other actors’ choices. Only Phil’s decoding seed changed.";
    return;
  }
  const count=data.end-data.start, moments=["1:00 pm · The ticket","7:00 pm · That evening","6:00 am · The alarm","9:30 am · Afterward"];
  const tracks=[data.original,data.alternate].map(WinterReplay.normalize);
  const panels=[], buttons=[];
  let cursor=0, playing=false, lastTime=0, lastPaint=0;
  function element(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt)n.textContent=txt;return n;}
  for(const [i,tr] of tracks.entries()){
    const card=element("article"), title=element("h2","",i===0?"Original take":"Alternate draw");
    const scene=element("div","scene"),canvas=element("canvas"),alarm=element("span","alarm"),fade=element("div","fade");
    canvas.setAttribute("aria-label",title.textContent+" town scene");
    scene.append(canvas,fade,alarm);
    const speech=element("div","speech"),where=element("div","where"),words=element("blockquote"),effect=element("p","effect");
    speech.append(where,words,effect);card.append(title,scene,speech);$("screens").append(card);
    panels.push({tr,canvas,alarm,fade,where,words,effect});
  }
  function draw(){
    const step=Math.min(count-1,Math.floor(cursor)),progress=cursor>=count?1:cursor-step;
    for(const panel of panels){
      const w=WinterReplay.at(panel.tr,data.start+step,progress),e=w.shown;
      const r=panel.canvas.getBoundingClientRect(), dpr=Math.min(2,window.devicePixelRatio||1), ww=Math.round(r.width*dpr),hh=Math.round(r.height*dpr);
      if(panel.canvas.width!==ww||panel.canvas.height!==hh){panel.canvas.width=ww;panel.canvas.height=hh;}
      w.cameraSubject=w.people[0];
      const props={width:r.width,height:r.height,dpr,focus:w.hero,zoom:Math.max(.63,Math.min(1.2,r.width/550)),overview:false};
      // A stationary activity can be framed at its physical set. Keep the bus crossing in the exterior map.
      const interior=w.shown.origin===w.shown.place && w.actionProgress>.19 && !!window.WinterInterior;
      if(interior){WinterInterior.draw(panel.canvas,w,e.place,props);}
      else{WinterArt.draw(panel.canvas,w,props);}
      panel.fade.style.opacity=String(w.transition||0);
      panel.alarm.textContent=w.banner;
      panel.where.textContent=WinterMap.places[w.place].label;
      panel.words.textContent=e.words?"“"+e.words+"”":"Phil stays silent.";
      panel.effect.textContent=progress>.72?e.effect:"";
    }
    for(const [i,b] of buttons.entries())b.setAttribute("aria-pressed",String(i===step));
    $("scrub").value=String(cursor);
    $("clock").textContent="Day "+tracks[0].events[data.start+step].day+" · "+tracks[0].events[data.start+step].clock;
    $("play").textContent=playing?"Pause both":cursor>=count?"Replay both":"Play both";
  }
  function setCursor(v){cursor=Math.max(0,Math.min(v,count));playing=false;draw();}
  for(let i=0;i<count;i++){
    const b=element("button","",moments[i]);b.type="button";b.onclick=()=>setCursor(i+.015);buttons.push(b);$("steps").append(b);
  }
  $("scrub").max=String(count);$("scrub").oninput=e=>setCursor(Number(e.target.value));
  $("play").onclick=()=>{if(cursor>=count)cursor=0;playing=!playing;lastTime=performance.now();draw();if(playing)requestAnimationFrame(frame);};
  function frame(now){
    if(!playing)return;
    if(now-lastPaint>40){
      cursor=Math.min(count,cursor+Math.min(.1,(now-lastTime)/1000)/6);
      lastTime=now;lastPaint=now;if(cursor===count)playing=false;
      draw();
    }
    if(playing)requestAnimationFrame(frame);
  }
  $("method").textContent="We sampled Phil’s original one o’clock decision "+data.candidate_count+" more times. This is the first draw in our declared order where he chose a different act. Rita and Larry’s choices at that instant are identical. Afterward each person acts again from what they personally witnessed. The underlying source event is "+data.source_event+".";
  new ResizeObserver(draw).observe($("screens"));
  draw();
})();
