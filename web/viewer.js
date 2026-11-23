import { FilmRenderer } from "./renderer.js";
import { CastSpeech, FilmSound } from "./sound.js";

const byId = id => document.getElementById(id);
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text != null) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const clockText = ms => {
  const seconds = Math.floor(ms / 1000);
  return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
};
const readable = value => typeof value === "string" ? value.replaceAll("_", " ") : String(value);
const eventKind = event => readable(event.type || "event");
const eventText = event => event.text || event.line || event.outcome_text || event.utterance || event.description || "";
const actorFor = event => event.actor || event.agent || event.speaker;
const peopleColor = { phil: "#dca269", rita: "#ed8c8d", larry: "#83c8e8", ned: "#efce79" };
const changeTypes = new Set(["divergence", "npc_mode", "replay_match", "relationship", "gossip", "failure"]);
const evidenceTypes = new Set(["memory", "prediction", "test_result", "pencil", "experiment_result"]);
const visualOrder = ["puddle", "test_result", "performance", "kindness", "reply", "exit", "anchor", "utterance", "recognition", "position"];

function modeLabel(source) {
  if (source.mode === "fixture") return "Fixture film";
  if (source.mode === "local_policy") return source.complete ? "Local policy agents" : "Partial local run";
  if (source.mode === "muse_canary") return "Muse canary · fixture Phil";
  if (source.mode === "live" || source.mode === "live-canary") return source.complete ? "Live run" : "Partial live run";
  return "Replay";
}

function findShot(shots, time) {
  let low = 0, high = shots.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (shots[middle].start_ms <= time) low = middle + 1;
    else high = middle;
  }
  return Math.max(0, low - 1);
}

function setText(id, value) {
  const field = byId(id);
  if (field.textContent !== value) field.textContent = value;
}

function option(value, label) {
  const item = node("option", label);
  item.value = value;
  return item;
}

function drawTown(canvas, locations, stage, roads) {
  const zones = Object.entries(locations).filter(([, site]) => Number.isFinite(site?.x) && Number.isFinite(site?.z));
  canvas.width = 700;
  canvas.height = 288;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#13232b";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (zones.length === 0) return;
  const xs = zones.map(([, site]) => site.x);
  const zs = zones.map(([, site]) => site.z);
  const minX = Math.min(...xs), minZ = Math.min(...zs);
  const rangeX = Math.max(1, Math.max(...xs) - minX), rangeZ = Math.max(1, Math.max(...zs) - minZ);
  const coords = Object.fromEntries(zones.map(([key, site]) => [
    key, [72 + (site.x - minX) / rangeX * 552, 47 + (site.z - minZ) / rangeZ * 181],
  ]));
  ctx.lineWidth = 12;
  ctx.lineCap = "round";
  for (const [a, b] of roads) {
    if (!coords[a] || !coords[b]) continue;
    ctx.beginPath();
    ctx.moveTo(...coords[a]);
    ctx.lineTo(...coords[b]);
    ctx.strokeStyle = "#30434a";
    ctx.stroke();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#697c80";
    ctx.stroke();
    ctx.lineWidth = 12;
  }
  for (const [key, site] of zones) {
    const [x, y] = coords[key];
    const occupants = Object.entries(stage.positions).filter(([, place]) => place === key);
    ctx.beginPath();
    ctx.arc(x, y, key === stage.location ? 13 : 9, 0, Math.PI * 2);
    ctx.fillStyle = key === stage.location ? "#d9a06e" : "#789099";
    ctx.fill();
    ctx.font = "600 15px system-ui sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#e6e4d9";
    ctx.fillText(site.label || key, x, y - 19);
    const begin = x - (occupants.length - 1) * 7;
    occupants.forEach(([actor], index) => {
      const bx = begin + index * 14;
      ctx.beginPath();
      ctx.arc(bx, y + 20, 6, 0, Math.PI * 2);
      ctx.fillStyle = peopleColor[actor] || "#d8e4e3";
      ctx.fill();
    });
  }
  const marks = Object.entries(peopleColor);
  marks.forEach(([actor, color], index) => {
    const x = 34 + index * 95;
    ctx.fillStyle = color;
    ctx.fillRect(x, 265, 9, 9);
    ctx.font = "600 13px system-ui sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(actor[0].toUpperCase() + actor.slice(1), x + 15, 274);
  });
}

const linkFields = {
  prediction: "Earlier prediction", action_evidence: "Earlier action", observation: "Observation",
  source_event: "Source event", current_event: "Current event", trigger: "Trigger", recalled: "Memory used",
  stated_support: "Character cites", evidence: "Evidence", source: "Source", witness_events: "Witness record",
  decision_id: "Decision", current_evidence: "World evidence", action_event_id: "Earlier action",
  observation_event_id: "Observation", prediction_id: "Earlier prediction",
  replay_source_event: "Replayed decision",
};

function history(bundle) {
  const { run, stages, roads = [], label = "Main run" } = bundle;
  const events = run.events;
  const loops = Array.from(new Set(events.map(event => event.loop ?? 1))).sort((a, b) => a - b);
  const byLoop = new Map(loops.map(loop => [loop, []]));
  events.forEach((event, index) => byLoop.get(event.loop ?? 1).push(index));
  const eventKeys = new Map(events.map((event, index) => [event.id ?? "event-" + index, index]));
  return { label, stages, roads, events, loops, byLoop, eventKeys, locations: run.locations || {}, cast: run.cast || {} };
}

class ReplayViewer {
  constructor(bundle) {
    this.film = bundle.film;
    this.primary = history(bundle);
    this.reference = bundle.comparison ? history(bundle.comparison) : null;
    this.sources = new Map([["primary", this.primary]]);
    if (this.reference) this.sources.set("reference", this.reference);
    this.audit = this.primary;
    this.initialTick = bundle.compare_tick || 0;
    this.shots = this.film.shots;
    this.mode = modeLabel(this.film.source);
    this.canvas = byId("stage");
    this.renderer = new FilmRenderer(this.canvas, bundle.art);
    this.comparisonScreen = [0, 1].map(() => {
      const canvas = node("canvas", null, "compare-stage");
      canvas.width = 640;
      canvas.height = 360;
      return { canvas, renderer: new FilmRenderer(canvas, bundle.art) };
    });
    this.audio = new FilmSound();
    this.speech = new CastSpeech(available => { byId("voices").hidden = !available; });
    this.view = "film";
    this.playing = false;
    this.current = 0;
    this.shotIndex = -1;
    this.soundShot = -1;
    this.voiceShot = -1;
    this.speed = 1;
    this.ledgerIndex = 0;
    this.startClock = 0;
    this.recorder = null;
    this.bind();
  }

  get events() { return this.audit.events; }

  bind() {
    const { ending, complete } = this.film.source;
    const description = complete ? "One town. Every February 2." : "A replay of the decisions recorded so far.";
    setText("cover-caption", description);
    setText("run-mode", this.mode);
    document.body.dataset.mode = this.film.source.mode;
    const loops = this.primary.loops.length;
    const endingText = ending === "day_two" ? "February 3" : ending === "repeat" ? "Loop repeats" :
      (complete && ending && ending !== "unknown") ? readable(ending) : "Partial ending";
    setText("film-metadata", [this.shots.length + " shots", loops + (loops === 1 ? " loop" : " loops"), endingText].join(" · "));
    byId("timeline").max = this.film.duration_ms;
    byId("watch").disabled = false;
    byId("fullscreen").hidden = typeof byId("scene").requestFullscreen !== "function";
    byId("capture").hidden = typeof globalThis.MediaRecorder !== "function" ||
      typeof this.canvas.captureStream !== "function";
    byId("filter-source-label").hidden = !this.reference;
    let maxTick = 0;
    for (const [key, source] of this.sources) {
      byId("filter-source").append(option(key, source.label));
      for (const id of ["compare-a", "compare-b"]) {
        for (const loop of source.loops) {
          const prefix = this.reference ? source.label + " · " : "";
          byId(id).append(option(key + ":" + loop, prefix + "Loop " + loop));
        }
      }
      for (const event of source.events) maxTick = Math.max(maxTick, event.tick || 0);
    }
    byId("compare-a").value = "primary:" + (this.reference ? this.primary.loops.at(-1) : this.primary.loops[0]);
    byId("compare-b").value = this.reference ? "reference:" + this.reference.loops.at(-1) : "primary:" + this.primary.loops.at(-1);
    byId("compare-tick").max = maxTick;
    byId("compare-tick").value = Math.min(maxTick, Math.max(0, this.initialTick));
    this.selectSource("primary");
    byId("filter-source").addEventListener("change", event => {
      this.selectSource(event.currentTarget.value);
      this.ledgerIndex = 0;
      this.populateEvents();
    });
    for (const view of ["film", "ledger", "compare"]) {
      byId(view + "-view").addEventListener("click", () => this.show(view));
    }
    for (const id of ["filter-loop", "filter-actor", "filter-kind"]) {
      byId(id).addEventListener("change", () => this.populateEvents());
    }
    for (const id of ["compare-a", "compare-b", "compare-tick"]) {
      byId(id).addEventListener("input", () => this.compare());
    }
    byId("replay-pair").addEventListener("click", () => this.animatePair());
    byId("home").addEventListener("click", event => { event.preventDefault(); this.show("film"); });
    byId("back-to-film").addEventListener("click", () => this.show("film"));
    byId("inspect-shot").addEventListener("click", () => this.focusEvent(this.shots[this.shotIndex].event_index, "primary"));
    byId("watch").addEventListener("click", () => this.play());
    byId("play").addEventListener("click", () => this.playing ? this.pause() : this.play());
    byId("timeline").addEventListener("input", event => {
      this.pause();
      this.current = Number(event.currentTarget.value);
      this.draw(this.current);
    });
    byId("speed").addEventListener("change", event => {
      this.speed = Number(event.currentTarget.value);
      this.startClock = performance.now() - this.current / this.speed;
    });
    byId("sound").addEventListener("click", () => this.toggleSound());
    byId("voices").addEventListener("click", () => {
      this.speech.enabled = !this.speech.enabled;
      if (this.speech.enabled) this.voiceShot = -1;
      else this.speech.stop();
      byId("voices").setAttribute("aria-pressed", String(this.speech.enabled));
      setText("voices", this.speech.enabled ? "Voices on" : "Voices off");
    });
    byId("fullscreen").addEventListener("click", async () => {
      try { await byId("scene").requestFullscreen(); }
      catch { this.feedback("Fullscreen is unavailable in this browser."); }
    });
    byId("capture").addEventListener("click", () => this.capture());
    document.addEventListener("keydown", event => {
      if (this.view !== "film" || this.recorder?.state === "recording" || event.target.closest("button,input,select,a")) return;
      if (event.code === "Space") {
        event.preventDefault();
        if (this.playing) this.pause();
        else this.play();
      } else if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        this.pause();
        const offset = event.key === "ArrowRight" ? 1 : -1;
        const shot = this.shots[Math.min(this.shots.length - 1, Math.max(0, this.shotIndex + offset))];
        this.current = shot.start_ms;
        this.draw(this.current);
      }
    });
    this.drawCover();
  }

  selectSource(key) {
    this.audit = this.sources.get(key) || this.primary;
    byId("filter-source").value = key;
    byId("filter-loop").replaceChildren(option("", "All loops"), ...this.audit.loops.map(loop => option(loop, "Loop " + loop)));
    byId("filter-actor").replaceChildren(option("", "All characters"), ...Object.keys(this.audit.cast).map(actor => option(actor, this.name(actor))));
  }

  name(actor, source = this.audit) {
    const person = source.cast[actor];
    return person?.name || (typeof person === "string" ? person : actor) || "Town";
  }

  location(id, source = this.audit) {
    return source.locations[id]?.label || readable(id || "Town");
  }

  show(view) {
    if (this.recorder?.state === "recording" && view !== "film") this.recorder.stop();
    this.view = view;
    if (view !== "film") this.pause();
    if (view !== "compare") this.stopPair();
    byId("player").hidden = view !== "film";
    byId("audit").hidden = view !== "ledger";
    byId("comparison").hidden = view !== "compare";
    for (const id of ["film", "ledger", "compare"]) byId(id + "-view").setAttribute("aria-pressed", String(id === view));
    if (view === "ledger") this.populateEvents();
    if (view === "compare") this.compare();
  }

  drawCover() {
    const opening = this.shots.find(shot => shot.camera === "puddle") || this.shots[0];
    const stage = this.primary.stages[opening.event_index];
    this.renderer.draw(stage, { caption: "", speaker: "", title: "" }, .46);
  }

  draw(time) {
    this.shotIndex = findShot(this.shots, time);
    const shot = this.shots[this.shotIndex];
    const stage = this.primary.stages[shot.event_index];
    const progress = Math.min(1, (time - shot.start_ms) / shot.duration_ms);
    const mark = ["fixture", "local_policy"].includes(this.film.source.mode) || !this.film.source.complete ? this.mode : "";
    this.renderer.draw(stage, shot, progress, mark);
    byId("timeline").value = String(Math.round(time));
    setText("clock", clockText(time) + " / " + clockText(this.film.duration_ms));
    setText("scene-info", "Loop " + shot.loop + " · " + shot.time + " · " + this.location(stage.location, this.primary));
    setText("accessible-caption", [shot.title, shot.speaker, shot.caption].filter(Boolean).join(". "));
    if (this.playing && this.audio.enabled && this.soundShot !== this.shotIndex) {
      this.soundShot = this.shotIndex;
      this.audio.play(shot, this.speed);
    }
    if (this.playing && this.speech.enabled && !this.recorder && this.voiceShot !== this.shotIndex) {
      this.voiceShot = this.shotIndex;
      this.speech.speak(shot, this.speed);
    }
  }

  play(fromStart = false) {
    if (this.playing) return;
    if (fromStart || this.current >= this.film.duration_ms) this.current = 0;
    this.playing = true;
    this.soundShot = -1;
    this.voiceShot = -1;
    byId("cover").hidden = true;
    byId("transport").hidden = false;
    byId("film-info").hidden = false;
    setText("play", "Pause");
    byId("play").setAttribute("aria-label", "Pause");
    this.startClock = performance.now() - this.current / this.speed;
    this.draw(this.current);
    let frameClock = 0;
    const next = time => {
      if (!this.playing) return;
      this.current = Math.min(this.film.duration_ms, Math.max(0, (time - this.startClock) * this.speed));
      if (time - frameClock >= 27 || this.current >= this.film.duration_ms) {
        this.draw(this.current);
        frameClock = time;
      }
      if (this.current >= this.film.duration_ms) {
        this.pause();
        if (this.recorder?.state === "recording") this.recorder.stop();
      } else {
        this.animation = requestAnimationFrame(next);
      }
    };
    this.animation = requestAnimationFrame(next);
  }

  pause() {
    this.playing = false;
    if (this.animation) cancelAnimationFrame(this.animation);
    this.audio.stop();
    this.speech.stop();
    setText("play", "Play");
    byId("play").setAttribute("aria-label", "Play");
  }

  async toggleSound() {
    if (this.audio.enabled) {
      this.audio.enabled = false;
      this.audio.stop();
    } else {
      try {
        await this.audio.enable();
      } catch {
        this.feedback("The browser could not enable sound.");
      }
      if (!this.audio.enabled) this.feedback("Sound is unavailable in this browser.");
      this.soundShot = -1;
    }
    byId("sound").setAttribute("aria-pressed", String(this.audio.enabled));
    setText("sound", this.audio.enabled ? "Sound on" : "Sound off");
  }

  feedback(message) {
    byId("feedback").hidden = !message;
    setText("feedback", message);
  }

  capture() {
    if (this.recorder?.state === "recording") {
      this.recorder.stop();
      return;
    }
    this.pause();
    const source = this.canvas.captureStream(30);
    for (const track of this.audio.output()) source.addTrack(track);
    const choices = ["video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
    const mimeType = choices.find(type => MediaRecorder.isTypeSupported(type));
    if (!mimeType) {
      this.feedback("This browser does not support local video capture.");
      return;
    }
    let recorder;
    try {
      recorder = new MediaRecorder(source, { mimeType });
    } catch {
      this.feedback("The browser could not start a video capture.");
      return;
    }
    const blocks = [];
    recorder.ondataavailable = message => { if (message.data.size) blocks.push(message.data); };
    recorder.onerror = () => this.feedback("The browser stopped recording.");
    recorder.onstop = () => {
      source.getVideoTracks().forEach(track => track.stop());
      this.recorder = null;
      for (const id of ["play", "timeline", "speed", "sound", "voices"]) byId(id).disabled = false;
      setText("capture", "Save clip");
      if (!blocks.length) {
        this.feedback("The recording did not contain any frames.");
        return;
      }
      const type = recorder.mimeType || mimeType;
      const url = URL.createObjectURL(new Blob(blocks, { type }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "loopday-" + this.film.source.mode + (type.startsWith("video/mp4") ? ".mp4" : ".webm");
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      this.feedback("Clip saved.");
    };
    this.recorder = recorder;
    this.speed = 1;
    byId("speed").value = "1";
    for (const id of ["play", "timeline", "speed", "sound", "voices"]) byId(id).disabled = true;
    setText("capture", "Stop recording");
    this.feedback(this.speech.enabled ? "Recording the film and score. On-device voices are for browser playback." :
      "Recording the film from the beginning.");
    recorder.start(250);
    this.play(true);
  }

  match(event) {
    const loop = byId("filter-loop").value, actor = byId("filter-actor").value, kind = byId("filter-kind").value;
    if (loop && String(event.loop) !== loop) return false;
    if (actor && actorFor(event) !== actor && !event.witnesses?.includes(actor)) return false;
    if (!kind) return true;
    if (kind === "decision") return event.type === "decision";
    if (kind === "evidence") return evidenceTypes.has(event.type);
    if (kind === "change") return changeTypes.has(event.type) || ["replay", "replayed", "judged", "changed"].includes(event.mode);
    return event.type !== "decision" && !evidenceTypes.has(event.type) && !changeTypes.has(event.type);
  }

  eventButtons(indices, sourceKey = null) {
    const source = this.sources.get(sourceKey) || this.audit;
    const entries = node("div", null, "event-list");
    for (const index of indices) {
      const event = source.events[index];
      const label = sourceKey ? eventKind(event) : "Loop " + (event.loop ?? 1) + " · " + (event.time ?? "—");
      const button = node("button");
      button.type = "button";
      const description = event.action ? readable(event.action) + " · " + this.name(actorFor(event), source) :
        eventText(event) || eventKind(event);
      button.append(node("span", label, "when"), node("span", description, "event-line"));
      button.title = description;
      if (!sourceKey) button.setAttribute("aria-current", String(index === this.ledgerIndex));
      button.dataset.index = index;
      button.addEventListener("click", () => {
        if (sourceKey) this.focusEvent(index, sourceKey);
        else this.selectEvent(index);
      });
      entries.append(button);
    }
    return entries;
  }

  populateEvents() {
    const list = byId("events");
    const indices = [];
    this.events.forEach((event, index) => { if (this.match(event)) indices.push(index); });
    if (!indices.length) {
      list.replaceChildren(node("p", "No events match these filters.", "no-events"));
      byId("details").replaceChildren(node("h2", "No event selected"));
      return;
    }
    const selected = indices.includes(this.ledgerIndex) ? this.ledgerIndex : indices[0];
    list.replaceChildren(this.eventButtons(indices));
    this.selectEvent(selected);
  }

  focusEvent(index, sourceKey = null) {
    if (sourceKey) this.selectSource(sourceKey);
    for (const id of ["filter-loop", "filter-actor", "filter-kind"]) byId(id).value = "";
    this.ledgerIndex = index;
    this.show("ledger");
    const selected = byId("events").querySelector('[aria-current="true"]');
    selected?.scrollIntoView({ block: "nearest" });
  }

  selectEvent(index) {
    const event = this.events[index];
    if (!event) return;
    const stage = this.audit.stages[index];
    this.ledgerIndex = index;
    const list = byId("events");
    list.querySelector('[aria-current="true"]')?.setAttribute("aria-current", "false");
    list.querySelector('button[data-index="' + index + '"]')?.setAttribute("aria-current", "true");
    const container = byId("details");
    const subject = actorFor(event);
    const type = eventKind(event);
    const heading = node("h2", (subject ? this.name(subject) + " · " : "") + type);
    heading.id = "detail-title";
    const meta = [event.id || "Event " + (index + 1), "Loop " + (event.loop ?? 1), event.time].filter(Boolean).join(" · ");
    container.replaceChildren(node("p", meta, "event-id"), heading);
    const story = eventText(event);
    if (story && event.type !== "decision") container.append(node("p", story, "description"));
    const row = (label, value) => {
      if (value == null || value === "" || (Array.isArray(value) && !value.length)) return;
      const line = node("div", null, "detail-row");
      line.append(node("span", label), node("span", Array.isArray(value) ? value.join(", ") : value));
      container.append(line);
    };
    row("Location", this.location(stage.location));
    if (event.type === "decision") {
      row("Chosen action", event.action && readable(event.action));
      row("Character’s stated reason", event.reason || story);
      row("Available actions", event.available_actions?.map(readable));
    }
    row("Decision mode", event.mode && readable(event.mode));
    row("Scene mode", event.npc_mode && readable(event.npc_mode));
    row("Arrived from", event.moving_from && this.location(event.moving_from));
    row("Witnesses", event.witnesses?.map(actor => this.name(actor)));
    row("Used by", event.to && (Array.isArray(event.to) ? event.to.map(actor => this.name(actor)) : this.name(event.to)));
    row("Observed state", event.state);
    row("Source actor", event.source_actor && this.name(event.source_actor));
    row("Source category", event.source_type && readable(event.source_type));
    if (event.hypothesis) row("Hypothesis", event.hypothesis);
    if (event.predicted) row("Predicted outcome", event.predicted);
    row("Matched previous situation", typeof event.replay_match === "boolean" ? (event.replay_match ? "Yes" : "No") : event.replay_match);
    row("Memory operation", event.operation && readable(event.operation));
    row("Memory content before", event.before);
    row("Memory content after", event.after);
    row("Result", event.observed);
    row("Ending decision", event.ending_reason && readable(event.ending_reason));
    if (event.type === "relationship" && event.deltas && typeof event.deltas === "object") {
      row("Relationship change", Object.entries(event.deltas).filter(([, value]) => value !== 0)
        .map(([key, value]) => readable(key) + " " + (value > 0 ? "+" : "") + value));
    }
    row("Agrees with prediction", typeof event.agrees_with_prediction === "boolean" ? (event.agrees_with_prediction ? "Yes" : "No") : null);
    this.appendLinks(container, event, index);
    this.appendModel(container, event.model_metadata);
    this.appendPolicy(container, event.policy_metadata);
    container.append(node("h3", "Town at this event"));
    const map = node("canvas", null, "map");
    map.setAttribute("aria-label", Object.entries(stage.positions).map(([actor, place]) =>
      this.name(actor) + " at " + this.location(place)).join("; "));
    container.append(map);
    drawTown(map, this.audit.locations, stage, this.audit.roads);
    const cast = node("details", null, "cast-roles");
    cast.append(node("summary", "Character goals"));
    for (const [actor, member] of Object.entries(this.audit.cast)) {
      const line = node("p");
      line.append(node("b", this.name(actor) + " "), member.goal || "");
      cast.append(line);
    }
    container.append(cast);
  }

  appendLinks(container, event, index) {
    const links = node("div", null, "evidence-links");
    const linked = new Set();
    const add = (label, key) => {
      const target = this.audit.eventKeys.get(key);
      if (target === undefined || linked.has(target) || target === index) return;
      linked.add(target);
      const button = node("button", label + " · " + key);
      button.type = "button";
      button.addEventListener("click", () => this.focusEvent(target));
      links.append(button);
    };
    for (const [field, label] of Object.entries(linkFields)) {
      const values = Array.isArray(event[field]) ? event[field] : [event[field]];
      for (const value of values) add(label, typeof value === "object" && value ? value.event_id : value);
    }
    add("Appointment notice", event.policy_metadata?.appointment_plan?.source_event);
    const id = event.id ?? "event-" + index;
    for (const later of this.events.slice(index + 1)) {
      if (["source_event", "trigger", "prediction", "action_evidence", "observation"].some(field => later[field] === id)) {
        add("Later event", later.id);
      }
    }
    if (links.children.length) container.append(node("h3", "Linked evidence"), links);
  }

  appendModel(container, metadata) {
    if (!metadata || typeof metadata !== "object") return;
    const fields = {
      provider: "Provider", model: "Model", model_revision: "Model revision", adapter: "Adapter",
      selection: "Candidate selection", selected_action: "Selected candidate", precision: "Precision",
      raw_projections: "Raw activation projection", projection_z: "Calibrated activation projection",
      persona_bank: "Persona calibration", steering: "Applied coefficients", candidates: "Action candidates",
      ranker_held_out: "Held-out ranker results",
    };
    const inspector = node("details", null, "model-info");
    inspector.append(node("summary", "Model measurements"));
    const format = value => value && typeof value === "object" ?
      Object.entries(value).map(([name, evidence]) => readable(name) + " = " + evidence).join(" · ") : readable(value);
    for (const [key, label] of Object.entries(fields)) {
      const value = metadata[key];
      if (value == null || value === "" || (typeof value === "object" && !Object.keys(value).length)) continue;
      const line = node("div", null, "detail-row");
      const text = key === "candidates" && Array.isArray(value) ? value.map(candidate => {
        const name = readable(candidate.action || "rejected");
        return Number.isFinite(candidate.score) ? name + " (" + candidate.score.toFixed(3) + ")" : name;
      }).join(" · ") : format(value);
      line.append(node("span", label), node("span", text));
      inspector.append(line);
    }
    if (metadata.model_trace) {
      inspector.append(node("h3", "Model-emitted text"));
      inspector.append(node("p", "This text is a provider output. Use linked events to verify what happened in the world."));
      inspector.append(node("pre", metadata.model_trace));
    }
    if (inspector.children.length > 1) container.append(inspector);
  }

  appendPolicy(container, metadata) {
    if (!Array.isArray(metadata?.presented_options) || !metadata.presented_options.length) return;
    const ledger = node("details", null, "model-info");
    ledger.append(node("summary", "Local policy scores"));
    ledger.append(node("p", "The local agent scored each allowed action using the listed factors and seeded exploration."));
    const plan = metadata.appointment_plan;
    if (plan) {
      const clock = tick => tick == null ? "unavailable" :
        String(Math.floor((360 + tick * 30) / 60) % 24).padStart(2, "0") + (tick % 2 ? ":30" : ":00");
      const caption = ["Piano lesson opens " + clock(plan.opens), "Arrival if acting now " + clock(plan.projected_lesson_if_act_now),
        "Arrival after waiting " + clock(plan.projected_lesson_if_wait)];
      ledger.append(node("p", caption.join(" · ")));
    }
    for (const candidate of metadata.presented_options) {
      const line = node("div", null, "detail-row");
      const mark = candidate.action === metadata.selected_action ? " · chosen" : "";
      const value = Number.isFinite(candidate.score) ? candidate.score.toFixed(2) : "—";
      const draw = Number.isFinite(candidate.exploration) ? " · Exploration " + candidate.exploration.toFixed(2) : "";
      const factors = (candidate.factors || []).map(factor =>
        (factor.weight > 0 ? "+" : "") + factor.weight + " " + factor.reason).join(" · ");
      const scores = node("div");
      scores.append(node("strong", value + draw));
      if (factors) scores.append(node("p", factors));
      line.append(node("span", readable(candidate.action) + mark), scores);
      ledger.append(line);
    }
    container.append(ledger);
  }

  compare() {
    this.stopPair();
    const a = byId("compare-a").value, b = byId("compare-b").value;
    const tick = Number(byId("compare-tick").value);
    const clock = 6 * 60 + tick * 30;
    setText("compare-time", String(Math.floor(clock / 60) % 24).padStart(2, "0") + ":" + String(clock % 60).padStart(2, "0"));
    const note = byId("compare-note");
    note.hidden = a !== b;
    setText("compare-note", this.primary.loops.length === 1 && !this.reference ?
      "This run contains one loop." : "Choose two loops to compare their choices.");
    const container = byId("compare-columns");
    container.replaceChildren();
    const days = [a, b].map(value => {
      const [key, day] = value.split(":");
      const source = this.sources.get(key);
      const all = source.byLoop.get(Number(day)) || [];
      const current = all.filter(index => source.events[index].type !== "day_two" && Number(source.events[index].tick) === tick);
      const last = all.findLast(index => source.events[index].type !== "day_two" && Number(source.events[index].tick) <= tick);
      return { key, day, source, current, last };
    });
    const typeThere = ({ source, current }, type) => current.some(index => source.events[index].type === type);
    const common = visualOrder.find(type => days.every(day => typeThere(day, type)));
    this.currentPair = [];
    for (const [side, { key, day, source, current, last }] of days.entries()) {
      const column = node("article", null, "compare-column");
      column.append(node("h2", (this.reference ? source.label + " · " : "") + "Loop " + day));
      const preferred = common || visualOrder.find(type => typeThere({ source, current }, type));
      const picked = current.find(index => source.events[index].type === preferred) ?? last;
      if (picked !== undefined) {
        const { canvas, renderer } = this.comparisonScreen[side];
        const stage = source.stages[picked];
        const event = source.events[picked];
        const caption = current.includes(picked) && ["puddle", "test_result", "reply", "performance", "kindness", "exit"].includes(event.type)
          ? eventText(event) : "";
        const shot = { caption, speaker: caption ? stage.speaker : "" };
        canvas.setAttribute("aria-label", eventText(event) || "Town at this time");
        column.append(canvas);
        this.currentPair.push({ renderer, stage, shot });
      }
      if (last !== undefined) {
        const mapPanel = node("details");
        mapPanel.append(node("summary", "Town positions"));
        const map = node("canvas", null, "map");
        map.setAttribute("aria-label", "Town in loop " + day);
        mapPanel.append(map);
        column.append(mapPanel);
        drawTown(map, source.locations, source.stages[last], source.roads);
      }
      if (current.length) column.append(this.eventButtons(current, key));
      else column.append(node("p", "No events at this time.", "no-events"));
      container.append(column);
    }
    byId("replay-pair").disabled = this.currentPair.length !== 2 || a === b;
    this.drawPair(.48);
    const summary = byId("compare-changes");
    summary.replaceChildren();
    const actions = days.map(({ source, current }) => new Map(current.map(index => source.events[index])
      .filter(event => event.type === "decision")
      .map(event => [actorFor(event) + ":" + (event.exchange || 0), event])));
    for (const [key, previous] of actions[0]) {
      const following = actions[1].get(key);
      if (!following || previous.action === following.action) continue;
      const line = node("p");
      line.append(node("b", this.name(actorFor(previous), days[0].source) + " "),
        readable(previous.action) + " → " + readable(following.action));
      summary.append(line);
    }
    summary.hidden = summary.children.length === 0 || a === b;
  }

  drawPair(progress) {
    for (const { renderer, stage, shot } of this.currentPair || []) renderer.draw(stage, shot, progress);
  }

  stopPair() {
    if (this.pairAnimation) cancelAnimationFrame(this.pairAnimation);
    this.pairAnimation = null;
  }

  animatePair() {
    this.stopPair();
    const start = performance.now();
    let lastFrame = 0;
    const step = now => {
      const progress = Math.max(0, Math.min(1, (now - start) / 3100));
      if (now - lastFrame >= 27 || progress === 1) {
        this.drawPair(progress);
        lastFrame = now;
      }
      this.pairAnimation = progress < 1 ? requestAnimationFrame(step) : null;
    };
    this.pairAnimation = requestAnimationFrame(step);
  }
}

function witnessMode(mode) {
  const names = {
    live: "Live Qwen and Muse agents",
    muse_canary: "Muse canary with fixture Phil",
    local_policy: "Local policy test",
    fixture: "Scripted fixture test",
  };
  return names[mode] || "Run source pending";
}

function eventSource(event) {
  if (event.mode === "replay") return "Replayed earlier decision";
  if (event.mode === "fixture") return "Fixture choice";
  if (event.mode === "local_policy") return "Local policy choice";
  if (event.mode === "live") return event.model_metadata?.model ? "Model choice · " + event.model_metadata.model : "Live model choice";
  return "Recorded world event";
}

class FollowViewer {
  constructor() {
    this.etag = "";
    this.following = true;
    this.active = null;
    this.bundle = null;
    this.rendered = new Map();
    byId("player").hidden = true;
    byId("views").hidden = true;
    byId("follow-pane").hidden = false;
    byId("home").href = "/";
    byId("follow-latest").addEventListener("click", () => {
      this.following = true;
      if (this.bundle) this.display(this.bundle.run.events.length - 1);
    });
  }

  async poll() {
    try {
      const headers = this.etag ? { "If-None-Match": this.etag } : {};
      const response = await fetch("/follow.json", { headers });
      if (response.status !== 304) {
        if (!response.ok) throw new Error("Could not read the checkpoint");
        this.update(await response.json());
        this.etag = response.headers.get("ETag") || "";
      }
      byId("follow-connection").hidden = true;
    } catch {
      setText("follow-connection", "Checkpoint temporarily unavailable. Retrying…");
      byId("follow-connection").hidden = false;
    } finally {
      setTimeout(() => this.poll(), 650);
    }
  }

  update(snapshot) {
    const source = witnessMode(snapshot.mode);
    setText("run-mode", source);
    const labels = { in_progress: "In progress", partial: "Partial run saved", complete: "Complete" };
    setText("follow-status", snapshot.status === "waiting" ? "Waiting for the first committed event." :
      labels[snapshot.status] + " · " + snapshot.committed + " committed events");
    if (!snapshot.bundle) {
      this.bundle = null;
      this.active = null;
      this.following = true;
      byId("follow-content").hidden = true;
      byId("follow-replay").hidden = true;
      if (this.animation) cancelAnimationFrame(this.animation);
      return;
    }
    byId("follow-content").hidden = false;
    byId("follow-replay").hidden = false;
    if (!this.renderer) this.renderer = new FilmRenderer(byId("follow-stage"), snapshot.bundle.art);
    const previous = this.bundle?.run.events.length || 0;
    this.bundle = snapshot.bundle;
    const events = snapshot.bundle.run.events;
    if (events.length < previous) {
      this.active = null;
      this.following = true;
    }
    const latest = events.slice(-38).reverse();
    const list = node("div", null, "event-list");
    this.rendered.clear();
    latest.forEach((event, offset) => {
      const index = events.length - 1 - offset;
      const button = node("button");
      button.type = "button";
      const description = event.action ? readable(event.action) + " · " + eventSource(event) : eventText(event) || eventKind(event);
      button.append(node("span", "Loop " + (event.loop ?? 1) + " · " + (event.time || "—"), "when"),
        node("span", description, "event-line"));
      button.title = description;
      button.addEventListener("click", () => {
        this.following = false;
        this.display(index);
      });
      this.rendered.set(index, button);
      list.append(button);
    });
    byId("follow-events").replaceChildren(list);
    const preferred = this.suggested(events, previous);
    if (this.active == null || (this.following && preferred !== this.active)) this.display(preferred);
    else this.rendered.get(this.active)?.setAttribute("aria-current", "true");
  }

  suggested(events, previous = Math.max(0, events.length - 10)) {
    for (let index = events.length - 1; index >= previous; index--) {
      if (events[index].type === "day_two" || visualOrder.includes(events[index].type)) return index;
    }
    return events.length > previous ? events.length - 1 : (this.active ?? events.length - 1);
  }

  display(index) {
    const event = this.bundle.run.events[index];
    const stage = this.bundle.stages[index];
    if (!event || !stage) return;
    this.rendered.get(this.active)?.setAttribute("aria-current", "false");
    this.active = index;
    this.rendered.get(index)?.setAttribute("aria-current", "true");
    const actor = actorFor(event);
    const name = this.bundle.run.cast?.[actor]?.name || actor;
    const heading = [name, event.action ? readable(event.action) : eventKind(event)].filter(Boolean).join(" · ");
    const details = byId("follow-detail");
    details.replaceChildren(node("p", [event.id, eventSource(event), event.time].filter(Boolean).join(" · "), "event-id"),
      node("h2", heading), node("p", eventText(event)));
    const shot = this.bundle.film.shots.find(candidate => candidate.event_index === index);
    const cue = shot || { caption: stage.subtitle, speaker: stage.speaker };
    if (this.animation) cancelAnimationFrame(this.animation);
    const start = performance.now();
    const duration = Math.min(3200, stage.duration_ms);
    const draw = time => {
      const progress = Math.max(0, Math.min(1, (time - start) / duration));
      this.renderer.draw(stage, cue, progress);
      this.animation = progress < 1 ? requestAnimationFrame(draw) : null;
    };
    draw(start);
  }
}

async function startReplay() {
  if (document.body.dataset.follow === "true") return new FollowViewer().poll();
  const embedded = byId("loopday-bundle");
  let bundle;
  if (embedded) {
    bundle = JSON.parse(embedded.textContent);
  } else {
    const response = await fetch("/bundle.json");
    if (!response.ok) throw new Error("The replay bundle could not be loaded.");
    bundle = await response.json();
  }
  return new ReplayViewer(bundle);
}

startReplay().catch(error => {
  const field = byId("error");
  field.hidden = false;
  field.textContent = error.message;
});
