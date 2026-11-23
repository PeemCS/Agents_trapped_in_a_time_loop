const ids = new Map();
const draws = { fills: 0 };
const gradient = { addColorStop() {} };
const canvasContext = {
  fillRect() { draws.fills += 1; }, createLinearGradient: () => gradient, createRadialGradient: () => gradient,
  beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, fill() {}, stroke() {}, arc() {},
  fillText() {}, measureText: text => ({ width: text.length * 9 }), save() {}, restore() {},
};

class TestElement {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.attributes = new Map();
    this.listeners = new Map();
    this.dataset = {};
    this.width = 1280;
    this.height = 720;
    this.value = "";
    this.hidden = false;
  }

  get textContent() {
    return this.text ?? this.children.map(child => typeof child === "string" ? child : child.textContent).join("");
  }

  set textContent(text) {
    this.children = [];
    this.text = String(text);
  }

  append(...children) {
    this.children.push(...children);
  }

  replaceChildren(...children) {
    this.children = [...children];
    this.text = null;
  }

  querySelector(pattern) {
    const visit = item => {
      if (!(item instanceof TestElement)) return null;
      if (pattern === '[aria-current="true"]' && item.attributes.get("aria-current") === "true") return item;
      if (pattern === 'button[data-index="' + item.dataset.index + '"]') return item;
      return item.children.map(visit).find(Boolean) || null;
    };
    return visit(this);
  }

  setAttribute(key, value) { this.attributes.set(key, value); }
  addEventListener(name, call) { this.listeners.set(name, call); }
  getContext(kind) { return kind === "2d" ? canvasContext : null; }
  scrollIntoView() {}
}

globalThis.document = {
  body: new TestElement("body"),
  createElement: tag => new TestElement(tag),
  getElementById: id => ids.get(id),
  addEventListener() {},
};
globalThis.performance = { now: () => 1_000 };
globalThis.requestAnimationFrame = () => 42;
globalThis.cancelAnimationFrame = () => {};

function runChecks(bundle, elementIds) {
  for (const id of elementIds) ids.set(id, new TestElement(id));
  const viewer = new ReplayViewer(bundle);
  const check = (condition, message) => {
    if (!condition) throw new Error(message);
  };
  check(byId("run-mode").textContent === "Fixture film", "Fixture label changed");
  check(byId("watch").disabled === false, "Film never became playable");
  viewer.play();
  check(draws.fills > 1 && byId("cover").hidden && !byId("transport").hidden, "Film failed to use the canvas");
  viewer.focusEvent(5, "primary");
  check(!byId("audit").hidden && byId("details").textContent.includes("Earlier action"), "Evidence link is missing");
  check(byId("details").textContent.includes("Agrees with prediction"), "Recorded experiment result is missing");
  viewer.show("compare");
  check(!byId("comparison").hidden && byId("compare-columns").children.length === 2, "Comparison failed");
  check(byId("compare-columns").textContent.includes("Memory withheld"), "Comparison mixed up run labels");
  check(byId("compare-changes").textContent.includes("avoid puddle → take shortcut"), "Comparison omitted a changed action");
  viewer.focusEvent(6, "reference");
  check(byId("filter-source").value === "reference", "Selected event opened in the wrong run");
  check(byId("details").textContent.includes("take shortcut"), "Comparison did not open the correct event");
  check(byId("details").textContent.includes("Calibrated activation projection"), "Observed model measurements did not render");
  return "passed";
}

function checkFollow(first, next, elementIds) {
  for (const id of elementIds) ids.set(id, new TestElement(id));
  const view = new FollowViewer();
  if (!byId("player").hidden || byId("follow-pane").hidden) throw new Error("Follow mode did not open separately");
  view.update(first);
  if (byId("run-mode").textContent !== "Local policy test") throw new Error("Follow state mislabeled local choice");
  if (!byId("follow-status").textContent.startsWith("In progress")) throw new Error("Partial checkpoint looked complete");
  const before = draws.fills;
  view.update(next);
  if (draws.fills <= before) throw new Error("Newly committed decision never reached the stage");
  if (!byId("follow-detail").textContent.includes("Local policy choice")) throw new Error("Missing decision provenance");
  if (!byId("follow-status").textContent.includes("7 committed events")) throw new Error("Wrong checkpoint event counter");
  return "passed";
}
