const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const smooth = value => {
  const f = clamp(value, 0, 1);
  return f * f * (3 - 2 * f);
};
const vecAdd = (a, b) => a.map((n, i) => n + b[i]);
const vecSub = (a, b) => a.map((n, i) => n - b[i]);
const scale = (a, k) => a.map(n => k * n);
const dot = (a, b) => a.reduce((sum, n, i) => sum + n * b[i], 0);
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const unit = vec => scale(vec, 1 / (Math.hypot(...vec) || 1));
const yawed = ([x, y, z], angle) => [
  x * Math.cos(angle) + z * Math.sin(angle), y,
  -x * Math.sin(angle) + z * Math.cos(angle),
];

const geo = {
  box: {
    vertices: [
      [-.5, -.5, -.5], [.5, -.5, -.5], [.5, .5, -.5], [-.5, .5, -.5],
      [-.5, -.5, .5], [.5, -.5, .5], [.5, .5, .5], [-.5, .5, .5],
    ],
    faces: [[0, 3, 2, 1], [4, 5, 6, 7], [0, 4, 7, 3], [5, 1, 2, 6], [3, 7, 6, 2], [0, 1, 5, 4]],
  },
  gable: {
    vertices: [[-.5, -.5, -.5], [.5, -.5, -.5], [0, .5, -.5], [-.5, -.5, .5], [.5, -.5, .5], [0, .5, .5]],
    faces: [[0, 2, 1], [3, 4, 5], [0, 3, 5, 2], [1, 2, 5, 4], [0, 1, 4, 3]],
  },
};
const chamfered = [[-.5, -.30], [-.30, -.5], [.30, -.5], [.5, -.30], [.5, .30], [.30, .5], [-.30, .5], [-.5, .30]];
geo.bevel = {
  vertices: [-.5, .5].flatMap(y => chamfered.map(([x, z]) => [x, y, z])),
  faces: [
    chamfered.map((_, index) => index),
    chamfered.map((_, index) => 15 - index),
    ...chamfered.map((_, index) => {
      const next = (index + 1) % chamfered.length;
      return [index, index + 8, next + 8, next];
    }),
  ],
};
for (const name of ["cone", "disc"]) {
  const count = name === "cone" ? 7 : 16;
  const vertices = Array.from({ length: count }, (_, i) => {
    const angle = 2 * Math.PI * i / count;
    return [.5 * Math.cos(angle), name === "cone" ? -.5 : 0, .5 * Math.sin(angle)];
  });
  if (name === "cone") {
    vertices.push([0, .5, 0]);
    geo[name] = { vertices, faces: Array.from({ length: count }, (_, i) => [i, count, (i + 1) % count]) };
  } else {
    geo[name] = { vertices, faces: [vertices.map((_, i) => count - i - 1)] };
  }
}

function colored(name, p, s, color, extra = {}) {
  return { name, p, s, color, shape: "box", yaw: 0, emissive: false, ...extra };
}

const segments = {
  0: "abcedf", 1: "bc", 2: "abged", 3: "abgcd",
  4: "fgbc", 5: "afgcd", 6: "afgecd", 7: "abc",
  8: "abcdefg", 9: "abfgcd",
};
const segmentPositions = {
  a: [0, .068, .082, .012], g: [0, 0, .082, .012], d: [0, -.068, .082, .012],
  f: [-.041, .033, .012, .061], b: [.041, .033, .012, .061],
  e: [-.041, -.033, .012, .061], c: [.041, -.033, .012, .061],
};

function radioDisplay(phase, tomorrow, time) {
  const chars = /^\d\d:\d\d$/.test(time) ? time.replace(":", "") : phase < .22 ? "0559" : "0600";
  const shapes = [];
  const color = tomorrow ? "#ffb36f" : "#f37d57";
  for (let i = 0; i < chars.length; i++) {
    const center = -.277 + .137 * i + (i > 1 ? .045 : 0);
    for (const segment of segments[chars[i]]) {
      const [sx, sy, w, h] = segmentPositions[segment];
      shapes.push(colored("segment", [center + sx, 1.467 + sy, -.074], [w, h, .006], color, { emissive: true }));
    }
  }
  for (const y of [1.431, 1.502]) {
    shapes.push(colored("colon", [-.048, y, -.074], [.013, .014, .005], color, { emissive: true }));
  }
  return shapes;
}

const pianoMelody = [7, 4, 3, 5, 1, 3, 6, 8, 4];
const practiceMelody = [3, 5, 1];

export function frameObjects(art, stage, progress) {
  const melody = stage.sound === "practice" ? practiceMelody : pianoMelody;
  const note = (progress - .15) / (stage.sound === "practice" ? .18 : .073);
  const rightKey = melody[Math.max(0, Math.min(melody.length - 1, Math.floor(note)))];
  const leftKey = Math.max(0, rightKey - 2);
  const objects = (art.sets[stage.set] || art.sets.main_st).flatMap(item => {
    if (item.name.startsWith("animal_")) {
      if (stage.camera !== "square") return [];
      const reveal = smooth((progress - .12) / .48);
      return [{ ...item, p: vecAdd(item.p, [0, .09 * reveal, -.33 + .53 * reveal]) }];
    }
    if (["country_rd", "outskirts"].includes(stage.set) && !stage.barrier &&
        (item.name.startsWith("gate_") || item.name === "road_barrier")) return [];
    if (stage.pencil === "broken" && (item.name === "pencil_right" || item.name === "pencil_tip")) {
      const shift = stage.camera === "insert" ? .15 + .13 * smooth(progress) : .28;
      return [{ ...item, p: vecAdd(item.p, [shift, .006, .12]), yaw: -.45 }];
    }
    if (stage.camera === "piano" && item.name.startsWith("white_key")) {
      const index = Number(item.name.split("_").at(-1));
      if ((index === rightKey || index === leftKey) && note >= 0 && note < melody.length && note % 1 < .64) {
        return [{ ...item, p: vecAdd(item.p, [0, -.03, 0]), color: "#f6cc7e" }];
      }
    }
    if (stage.branch_breaks && ["rescue_branch", "rescue_snow"].includes(item.name)) {
      const fall = smooth((progress - .26) / .42);
      return [{ ...item, p: vecAdd(item.p, [.24 * fall, -1.90 * fall, .13 * fall]), yaw: -.43 * fall }];
    }
    return [item];
  });
  if (stage.set === "inn" && !(stage.switch_radio && progress > .69)) {
    objects.push(...radioDisplay(progress, stage.tomorrow, stage.camera === "clock" ? "" : stage.time));
  }
  if (stage.switch_radio && progress > .46) {
    const reach = smooth((progress - .46) / .23) - smooth((progress - .74) / .25);
    const x = 1.27 - .91 * reach;
    objects.push(colored("radio_hand", [x, 1.74, -.20], [.17, .105, .16], "#e0a688", { yaw: .21 }));
    objects.push(colored("radio_coat", [x + .47, 1.77, -.19], [.87, .147, .17], "#a94d57", { yaw: .075 }));
  }
  for (const role of stage.cast) {
    let dx = 0, dz = 0, bob = 0;
    if (role.pose === "walk") {
      const amble = smooth(progress);
      dx = (1 - amble) * (role.approach?.[0] ?? (stage.camera === "puddle" ? -2.22 : -2.7));
      dz = stage.camera === "puddle" ? (stage.splash ? .12 : -.84 * Math.sin(Math.PI * amble)) :
        (role.approach?.[1] ?? .4) * (1 - amble);
      bob = .037 * Math.sin(progress * 22 * Math.PI);
    }
    const playing = role.pose === "play";
    const crouch = playing ? -.28 : 0;
    const smaller = role.scale || 1;
    let lift = role.elevation || 0;
    if (role.pose === "descend") {
      const lowered = smooth((progress - .26) / .62);
      dx = .47 * lowered;
      lift *= 1 - lowered;
    }
    const base = [role.x + dx, bob + crouch + lift, role.z + dz];
    const shadow = stage.set === "inn" ? "#7c645b" : stage.set === "hotel" ? "#754d43" : "#91a5b0";
    objects.push(colored("cast_shadow", [base[0], .013, base[2]], [1.15, .009, .72], shadow, { shape: "disc" }));
    for (const part of art.actors[role.actor] || art.actors.phil) {
      const position = part.p.slice();
      const shape = part.s.slice();
      const side = part.name.startsWith("left_") ? -1 : 1;
      if (role.pose === "walk" && (part.name.endsWith("_foot") || part.name.endsWith("_leg"))) {
        position[2] += .22 * Math.sin(progress * 8 * Math.PI) * side;
      }
      if (role.pose === "talk" && (part.name === "right_arm" || part.name === "right_hand")) {
        position[1] += .19 + .092 * Math.sin(progress * 7 * Math.PI);
        position[2] += .14;
      }
      if (role.pose === "talk" && part.name === "mouth") {
        shape[1] += .042 * Math.abs(Math.sin(progress * 15 * Math.PI));
      }
      if (role.pose === "aim_camera" && ["camera", "lens", "lens_glass", "right_arm", "right_hand"].includes(part.name)) {
        position[1] += .34 * smooth(progress / .25);
        position[2] += .22 * smooth(progress / .25);
      }
      if (role.pose === "lift" && (part.name.endsWith("_arm") || part.name.endsWith("_hand"))) {
        const raise = smooth(progress / .25) * (1 - .77 * smooth((progress - .31) / .58));
        position[1] += .89 * raise;
        position[2] += .37 * raise;
      }
      if (role.pose === "listen" && (part.name === "face" || part.name.startsWith("hair") ||
          part.name.endsWith("_eye") || ["nose", "mouth"].includes(part.name))) {
        position[1] -= .043 * Math.sin(progress * Math.PI * 2) ** 2;
      }
      if (role.pose === "reach" && (part.name.endsWith("_hand") || part.name.endsWith("_arm"))) {
        position[1] += .25 + .04 * Math.sin(progress * 16 * Math.PI + side);
        position[2] += .27;
      }
      if (playing && part.name.endsWith("_hand")) {
        const beat = side < 0 ? rightKey : leftKey;
        const bent = note >= 0 && note < melody.length ? Math.sin(Math.PI * (note % 1)) : .7;
        position[0] = role.x - (-1.34 + beat * .163);
        position[1] += .56 + .046 * bent;
        position[2] += .664 + .053 * bent;
      }
      if (playing && part.name.endsWith("_arm")) {
        position[1] += .18;
        position[2] += .27;
        shape[1] *= .73;
        shape[2] *= 1.70;
      }
      if (playing && part.name.endsWith("_leg")) {
        position[2] += .20;
        position[1] += .26;
        shape[1] *= .7;
      }
      if (playing && part.name.endsWith("_foot")) position[1] -= crouch;
      objects.push({ ...part, s: scale(shape, smaller), name: role.actor + "_" + part.name,
        p: vecAdd(base, yawed(scale(position, smaller), role.yaw)), yaw: role.yaw + part.yaw });
    }
  }
  if (stage.splash && progress > .32 && progress < .75) {
    const phase = (progress - .32) / .43;
    for (let i = 0; i < 12; i++) {
      const angle = i * Math.PI / 6;
      const range = (.11 + phase * .74) * (1 + i % 4 * .18);
      const rise = Math.sin(Math.PI * phase) * (.33 + i % 5 * .077);
      objects.push(colored("droplet", [-1.45 + Math.cos(angle) * range, .025 + rise, 1.0 + Math.sin(angle) * range],
        [.06, .067, .06], "#97b6bf"));
    }
  }
  return objects;
}

function transformed(item) {
  const g = geo[item.shape] || geo.box;
  const vertices = g.vertices.map(v => vecAdd(item.p, yawed(v.map((n, i) => n * item.s[i]), item.yaw)));
  return [vertices, g.faces];
}

const hex = color => [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16));
const rgb = colors => "rgb(" + colors.map(n => Math.round(clamp(n, 0, 255))).join(",") + ")";
const tint = (a, b, weight) => a.map((value, i) => value * (1 - weight) + b[i] * weight);
const keyLight = unit([-.45, .92, .55]);

export function projectScene(art, stage, progress, width, height) {
  const drift = {
    clock: [0, 0, 0], puddle: [-.21, -.06, -.48], road: [-.43, -.08, -.58],
    piano: [-.41, .05, -.56], ballroom: [-.50, -.06, -.48], square: [-.57, .06, -.40],
    tree: [-.12, -.14, -.27], two_shot: [-.13, -.03, -.37], insert: [-.10, 0, -.20],
  };
  const eye = vecAdd(stage.eye, scale(drift[stage.camera] || [-.21, 0, -.36], smooth(progress)));
  const objects = frameObjects(art, stage, progress);
  const sky = hex(stage.weather.sky);
  const forward = unit(vecSub(stage.look, eye));
  const right = unit(cross(forward, [0, 1, 0]));
  const up = cross(right, forward);
  const focal = height / (2 * Math.tan(stage.fov * Math.PI / 360));
  const light = hex(stage.weather.light);
  const queue = [];
  for (const item of objects) {
    const [vertices, faces] = transformed(item);
    const color = hex(item.color);
    const view = vertices.map(point => {
      const rel = vecSub(point, eye);
      return [dot(rel, right), dot(rel, up), dot(rel, forward)];
    });
    for (const face of faces) {
      const [a, b, c] = face.map(i => vertices[i]);
      const normal = unit(cross(vecSub(b, a), vecSub(c, a)));
      if (dot(normal, vecSub(eye, a)) <= 0) continue;
      const source = face.map(i => view[i]);
      const clipped = [];
      for (let i = 0; i < source.length; i++) {
        const start = source[i], end = source[(i + 1) % source.length];
        const front = start[2] > .085, next = end[2] > .085;
        if (front) clipped.push(start);
        if (front !== next) {
          const t = (.085 - start[2]) / (end[2] - start[2]);
          clipped.push(vecAdd(start, scale(vecSub(end, start), t)));
        }
      }
      if (clipped.length < 3) continue;
      const points = clipped.map(([x, y, d]) => [width / 2 + x / d * focal, height / 2 - y / d * focal, d]);
      const depth = source.reduce((value, point) => value + point[2], 0) / source.length;
      const lit = item.emissive ? 1.09 : (.48 + .48 * Math.max(0, dot(normal, keyLight))) * stage.weather.ambient;
      const shade = tint(scale(color, lit * 1.19), light, item.emissive ? .08 : .16);
      const haze = stage.storm ? clamp((depth - 6) * .023, 0, .53) : clamp((depth - 13) * .012, 0, .24);
      // The floor remains the furthest surface. This keeps the perspective
      // plane behind nearby actors even where it crosses the camera.
      const priority = item.name === "ground" ? 1_000 :
        (item.name === "segment" || item.name === "colon") ? depth - .19 : depth;
      queue.push([priority, rgb(tint(shade, sky, haze)), points]);
    }
  }
  queue.sort((a, b) => b[0] - a[0]);
  return {
    sky: [rgb(tint(sky, [44, 55, 73], .27)), stage.weather.sky, rgb(tint(sky, [181, 181, 150], .22))],
    faces: queue.map(([, color, points]) => [color, points]),
  };
}

function renderSky(ctx, width, height, scene) {
  const horizon = ctx.createLinearGradient(0, 0, 0, height);
  for (const [i, offset] of [0, .65, 1].entries()) horizon.addColorStop(offset, scene.sky[i]);
  ctx.fillStyle = horizon;
  ctx.fillRect(0, 0, width, height);
}

function renderSoftware(ctx, scene) {
  for (const [color, points] of scene.faces) {
    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
      const [x, y] = points[i];
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }
}

const vertexSource = `
attribute vec3 pixel;
attribute vec3 rgb;
uniform vec2 size;
varying vec3 shade;
void main() {
  vec2 screen = pixel.xy / size * 2.0 - 1.0;
  float d = pixel.z;
  gl_Position = vec4(screen.x * d, -screen.y * d, 1.001 * d - .1701, d);
  shade = rgb;
}`;
const fragmentSource = `
precision mediump float;
varying vec3 shade;
void main() { gl_FragColor = vec4(shade, 1.0); }
`;

class DepthCanvas {
  constructor(width, height) {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const gl = canvas.getContext("webgl", { antialias: true, alpha: true, preserveDrawingBuffer: true });
    if (!gl) throw new Error("WebGL unavailable");
    const shader = (type, source) => {
      const item = gl.createShader(type);
      gl.shaderSource(item, source);
      gl.compileShader(item);
      if (!gl.getShaderParameter(item, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(item));
      return item;
    };
    const program = gl.createProgram();
    const vertex = shader(gl.VERTEX_SHADER, vertexSource);
    const fragment = shader(gl.FRAGMENT_SHADER, fragmentSource);
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);
    gl.useProgram(program);
    gl.uniform2f(gl.getUniformLocation(program, "size"), width, height);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    for (const [attribute, offset] of [["pixel", 0], ["rgb", 12]]) {
      const location = gl.getAttribLocation(program, attribute);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 24, offset);
    }
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.viewport(0, 0, width, height);
    gl.clearColor(0, 0, 0, 0);
    this.context = gl;
    this.canvas = canvas;
  }

  draw(output, scene) {
    const gl = this.context;
    if (gl.isContextLost()) return false;
    const data = [];
    for (const [color, points] of scene.faces) {
      const channels = color.slice(4, -1).split(",").map(value => Number(value) / 255);
      for (let i = 1; i + 1 < points.length; i++) {
        for (const point of [points[0], points[i], points[i + 1]]) data.push(...point, ...channels);
      }
    }
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STREAM_DRAW);
    gl.drawArrays(gl.TRIANGLES, 0, data.length / 6);
    output.drawImage(this.canvas, 0, 0);
    return true;
  }
}

function fitLines(ctx, text, maxWidth, limit = 3) {
  const lines = [];
  let active = "";
  for (const word of text.split(/\s+/)) {
    if (!active || ctx.measureText(active + " " + word).width <= maxWidth) {
      active += (active ? " " : "") + word;
    } else {
      lines.push(active);
      if (lines.length >= limit) {
        lines[limit - 1] += "…";
        return lines;
      }
      active = word;
    }
  }
  if (active) lines.push(active);
  return lines;
}

function renderOverlays(ctx, width, height, stage, shot, progress, inputMode) {
  if (stage.flurry > 0) {
    const unit = height / 720;
    for (let i = 0; i < 136 * stage.flurry; i++) {
      const gust = (stage.storm ? 395 : 65) + i % 7 * 12;
      const x = (i * 163.397 * unit + progress * gust) % width;
      const y = (i * 52.613 * unit + progress * (105 + i % 4 * 18)) % height;
      const size = Math.max(1, (1 + i % 9 * .30) * unit);
      ctx.fillStyle = i % 4 === 0 ? "rgba(221,239,247,.66)" : "rgba(218,235,244,.41)";
      ctx.fillRect(x, y, size * (stage.storm ? 1.55 : 1), size);
    }
  }
  const edge = ctx.createRadialGradient(width * .53, height * .45, height * .32,
    width * .53, height * .45, Math.max(width, height) * .62);
  edge.addColorStop(0, "rgba(9,15,28,0)");
  edge.addColorStop(1, "rgba(9,15,28,.35)");
  ctx.fillStyle = edge;
  ctx.fillRect(0, 0, width, height);
  if (shot?.title) {
    const fade = smooth(progress / .15) * smooth((1 - progress) / .2);
    ctx.save();
    ctx.globalAlpha = fade;
    const gradient = ctx.createLinearGradient(0, height * .62, 0, height);
    gradient.addColorStop(0, "rgba(16,22,28,0)");
    gradient.addColorStop(1, "rgba(16,22,28,.82)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, height * .62, width, height * .38);
    ctx.textAlign = "center";
    ctx.fillStyle = "#f8eee0";
    ctx.font = `700 ${Math.round(height * .077)}px Georgia, serif`;
    ctx.fillText(shot.title, width * .5, height * (shot.caption ? .79 : .889));
    ctx.restore();
  }
  const caption = shot?.caption ?? stage.subtitle;
  const speaker = shot?.speaker || stage.speaker;
  if (caption) {
    const font = Math.max(15, Math.round(height * .036));
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    const lines = fitLines(ctx, caption, width * .77);
    const rowHeight = font * 1.35;
    const center = width * .5;
    const bottom = height * .91;
    ctx.textAlign = "center";
    for (let i = 0; i < lines.length; i++) {
      const y = bottom - (lines.length - 1 - i) * rowHeight;
      const size = ctx.measureText(lines[i]).width;
      ctx.fillStyle = "rgba(12,21,28,.82)";
      ctx.fillRect(center - size / 2 - 14, y - font * .91, size + 28, rowHeight);
      ctx.fillStyle = "#fffcf3";
      ctx.fillText(lines[i], center, y);
    }
    if (speaker) {
      ctx.font = `700 ${Math.round(font * .70)}px system-ui, sans-serif`;
      ctx.fillStyle = "#ffe2b8";
      ctx.shadowColor = "#121920";
      ctx.shadowBlur = 4;
      ctx.fillText(speaker, center, bottom - lines.length * rowHeight - font * .15);
      ctx.shadowBlur = 0;
    }
  }
  if (inputMode) {
    const font = Math.max(10, Math.round(height * .023));
    ctx.font = `600 ${font}px system-ui, sans-serif`;
    ctx.textAlign = "left";
    const badge = ctx.measureText(inputMode).width;
    ctx.fillStyle = "rgba(15,22,29,.72)";
    ctx.fillRect(12, 12, badge + 18, font + 12);
    ctx.fillStyle = "#f4ead9";
    ctx.fillText(inputMode, 21, 21 + font * .73);
  }
}

export class FilmRenderer {
  constructor(canvas, art) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.art = art;
    try { this.depth = new DepthCanvas(canvas.width, canvas.height); }
    catch { this.depth = null; }
  }

  draw(stage, shot, progress, inputMode = "") {
    const { canvas, ctx } = this;
    const scene = projectScene(this.art, stage, progress, canvas.width, canvas.height);
    renderSky(ctx, canvas.width, canvas.height, scene);
    if (!this.depth?.draw(ctx, scene)) renderSoftware(ctx, scene);
    renderOverlays(ctx, canvas.width, canvas.height, stage, shot, progress, inputMode);
  }
}
