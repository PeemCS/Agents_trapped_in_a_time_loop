// Read the same route sampler as the browser. Emit a scene graph and motion for a DCC to consume.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const inputs = process.argv.slice(2);
const tracePath = inputs[0], begin = Number(inputs[1]), end = Number(inputs[2]);
const window = {};
const context = vm.createContext({window});
for (const [file,globalName] of [["world.js","WinterMap"],["replay.js","WinterReplay"]]) {
  vm.runInContext(fs.readFileSync(path.join(__dirname,"../visual",file),"utf8"),context);
  context[globalName] = window[globalName];
}
const W = window.WinterMap, R = window.WinterReplay;
const trace = R.normalize(JSON.parse(fs.readFileSync(tracePath)));
if (!(begin >= 0 && begin < end && end <= trace.events.length)) throw Error("Invalid slot range");
const fps = 24, framesPerSlot = 96, samples = [];
const setOffset = s => s === "city" ? 42 : 0;
for (let index=begin; index<end; index++) {
  for(let frame=0; frame<framesPerSlot; frame++) {
    const w = R.at(trace,index,frame/(framesPerSlot-1));
    samples.push({frame:(index-begin)*framesPerSlot+frame,slot:index,day:w.day,clock:w.clock,scene:w.scene,
      actors:w.people.map(p => ({name:p.name,role:p.role,x:p.pos.x+setOffset(p.scene),z:p.pos.y,
        visible:p.visible!==false,moving:p.moving,scene:p.scene})),
      bus:w.bus?{x:w.bus.pos.x+setOffset(w.bus.scene),z:w.bus.pos.y,scene:w.bus.scene}:null});
  }
}
const shots = trace.events.slice(begin,end).map(e=>({id:e.id,day:e.day,clock:e.clock,actor:e.actor,
  action:e.action,origin:e.origin,place:e.place,cast:e.cast.map(x=>({actor:x.actor,id:x.id,action:x.action,origin:x.origin,place:x.place}))}));
process.stdout.write(JSON.stringify({fps,framesPerSlot,shots,samples,places:W.places,
  buildings:{town:W.buildings,city:W.cityBuildings},roads:W.roads,setOffsets:{town:0,city:42}}));
