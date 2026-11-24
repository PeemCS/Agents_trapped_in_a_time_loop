"use strict";

const film = document.getElementById("film");
const startButton = document.getElementById("start");
const viewing = document.getElementById("viewing");
const response = document.getElementById("response");
const form = response.querySelector("form");
const statusLine = document.getElementById("status");
const factualFields = Array.from(form.querySelectorAll("textarea[required]"));

function openResponse() {
  film.pause();
  viewing.hidden = true;
  response.hidden = false;
  document.getElementById("after").focus();
}

function exportAnswers() {
  for (const field of factualFields) {
    field.setCustomValidity(field.value.trim() ? "" : "Enter an answer or write “Unsure”.");
  }
  if (!form.reportValidity()) return;

  const clarity = document.getElementById("clarity").value;
  const data = {
    format: "eight-bars-audience-response-v1",
    film: {
      title: "Eight Bars",
      sha256: "423114d7370078a35fbb61ebdb1b4ab806ce03207977377677fef20bc0fbe243"
    },
    factual: Object.fromEntries(factualFields.map(field => [field.id, field.value.trim()])),
    optional: {
      moment: document.getElementById("moment").value.trim() || null,
      clarity_1_to_5: clarity ? Number(clarity) : null
    }
  };
  const blob = new Blob([JSON.stringify(data, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "eight-bars-response.json";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30000);
  statusLine.textContent = "Download started. You can clear the card for the next viewer.";
}

function clearCard() {
  form.reset();
  for (const field of factualFields) field.setCustomValidity("");
  statusLine.textContent = "";
  film.pause();
  if (film.readyState >= 1) film.currentTime = 0;
  response.hidden = true;
  film.inert = true;
  startButton.hidden = false;
  viewing.hidden = false;
  startButton.focus();
}

film.inert = true;
startButton.hidden = false;
startButton.addEventListener("click", () => {
  film.inert = false;
  film.play().catch(() => {
    startButton.hidden = true;
    film.focus();
  });
});
film.addEventListener("play", () => {
  film.inert = false;
  startButton.hidden = true;
});
film.addEventListener("ended", openResponse);
document.getElementById("watched").addEventListener("click", openResponse);
document.getElementById("export").addEventListener("click", exportAnswers);
document.getElementById("clear").addEventListener("click", clearCard);
form.addEventListener("submit", event => event.preventDefault());
form.addEventListener("input", event => {
  if (event.target instanceof HTMLTextAreaElement) event.target.setCustomValidity("");
  statusLine.textContent = "";
});
window.addEventListener("pageshow", event => {
  if (event.persisted) clearCard();
});
