"""Build a file-openable booth evidence viewer from verified takes; no model or network is used."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>The eight-second fader</title>
<style>
:root{color-scheme:dark;font-family:"IBM Plex Mono",ui-monospace,monospace;background:#141914;color:#dce2d2}*{box-sizing:border-box}
body{max-width:990px;margin:auto;padding:clamp(14px,4vw,42px)}h1{font:normal clamp(34px,6vw,66px)/1.05 Georgia,serif;margin:16px 0 24px}h2{font:normal 24px Georgia,serif;margin:0 0 14px}
.controls,.tabs,.title{display:flex;flex-wrap:wrap;gap:8px;align-items:center}button,select{font:inherit;color:#dce2d2;border:1px solid #576052;background:#202820;padding:8px 12px;border-radius:3px;cursor:pointer}
button[aria-pressed=true]{background:#dce2d2;color:#172019;border-color:#dce2d2}button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #ffcc68;outline-offset:3px}
.panel{padding:clamp(15px,3vw,28px);border:1px solid #4a564b;border-radius:7px;background:#1b241d;margin-top:14px}.meter{display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center}
.clock{font:bold clamp(52px,10vw,93px)/1 ui-monospace,monospace;font-variant-numeric:tabular-nums;letter-spacing:-.08em;color:#ff8666;background:#301f1b;padding:10px 17px;border:1px solid #654a3a}.title{justify-content:space-between}.dim,small{color:#bcc6b5}.phase{font-weight:bold}p{line-height:1.55;margin:10px 0}.evidence{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.55;max-height:420px;overflow-y:auto;border-left:2px solid #758779;padding-left:14px}
.bars{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}.bars span{background:#253029;padding:7px 10px}.links a{color:#bbd8e9;margin-right:16px}.links{margin-top:16px}.controls{margin:14px 0}.receipt{display:block}.tabs{margin-top:14px}
@media(max-width:520px){.meter{grid-template-columns:1fr}.controls label{display:grid;gap:3px}.panel{padding:14px}.clock{width:max-content}}
</style></head><body>
<h1>The eight-second fader</h1>
<p>Phil returns a missing cassette. A scenery flat determines whether Rita can see who put it back. Follow an audited take to the morning the station clock repeats. The 1,000-token primary runs ended at their first incomplete response. This viewer uses completed higher-cap continuations with every earlier decision preserved.</p>
<div class="controls"><label>Root <select id="seed"><option>1801</option><option>1802</option></select></label>
<label>Acoustic window <select id="arm"><option value="open">Clear</option><option value="covered">Screened</option></select></label></div>
<nav class="tabs" id="phases" aria-label="Scene moment"></nav>
<section class="panel meter"><div class="clock" id="clock"></div><div><div class="phase" id="phase"></div><h2 id="choice"></h2><span class="dim" id="time"></span></div></section>
<section class="panel"><div class="title"><h2>What each person knew</h2><div class="tabs" id="people" aria-label="Observer"></div></div><p class="evidence" id="view"></p></section>
<section class="panel"><h2>Stage record and witnesses</h2><p id="receipts"></p><div class="bars" id="meters"></div><div class="links"><a id="raw">Exact model response</a><a id="request">Exact actor input</a><a id="take">Source take</a></div></section>
<script id="data" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent), el=id=>document.getElementById(id);
let pos=0, person='Rita';
const names=['Returned tin','Speaker test','Next morning','Producer’s cut'];
function buttons(id,options,active,select){const container=el(id);container.replaceChildren();options.forEach((name,i)=>{let b=document.createElement('button');b.textContent=name;b.setAttribute('aria-pressed',String(i===active));b.onclick=()=>select(i);container.append(b)})}
function render(){let t=data.takes.find(t=>String(t.root)===el('seed').value&&t.sightline===el('arm').value),s=t.steps[pos];buttons('phases',names,pos,i=>{pos=i;person=t.steps[pos].actor;render()});let cast=['Rita','Phil','Larry'];buttons('people',cast,cast.indexOf(person),i=>{person=cast[i];render()});
el('clock').textContent=String(s.clock).padStart(2,'0')+'s';el('phase').textContent='Morning '+s.day+' · '+s.actor+' chose';el('choice').textContent=s.menu[s.chosen];
el('time').textContent=s.clock===0?'The live tally is on.':'Time before the wire weather handoff';el('view').textContent=s.observers[person].text;
let consequence=t.events.filter(e=>s.consequence_event_ids.includes(e.id));el('receipts').replaceChildren();
for(let e of consequence){let span=document.createElement('span');span.className='receipt';span.textContent=e.audience.join(' + ')+' · '+e.text;el('receipts').append(span)}
let counters=el('meters');counters.replaceChildren();if(pos===3){for(let txt of [t.meter.heard_without_current_consent_s+'s aired without permission',t.meter.heard_with_current_consent_s+'s authorized audio','Later booth access · '+t.later_board_access]){let b=document.createElement('span');b.textContent=txt;counters.append(b)}}
el('raw').href=s.response;el('request').href=s.input;el('take').href=t.source}
el('seed').onchange=render;el('arm').onchange=render;render();
</script></body></html>'''
if __name__ == "__main__":
    data = json.loads((HERE/"measured.json").read_bytes())
    if len(data["takes"]) != 4:
        raise ValueError("The paired viewer requires four audited complete takes.")
    # Escape script delimiters even when an actor quotes markup in a private note.
    packed = json.dumps(data, ensure_ascii=False, separators=(",",":")).replace("<","\\u003c")
    (HERE/"exhibit.html").write_text(PAGE.replace("__DATA__",packed))
