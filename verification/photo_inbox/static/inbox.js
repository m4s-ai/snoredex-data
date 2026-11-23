"use strict";

const field = (id) => document.getElementById(id);
const DATE = new Intl.DateTimeFormat("de-DE", {dateStyle: "medium", timeStyle: "short"});

function message(text, kind) {
  const line = document.createElement("li");
  line.className = kind || "";
  line.textContent = text;
  return line;
}

// one file per request, so each photo is its own job and the service holds one file at a time
function send(file, onProgress) {
  return new Promise((resolve) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/uploads");
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.upload.onprogress = (event) => event.lengthComputable && onProgress(event.loaded / event.total);
    request.onload = () => {
      let reply = {};
      try { reply = JSON.parse(request.responseText); } catch { /* waitress answers 413 itself */ }
      if (request.status === 413) reply.error = "Bitte wähle ein Foto bis 200 MB.";
      resolve({ok: request.status < 300, reply, status: request.status});
    };
    request.onerror = () => resolve({ok: false, reply: {error: "Keine Verbindung. Ist das Handy im Heim-WLAN?"}});
    request.send(file);
  });
}

async function upload(event) {
  event.preventDefault();
  const files = [...field("photos").files];
  const button = event.target.querySelector("button");
  button.disabled = true;
  field("transfers").replaceChildren();
  for (const file of files) {
    const line = field("transfers").appendChild(message(`${file.name}: wird hochgeladen …`));
    const result = await send(file, (part) => { line.textContent = `${file.name}: ${Math.round(part * 100)} %`; });
    if (!result.ok) {
      line.className = "error";
      line.textContent = `${file.name}: ${result.reply.error || `Fehler (HTTP ${result.status})`}`;
    } else {
      line.className = "ok";
      line.textContent = `${file.name}: ${result.reply.existing ? "schon vorhanden" : "neu im Eingang"}`;
    }
  }
  button.disabled = false;
  event.target.reset();
  await showJobs();
}

function jobItem(job) {
  const item = field("job-template").content.firstElementChild.cloneNode(true);
  item.dataset.job = job.id;
  item.querySelector(".photo").href = `/jobs/${job.id}/preview?size=1600`;
  const image = item.querySelector("img");
  image.alt = `Foto ${job.file}, Auftrag ${job.id.slice(0, 8)}`;
  image.onerror = () => image.replaceWith("Keine Vorschau für dieses Foto.");
  image.src = `/jobs/${job.id}/preview?size=400`;
  item.querySelector(".when").textContent = `${job.file.endsWith(".dng") ? "DNG" : "JPEG"} · ${DATE.format(new Date(job.receivedAt))}`;
  setState(item, job);
  const form = item.querySelector("form");
  form.specimen.value = job.specimenHint || "";
  form.note.value = job.note || "";
  form.addEventListener("submit", (event) => describe(event, item));
  return item;
}

function setState(item, job) {
  item.dataset.described = job.described;
  const state = item.querySelector(".state");
  state.textContent = job.described ? "beschrieben" : "ohne Angabe";
  state.className = "state " + (job.described ? "ok" : "open");
}

async function describe(event, item) {
  event.preventDefault();
  const form = event.target;
  const saved = form.querySelector(".saved");
  const body = JSON.stringify({specimen: form.specimen.value, note: form.note.value});
  try {
    const response = await fetch(`/jobs/${item.dataset.job}`, {method: "POST", headers: {"Content-Type": "application/json"}, body});
    const reply = await response.json();
    if (!response.ok) throw new Error(reply.error);
    setState(item, reply);
    saved.className = "saved ok";
    saved.textContent = "Gespeichert.";
  } catch (error) {
    saved.className = "saved error";
    saved.textContent = error.message || "Speichern fehlgeschlagen.";
  }
}

async function showJobs() {
  try {
    const reply = await (await fetch("/jobs")).json();
    const open = field("open-only").checked;
    const jobs = reply.jobs.filter((job) => !open || !job.described);
    field("jobs").replaceChildren(...jobs.map(jobItem));
    field("jobs-status").textContent = jobs.length ? "" : "Keine Fotos.";
  } catch {
    field("jobs-status").textContent = "Die Liste konnte nicht geladen werden.";
  }
}

field("upload").addEventListener("submit", upload);
field("open-only").addEventListener("change", showJobs);
showJobs();
