"use strict";
(() => {
  const replay = window.RIALTO_REPLAYS;
  const roles = ["reporter", "producer", "camera"];
  const names = ["Phil", "Rita", "Larry"];
  const titles = {
    play_piano:"Play piano at the ballroom", go_to_party:"Attend the party",
    ask_Rita_to_dance:"Offer Rita a dance", wait_at_Rialto:"Wait at the Rialto",
    go_to_bed:"Go to bed", sit_at_depot:"Sit on the depot bench",
    call_sister:"Call his sister", sleep_at_terminal:"Sleep at the terminal",
    wait_for_morning:"Wait up for morning", wire_deposit:"Wire the missing fares",
    transmit_interview:"Take the regional line", go_dancing:"Go dancing",
    go_to_party_for_work:"Cover the party", take_evening_off:"Take the night off",
    deliver_reel:"Deliver the reel", screen_party:"Screen the party footage", go_home:"Go home"
  };
  const premises = {
    hypothesis:"Phil began this take with a supplied theory about reenacting the movie.",
    library:"On his first afternoon Phil saw a library display about a weatherman who relived February 2.",
    uncued:"Phil’s name and prior coach trip were carried in. His starting instructions left the film unnamed."
  };
  const el = id => document.getElementById(id);
  const make = (kind, text) => {
    const node = document.createElement(kind);
    node.textContent = text;
    return node;
  };
  function option(value, label) {
    const node = make("option", label);
    node.value = value;
    return node;
  }
  const sources = Object.keys(replay.sources);
  el("run").replaceChildren(...sources.map(run => option(run, run.replace("-", " · "))));
  el("day").replaceChildren(...[1, 2, 3].map(day => option(String(day), String(day))));
  const qs = new URLSearchParams(location.search);
  el("run").value = sources.includes(qs.get("run")) ? qs.get("run") : "721-hypothesis";
  el("day").value = ["1", "2", "3"].includes(qs.get("day")) ? qs.get("day") : "1";
  let checkpoint;

  function selected() { return roles.map(role => el(role).value); }
  function render() {
    const actions = selected();
    const row = checkpoint.branches[actions.join("|")];
    const unchanged = actions.every((action, i) => checkpoint.recorded[i] === action);
    el("status").textContent = unchanged ? "Recorded performance" : "Alternate choices · rule replay";
    for (const [i, role] of roles.entries()) el(role + "-effect").textContent = checkpoint.texts[row[i]];
    el("reel").textContent = row[3] ? "Her mother’s interview reaches her in Pittsburgh tonight." :
      "No new interview reaches Pittsburgh tonight.";
    el("party").textContent = row[4] ? "Phil and Rita dance through one song." :
      row[5] ? "Phil and Rita both attend the party. They do not dance together." :
      "There is no shared ballroom scene.";
    el("calendar").textContent = row[6] ? "Wednesday" : "Tuesday";
    el("restore").disabled = unchanged;
  }
  function openDay() {
    const run = el("run").value;
    const day = Number(el("day").value);
    checkpoint = replay.days.find(entry => entry.run === run && entry.day === day);
    el("premise").textContent = premises[run.split("-")[1]];
    el("source").href = "../runs/" + run + "/take.json";
    el("scope").textContent = Object.keys(checkpoint.branches).length + " legal joint evenings at this checkpoint. Only the recorded performance was sampled from the actors.";
    el("afternoon").replaceChildren(...checkpoint.afternoon.map((effect, i) => {
      const card = make("div", "");
      card.append(make("strong", names[i]), make("p", effect));
      return card;
    }));
    el("actors").replaceChildren(...roles.map((role, i) => {
      const card = make("div", "");
      const label = make("label", names[i]);
      const input = make("select", "");
      input.id = role;
      input.replaceChildren(...checkpoint.choices[role].map(choice => option(choice, titles[choice])));
      input.value = checkpoint.recorded[i];
      input.addEventListener("change", render);
      label.append(input);
      const effect = make("p", "");
      effect.id = role + "-effect";
      card.append(label, effect);
      return card;
    }));
    el("dance").disabled = !checkpoint.choices.reporter.includes("ask_Rita_to_dance");
    el("dance").title = el("dance").disabled ? "Phil is already in Pittsburgh." : "";
    render();
  }
  el("dance").addEventListener("click", () => {
    el("reporter").value = "ask_Rita_to_dance";
    el("producer").value = "go_dancing";
    render();
  });
  el("patch").addEventListener("click", () => {
    el("producer").value = "transmit_interview";
    render();
  });
  el("restore").addEventListener("click", () => {
    roles.forEach((role, i) => { el(role).value = checkpoint.recorded[i]; });
    render();
  });
  for (const id of ["run", "day"]) el(id).addEventListener("change", openDay);
  openDay();
})();
