"use strict";

const field = (id) => document.getElementById(id);
const DATE = new Intl.DateTimeFormat("de-DE", {dateStyle: "medium", timeStyle: "short"});
const DAY = new Intl.DateTimeFormat("de-DE", {dateStyle: "medium"});
const STAGE_NAMES = {none: "kein eigenes Foto", assigned: "hochgeladen, zugeordnet", filed: "verarbeitet",
                     online: "online", ready: "bereit für Instagram", posted: "gepostet"};
const state = {overview: null, labels: new Map(), catalogue: false, canPost: false, accounts: []};

function message(text, kind) {
  const line = document.createElement("li");
  line.className = kind || "";
  line.textContent = text;
  return line;
}

function link(href, text) {
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.textContent = text;
  if (!href.startsWith("#")) { anchor.target = "_blank"; anchor.rel = "noopener noreferrer"; }
  return anchor;
}

async function call(url, options) {
  const response = await fetch(url, options);
  const reply = await response.json();
  if (!response.ok) throw new Error(reply.error || `Fehler (HTTP ${response.status})`);
  return reply;
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
  if (!files.length) {
    field("chosen").textContent = "Bitte zuerst Fotos auswählen.";
    return;
  }
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
  showChosen();
  await refresh();
}

function showChosen() {
  const count = field("photos").files.length;
  field("chosen").textContent = count ? `${count} ${count === 1 ? "Foto" : "Fotos"} gewählt.` : "Noch keine Fotos gewählt.";
}

// tabs after the WAI-ARIA tabs pattern: automatic activation, arrows, Home and End, one hash per tab.
// The hash names the tab (#fotos), never the panel's id, so the browser neither scrolls nor focuses it.
const TABS = [...document.querySelectorAll('[role="tab"]')];
const tabName = (tab) => tab.getAttribute("aria-controls").replace("panel-", "");

function activate(name, focus) {
  const tab = TABS.find((entry) => tabName(entry) === name) || TABS[0];
  for (const entry of TABS) {
    const selected = entry === tab;
    entry.setAttribute("aria-selected", String(selected));
    entry.tabIndex = selected ? 0 : -1;
    field(entry.getAttribute("aria-controls")).hidden = !selected;
  }
  if (focus) tab.focus();
}

function follow() {
  const target = decodeURIComponent(location.hash.slice(1));
  if (target.startsWith("job-")) {
    activate("fotos");
    const job = field(target);
    if (job) job.scrollIntoView({block: "start"});
    return;
  }
  activate(target || "hochladen");
  window.scrollTo(0, 0);
}

function onTabKey(event) {
  const index = TABS.indexOf(event.target);
  const moves = {ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: TABS.length - 1};
  if (!(event.key in moves)) return;
  event.preventDefault();
  const next = TABS[(moves[event.key] + TABS.length) % TABS.length];
  history.replaceState(null, "", "#" + tabName(next));
  activate(tabName(next), true);
}

function showCount(id, count) {
  const badge = field(id);
  badge.hidden = !count;
  badge.textContent = count;
}

function itemLabel(itemId) {
  const row = state.overview && state.overview.rows.find((entry) => entry.itemId === itemId);
  return row ? row.label : itemId || "";
}

function jobItem(job) {
  const item = field("job-template").content.firstElementChild.cloneNode(true);
  item.dataset.job = job.id;
  item.id = `job-${job.id}`;
  item.querySelector(".photo").href = `/jobs/${job.id}/preview?size=1600`;
  const image = item.querySelector("img");
  image.alt = `Foto ${job.file}, Auftrag ${job.id.slice(0, 8)}`;
  image.onerror = () => image.replaceWith("Keine Vorschau für dieses Foto.");
  image.src = `/jobs/${job.id}/preview?size=400`;
  item.querySelector(".when").textContent = `${job.file.endsWith(".dng") ? "DNG" : "JPEG"} · ${DATE.format(new Date(job.receivedAt))}`;
  setState(item, job);
  const form = item.querySelector("form");
  form.specimen.value = job.specimenHint || "";
  form.item.value = itemLabel(job.itemId);
  form.note.value = job.note || "";
  form.addEventListener("submit", (event) => describe(event, item));
  const remove = item.querySelector(".delete");
  remove.hidden = !state.catalogue || Boolean(job.filedAs);
  remove.addEventListener("click", () => toTrash(item));
  const open = item.querySelector(".corners-open");
  resetCorners(item, job);
  open.addEventListener("click", () => toggleCorners(item, open));
  item.querySelector(".number-confirm").onclick = () => confirmNumber(item);
  showNumber(item, job);
  item.querySelector(".intake-start").onclick = () => startIntake(item);
  showIntake(item, job);
  return item;
}

// --- intake run (#659): filed, merged, published and linked without an agent ---

const STEP_NAMES = {intake: "Übernahme", merge: "Merge", publish: "Veröffentlichen", alias: "Kurzlink",
                    "alias-pr": "Kurzlink eintragen"};

function intakeText(intake) {
  const run = intake.run || {};
  if (run.status === "queued") return "Übernahme wartet auf ihren Lauf.";
  if (run.status === "running") return `Übernahme läuft: ${STEP_NAMES[run.step] || run.step}.`;
  if (run.status === "done") return `Übernommen als ${run.specimen}, veröffentlicht, Kurzlink ${run.alias}.`;
  if (run.status === "failed") return `Übernahme angehalten bei ${STEP_NAMES[run.step] || run.step}: ${run.error}`;
  return intake.blocked ? `Noch nicht bereit: ${intake.blocked}` : "Bereit zur Übernahme, sonst nachts automatisch.";
}

function showIntake(item, job) {
  const box = item.querySelector(".intake");
  box.hidden = !job.intake || (Boolean(job.filedAs) && !job.intake.run);
  if (box.hidden) return;
  const status = (job.intake.run || {}).status;
  box.querySelector(".intake-status").textContent = intakeText(job.intake);
  box.querySelector(".intake-status").className = `intake-status ${status === "failed" ? "error" : status === "done" ? "ok" : ""}`;
  box.querySelector(".intake-start").hidden = Boolean(job.intake.blocked) || ["queued", "running", "done"].includes(status);
  box.querySelector(".intake-start").textContent = status === "failed" ? "Erneut versuchen" : "Übernehmen";
}

async function startIntake(item) {
  try {
    showIntake(item, await call(`/jobs/${item.dataset.job}/intake`, {method: "POST"}));
  } catch (error) {
    item.querySelector(".intake-status").textContent = error.message;
  }
}

// --- number check (#658): what Tesseract read against the printing, a guard only ---

function numberText(check, confirmed) {
  const read = check.read.join(", ");
  if (check.result === "match") return `Nummer gelesen: ${check.expected}. Passt zum Druck.`;
  if (check.result === "unreadable") return `Nummer nicht lesbar${read ? ` (gelesen: ${read})` : ""}. Das hält nichts auf.`;
  if (check.result === "unavailable") return "Nummernprüfung nicht verfügbar (kein Tesseract). Das hält nichts auf.";
  return confirmed ? `Gelesen ${read}, erwartet ${check.expected}: von dir als richtig bestätigt.`
    : `Nummer passt nicht: gelesen ${read}, erwartet ${check.expected}. Prüfe die Zuordnung oder bestätige sie.`;
}

function showNumber(item, job) {
  const box = item.querySelector(".number");
  const check = !job.filedAs && job.numberCheck && job.numberCheck.itemId === job.itemId ? job.numberCheck : null;
  box.hidden = !check;
  if (!check) return;
  const pending = check.result === "mismatch" && !job.numberConfirmedAt;
  const status = box.querySelector(".number-status");
  status.textContent = numberText(check, Boolean(job.numberConfirmedAt));
  status.className = `number-status ${pending ? "error" : check.result === "match" ? "ok" : ""}`;
  box.querySelector(".number-confirm").hidden = !pending;
}

async function confirmNumber(item) {
  if (!confirm("Die gelesene Nummer passt nicht zum Druck. Ist die Zuordnung trotzdem richtig?")) return;
  try {
    showNumber(item, await call(`/jobs/${item.dataset.job}/number`, {method: "POST"}));
  } catch (error) {
    item.querySelector(".number-status").textContent = error.message;
  }
}

// --- card corners (#657): suggested, dragged on the phone, approved for intake ---

// another printing drops the approval on the server; the editor starts over from the next suggestion
function resetCorners(item, job) {
  const open = item.querySelector(".corners-open");
  open.hidden = !job.itemId || Boolean(job.filedAs);
  open.textContent = job.corners ? "Ecken freigegeben · prüfen" : "Ecken festlegen";
  if (job.corners) return;
  const panel = item.querySelector(".corners");
  panel.hidden = true;
  delete panel.dataset.ready;
  panel.querySelectorAll(".handle").forEach((handle) => handle.remove());
  open.setAttribute("aria-expanded", "false");
}

const CORNER_NAMES = ["oben links", "oben rechts", "unten rechts", "unten links"];

async function toggleCorners(item, open) {
  const panel = item.querySelector(".corners");
  const opening = panel.hidden;
  panel.hidden = !opening;
  open.setAttribute("aria-expanded", String(opening));
  if (!opening || panel.dataset.ready) return;
  const status = panel.querySelector(".corners-status");
  status.textContent = "Suche die Karte …";
  try {
    const found = await call(`/jobs/${item.dataset.job}/corners`);
    panel.dataset.ready = "1";
    cornerEditor(item, panel, found);
  } catch (error) {
    status.textContent = error.message;
  }
}

function startQuad(found) {
  // a copy: dragging must never change the stored suggestion that "Vorschlag wiederherstellen" returns to
  if (found.approved) return found.approved.map((point) => [...point]);
  if (found.candidates.length) return found.candidates[0].map((point) => [...point]);
  const [width, height] = found.size;  // nothing found: a card-shaped frame in the middle to drag from
  const w = width * 0.5, h = w * 88 / 63, x = (width - w) / 2, y = Math.max(0, (height - h) / 2);
  return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]].map((p) => p.map(Math.round));
}

function cornerEditor(item, panel, found) {
  const job = item.dataset.job;
  const [width, height] = found.size;
  const editor = {quad: startQuad(found), handles: [], panel, job, width, height};
  const photo = panel.querySelector(".frame-photo");
  photo.src = `/jobs/${job}/preview?size=1600`;
  photo.alt = "Foto mit dem Rahmen der Karte";
  panel.querySelector(".frame").setAttribute("viewBox", `0 0 ${width} ${height}`);
  panel.querySelector(".loupe").style.backgroundImage = `url("/jobs/${job}/preview?size=1600")`;
  const stage = panel.querySelector(".stage");
  editor.handles = CORNER_NAMES.map((name, index) => {
    const handle = Object.assign(document.createElement("button"), {type: "button", className: "handle"});
    handle.addEventListener("pointerdown", (event) => dragCorner(event, editor, index));
    handle.addEventListener("keydown", (event) => nudgeCorner(event, editor, index));
    handle.addEventListener("focus", () => showLoupe(editor, index));
    handle.addEventListener("blur", () => { panel.querySelector(".loupe").hidden = true; });
    stage.append(handle);
    return handle;
  });
  showChoices(editor, found);
  cornerStatus(editor, found);
  // assigned, not added: the editor is built again after another printing resets it
  panel.querySelector(".approve").onclick = () => approveCorners(item, editor);
  panel.querySelector(".reset").onclick = () => {
    editor.quad = startQuad({...found, approved: null});
    drawQuad(editor);
    refreshCover(editor);
  };
  drawQuad(editor);
  refreshCover(editor);
}

function cornerStatus(editor, found) {
  const count = found.candidates.length;
  const text = found.approved ? "Freigegebene Ecken." : count === 1 ? "Karte erkannt. Prüfe die Ecken und gib sie frei."
    : count > 1 ? `${count} Karten erkannt. Tippe die richtige an.` : "Keine Karte erkannt. Ziehe die Ecken auf die Karte.";
  editor.panel.querySelector(".corners-status").textContent = text;
}

function showChoices(editor, found) {
  const choices = editor.panel.querySelector(".choices");
  choices.hidden = found.candidates.length < 2;
  choices.replaceChildren(...(choices.hidden ? [] : found.candidates).map((quad, index) => {
    const button = Object.assign(document.createElement("button"), {type: "button", className: "primary", textContent: `Karte ${index + 1}`});
    button.addEventListener("click", () => { editor.quad = quad.map((p) => [...p]); drawQuad(editor); refreshCover(editor); });
    return button;
  }));
}

function drawQuad(editor) {
  editor.panel.querySelector(".frame polygon").setAttribute("points", editor.quad.map((p) => p.join(",")).join(" "));
  editor.handles.forEach((handle, index) => {
    const [x, y] = editor.quad[index];
    handle.style.left = `${(100 * x) / editor.width}%`;
    handle.style.top = `${(100 * y) / editor.height}%`;
    handle.setAttribute("aria-label", `Ecke ${CORNER_NAMES[index]}: ${x}, ${y}`);
  });
}

function moveCorner(editor, index, x, y) {
  editor.quad[index] = [Math.round(Math.min(Math.max(x, 0), editor.width - 1)),
                        Math.round(Math.min(Math.max(y, 0), editor.height - 1))];
  drawQuad(editor);
  showLoupe(editor, index);
}

function dragCorner(event, editor, index) {
  event.preventDefault();
  const handle = editor.handles[index];
  const photo = editor.panel.querySelector(".frame-photo");
  handle.setPointerCapture(event.pointerId);
  const follow = (move) => {
    const box = photo.getBoundingClientRect();
    moveCorner(editor, index, ((move.clientX - box.left) / box.width) * editor.width,
               ((move.clientY - box.top) / box.height) * editor.height);
  };
  const stop = () => {
    handle.removeEventListener("pointermove", follow);
    editor.panel.querySelector(".loupe").hidden = true;
    refreshCover(editor);
  };
  handle.addEventListener("pointermove", follow);
  handle.addEventListener("pointerup", stop, {once: true});
  handle.addEventListener("pointercancel", stop, {once: true});
}

function nudgeCorner(event, editor, index) {
  const steps = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
  if (!steps) return;
  event.preventDefault();
  const size = event.shiftKey ? 40 : 4;
  const [x, y] = editor.quad[index];
  moveCorner(editor, index, x + steps[0] * size, y + steps[1] * size);
  clearTimeout(editor.coverTimer);
  editor.coverTimer = setTimeout(() => refreshCover(editor), 600);
}

// a magnified view of the corner, so a fingertip does not hide what it places
function showLoupe(editor, index) {
  const loupe = editor.panel.querySelector(".loupe");
  const [x, y] = editor.quad[index];
  const zoom = 4;
  const box = editor.panel.querySelector(".frame-photo").getBoundingClientRect();
  const scale = (box.width * zoom) / editor.width;
  loupe.hidden = false;
  loupe.style.backgroundSize = `${box.width * zoom}px ${box.height * zoom}px`;
  loupe.style.backgroundPosition = `${60 - x * scale}px ${60 - y * scale}px`;
  loupe.classList.toggle("right", x < editor.width / 2);
}

function refreshCover(editor) {
  const image = editor.panel.querySelector(".cover");
  image.hidden = false;
  image.onerror = () => {
    image.hidden = true;
    editor.panel.querySelector(".corners-status").textContent = "Aus diesen Ecken entsteht kein Titelbild. Bitte prüfen.";
  };
  image.src = `/jobs/${editor.job}/cover?c=${editor.quad.flat().join(",")}`;
}

async function approveCorners(item, editor) {
  const status = editor.panel.querySelector(".corners-status");
  try {
    const job = await call(`/jobs/${editor.job}/corners`, {method: "POST", headers: {"Content-Type": "application/json"},
                                                              body: JSON.stringify({corners: editor.quad})});
    status.textContent = `Ecken freigegeben am ${DATE.format(new Date(job.cornersApprovedAt))}.`;
    item.querySelector(".corners-open").textContent = "Ecken freigegeben · prüfen";
    showNumber(item, job);
  } catch (error) {
    status.textContent = error.message;
  }
}

function setState(item, job) {
  item.dataset.described = job.described;
  const label = job.filedAs ? `übernommen als ${job.filedAs}` : job.described ? "beschrieben" : "ohne Angabe";
  const badge = item.querySelector(".state");
  badge.textContent = label;
  badge.className = "state " + (job.described || job.filedAs ? "ok" : "open");
}

async function describe(event, item) {
  event.preventDefault();
  const form = event.target;
  const saved = form.querySelector(".saved");
  const typed = form.item.value.trim();
  const itemId = state.labels.get(typed) || typed;
  const body = JSON.stringify({specimen: form.specimen.value, note: form.note.value, itemId});
  try {
    const reply = await call(`/jobs/${item.dataset.job}`, {method: "POST", headers: {"Content-Type": "application/json"}, body});
    setState(item, reply);
    // a filed job keeps the catalogue's SPEC and printing, so show what was stored
    form.specimen.value = reply.specimenHint || "";
    form.item.value = itemLabel(reply.itemId);
    resetCorners(item, reply);
    showNumber(item, reply);
    saved.className = "saved ok";
    saved.textContent = "Gespeichert.";
    showOverview();
  } catch (error) {
    saved.className = "saved error";
    saved.textContent = error.message || "Speichern fehlgeschlagen.";
  }
}

async function toTrash(item) {
  if (!confirm("Dieses Foto in den Papierkorb legen? Dort lässt es sich 30 Tage lang wiederherstellen.")) return;
  try {
    await call(`/jobs/${item.dataset.job}`, {method: "DELETE"});
  } catch (error) {
    item.querySelector(".saved").className = "saved error";
    item.querySelector(".saved").textContent = error.message;
    return;
  }
  await refresh();
}

const JOB_VIEWS = {
  all: () => true,
  open: (job) => !job.described && !job.filedAs,
  unclassified: (job) => !job.itemId && !job.filedAs,
  filed: (job) => Boolean(job.filedAs),
};

async function showJobs() {
  try {
    const reply = await call("/jobs");
    state.catalogue = reply.catalogue;
    showCount("count-fotos", reply.jobs.filter(JOB_VIEWS.open).length);
    const jobs = reply.jobs.filter(JOB_VIEWS[field("job-view").value]);
    field("jobs").replaceChildren(...jobs.map(jobItem));
    field("jobs-status").textContent = jobs.length ? "" : "Keine Fotos.";
  } catch {
    field("jobs-status").textContent = "Die Liste konnte nicht geladen werden.";
  }
}

const STAGE_ORDER = Object.keys(STAGE_NAMES);
const hasOwnPhoto = (row) => STAGE_ORDER.indexOf(row.stage) >= STAGE_ORDER.indexOf("filed");
const VIEWS = {all: () => true, own: hasOwnPhoto, missing: (row) => !hasOwnPhoto(row)};

function rowItem(row) {
  const item = field("row-template").content.firstElementChild.cloneNode(true);
  item.dataset.item = row.itemId;
  item.dataset.stage = row.stage;
  const image = item.querySelector("img");
  if (row.preview) { image.src = row.preview; image.alt = `Karte ${row.label}`; } else { image.remove(); }
  item.querySelector(".badge").textContent = STAGE_NAMES[row.stage];
  item.querySelector(".badge").className = `badge stage-${row.stage}`;
  item.querySelector(".label").textContent = row.specimen ? `${row.label} · ${row.specimen}` : row.label;
  const links = [link(row.card, "Kartenseite")];
  if (row.shortUrl) links.push(link(row.shortUrl, "Kurzlink"));
  row.posts.forEach((post, index) => links.push(link(post, `Instagram ${index + 1}`)));
  row.jobs.forEach((job) => links.push(link(`#job-${job}`, `Foto ${job.slice(0, 8)}`)));
  item.querySelector(".links").replaceChildren(...links);
  return item;
}

function showCounts(rows) {
  const counts = STAGE_ORDER.map((stage) => {
    const line = message(`${STAGE_NAMES[stage]}: ${rows.filter((row) => row.stage === stage).length}`);
    line.dataset.stage = stage;
    return line;
  });
  field("stage-counts").replaceChildren(...counts);
}

function showRows() {
  if (!state.overview) return;
  const stage = field("stage").value;
  const words = field("search").value.toLowerCase().split(/\s+/).filter(Boolean);
  const rows = state.overview.rows.filter(VIEWS[field("view").value])
    .filter((row) => !stage || row.stage === stage)
    .filter((row) => words.every((word) => row.label.toLowerCase().includes(word)));
  field("rows").replaceChildren(...rows.map(rowItem));
  field("rows-status").textContent = `${rows.length} von ${state.overview.rows.length} Drucken`;
}

function showStats() {
  if (!state.overview) return;
  const key = field("group-by").value;
  const groups = new Map();
  for (const row of state.overview.rows) {
    const counts = groups.get(row[key]) || {all: 0, own: 0, online: 0, posted: 0};
    counts.all += 1;
    counts.own += hasOwnPhoto(row) ? 1 : 0;
    counts.online += STAGE_ORDER.indexOf(row.stage) >= STAGE_ORDER.indexOf("online") ? 1 : 0;
    counts.posted += row.stage === "posted" ? 1 : 0;
    groups.set(row[key], counts);
  }
  const head = document.createElement("tr");
  for (const title of [key === "set" ? "Set" : "Sprache", "Drucke", "mit Owner-Foto", "online", "gepostet"]) {
    head.appendChild(document.createElement("th")).textContent = title;
  }
  const lines = [...groups].sort((a, b) => b[1].all - a[1].all).map(([name, counts]) => {
    const line = document.createElement("tr");
    for (const value of [name, counts.all, counts.own, counts.online, counts.posted]) {
      line.appendChild(document.createElement("td")).textContent = value;
    }
    return line;
  });
  field("stats").replaceChildren(head, ...lines);
}

async function showOverview() {
  try {
    state.overview = await call("/overview");
  } catch (error) {
    field("overview-status").textContent = error.message;
    return;
  }
  const {dataAsOf, siteError, rows} = state.overview;
  state.labels = new Map(rows.map((row) => [row.label, row.itemId]));
  field("items").replaceChildren(...rows.map((row) => Object.assign(document.createElement("option"), {value: row.label})));
  field("overview-status").textContent = `Datenstand ${DAY.format(new Date(dataAsOf))}.` + (siteError ? ` ${siteError}` : "");
  showCounts(rows);
  showRows();
  showStats();
}

function trashItem(job, keepDays) {
  const item = field("trash-template").content.firstElementChild.cloneNode(true);
  item.dataset.job = job.id;
  const image = item.querySelector("img");
  image.alt = `Gelöschtes Foto ${job.file}, Auftrag ${job.id.slice(0, 8)}`;
  image.onerror = () => image.replaceWith("Keine Vorschau für dieses Foto.");
  image.src = `/trash/${job.id}/preview?size=400`;
  const end = new Date(new Date(job.deletedAt).getTime() + keepDays * 86400000);
  // intake may file a job after it was trashed: then it only goes back, never away
  item.querySelector(".when").textContent = job.filedAs
    ? `${job.note || job.file} · übernommen als ${job.filedAs}, bitte wiederherstellen`
    : `${job.note || job.file} · endgültig gelöscht am ${DAY.format(end)}`;
  item.querySelector(".purge").hidden = Boolean(job.filedAs);
  item.querySelector(".restore").addEventListener("click", () => fromTrash(job.id, "POST", "restore"));
  item.querySelector(".purge").addEventListener("click", () => {
    if (confirm("Dieses Foto endgültig löschen? Das lässt sich nicht rückgängig machen.")) fromTrash(job.id, "DELETE", "");
  });
  return item;
}

async function fromTrash(jobId, method, action) {
  try {
    await call(`/trash/${jobId}${action ? "/" + action : ""}`, {method});
  } catch (error) {
    field("trash-status").textContent = error.message;
    return;
  }
  await refresh();
}

async function showTrash() {
  try {
    const reply = await call("/trash");
    showCount("count-papierkorb", reply.jobs.length);
    field("trash").replaceChildren(...reply.jobs.map((job) => trashItem(job, reply.keepDays)));
    field("trash-status").textContent = reply.jobs.length ? "" : "Der Papierkorb ist leer.";
  } catch {
    field("trash-status").textContent = "Der Papierkorb konnte nicht geladen werden.";
  }
}

// the exporter's open points, in the page's language
const OPEN_POINTS = {"Owner review": "Abnahme durch dich",
                     "Register a permanent short link for this card": "Kurzlink anlegen",
                     "Verify the public short link and matching preview": "Kurzlink und Vorschaubild öffnen und prüfen"};
const POST_VIEWS = {ready: (post) => post.stage === "ready", posted: (post) => post.stage === "posted", all: () => true};

function postItem(post) {
  const item = field("post-template").content.firstElementChild.cloneNode(true);
  item.dataset.item = post.itemId;
  item.querySelector(".badge").textContent = STAGE_NAMES[post.stage];
  item.querySelector(".badge").className = `badge stage-${post.stage}`;
  item.querySelector(".label").textContent = `${post.label} · ${post.draftSpecimen}`;
  const links = [link(post.card, "Kartenseite")];
  if (post.shortUrl) links.push(link(post.shortUrl, "Kurzlink"));
  post.posts.forEach((url, index) => links.push(link(url, `Instagram ${index + 1}`)));
  showOrder(item, post);
  if (post.error) {
    item.querySelector(".photo").remove();
    item.querySelectorAll("label").forEach((label) => label.remove());
    item.querySelector(".todo").className = "todo error";
    item.querySelector(".todo").textContent = post.error;
  } else {
    item.querySelector(".photo").href = post.image;
    const image = item.querySelector("img");
    image.src = post.image;
    image.alt = `Postbild: ${post.alt}`;
    item.querySelector(".caption").value = post.caption;
    item.querySelector(".alt").value = post.alt;
    item.querySelector(".todo").textContent = post.order ? "So geht der Post raus: eingefroren bei der Freigabe."
      : "Vor dem Posten: " + post.open.map((point) => OPEN_POINTS[point] || point).join(" · ");
    const save = link(post.image, "Bild laden");
    save.download = `${post.draftSpecimen}-post.jpg`;
    links.push(save);
    item.querySelector(".slides").replaceChildren(...post.slides.slice(1).map(slideItem));
  }
  item.querySelector(".links").replaceChildren(...links);
  return item;
}

function slideItem(slide, index) {
  const item = field("slide-template").content.firstElementChild.cloneNode(true);
  item.querySelector(".photo").href = slide.image;
  item.querySelector("img").src = slide.image;
  item.querySelector("img").alt = `Bild ${index + 2}: ${slide.alt}`;
  item.querySelector("textarea").value = slide.alt;
  return item;
}

const TARGET_STATES = {pending: "wartet", queued: "beim Uploader", container_created: "wird verarbeitet", processing: "wird verarbeitet",
                       publishing: "wird veröffentlicht", published: "veröffentlicht", failed: "gescheitert"};
const PLATFORM_NAMES = {instagram: "Instagram", facebook_page: "Facebook-Seite", threads: "Threads"};

function accountName(id) {
  const account = state.accounts.find((entry) => entry.id === id);
  return account ? `${PLATFORM_NAMES[account.platform] || account.platform} ${account.displayName || ""}`.trim() : id;
}

// an order shows each target's state; without one, a post that may be sent gets the send form
function showOrder(item, post) {
  const sent = item.querySelector(".sent");
  if (post.order) {
    const targets = Object.entries(post.order.targets);
    item.querySelector(".targets").replaceChildren(...targets.map(([id, target]) => targetLine(post, id, target, sent)));
    const waiting = targets.every(([, target]) => target.status === "pending" && !target.tried);
    const due = new Date(post.order.dueAt);
    if (waiting && due > new Date()) {
      sent.textContent = `Eingeplant für ${DATE.format(due)}.`;
      const cancel = item.querySelector(".cancel");
      cancel.hidden = false;
      cancel.addEventListener("click", () => cancelOrder(post, sent));
    }
    return;
  }
  if (!state.canPost || post.error || !state.accounts.length) return;
  const form = item.querySelector(".send");
  form.hidden = false;
  form.querySelector(".accounts").replaceChildren(...state.accounts.map((account) => {
    const label = document.createElement("label");
    label.className = "check";
    label.append(Object.assign(document.createElement("input"), {type: "checkbox", name: "account", value: account.id, checked: true}),
                 accountName(account.id));
    return label;
  }));
  const button = form.querySelector("button");
  form.elements.at.addEventListener("input", () => { button.textContent = form.elements.at.value ? "Einplanen" : "Jetzt posten"; });
  form.addEventListener("submit", (event) => sendOrder(event, post, sent));
}

function targetLine(post, id, target, sent) {
  const line = message(`${accountName(id)}: ${TARGET_STATES[target.status] || target.status}`,
                       target.status === "failed" ? "error" : "");
  if (target.permalink) line.append(" · ", link(target.permalink, "Post öffnen"));
  const reason = target.error || target.problem;
  if (reason) line.append(` · ${reason}`);
  if (target.status === "failed") {
    const again = Object.assign(document.createElement("button"), {type: "button", className: "primary", textContent: "Erneut senden"});
    again.addEventListener("click", () => act(`/posts/${post.draftSpecimen}/retry`, {account: id}, sent));
    line.append(" ", again);
  }
  return line;
}

async function act(url, body, sent, method = "POST") {
  try {
    await call(url, {method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    await showPosts();
  } catch (error) {
    sent.textContent = error.message;
  }
}

function sendOrder(event, post, sent) {
  event.preventDefault();
  const form = event.target;
  const accounts = [...form.querySelectorAll("input[name=account]:checked")].map((box) => box.value);
  const at = form.elements.at.value ? new Date(form.elements.at.value).toISOString() : null;
  const when = at ? `am ${DATE.format(new Date(at))}` : "sofort";
  if (!accounts.length) { sent.textContent = "Wähle mindestens ein Konto."; return; }
  if (!confirm(`${post.label} ${when} auf ${accounts.map(accountName).join(", ")} posten? Ein Post lässt sich nicht zurücknehmen.`)) return;
  form.querySelector("button").disabled = true;
  act(`/posts/${post.draftSpecimen}/order`, {draft: post.draft, accounts, at}, sent);
}

function cancelOrder(post, sent) {
  if (confirm("Die Einplanung zurücknehmen? Der Entwurf bleibt.")) act(`/posts/${post.draftSpecimen}/order`, {}, sent, "DELETE");
}

async function loadAccounts() {
  try {
    state.accounts = (await call("/accounts")).accounts;
  } catch {
    state.accounts = [];
  }
}

async function showPosts() {
  try {
    const {posts, canPost} = await call("/posts");
    if (canPost && !state.accounts.length) await loadAccounts();  // again after a failed attempt
    state.canPost = canPost;
    showCount("count-posts", posts.filter(POST_VIEWS.ready).length);
    const shown = posts.filter(POST_VIEWS[field("post-view").value]);
    field("posts").replaceChildren(...shown.map(postItem));
    field("posts-status").textContent = shown.length ? "" : "Keine Entwürfe in dieser Ansicht.";
    // a post on its way is followed until every target is published or failed
    const moving = posts.some((post) => post.order && Object.values(post.order.targets).some((target) =>
      !["published", "failed"].includes(target.status) && new Date(post.order.dueAt) <= new Date()));
    clearTimeout(state.follow);
    if (moving) state.follow = setTimeout(showPosts, 15000);
  } catch (error) {
    field("posts-status").textContent = error.message || "Die Entwürfe konnten nicht geladen werden.";
  }
}

async function refresh() {
  await showOverview();
  await Promise.all([showJobs(), showTrash(), showPosts()]);
}

field("stage").append(...STAGE_ORDER.map((stage) => Object.assign(document.createElement("option"), {value: stage, textContent: STAGE_NAMES[stage]})));
field("upload").addEventListener("submit", upload);
field("photos").addEventListener("change", showChosen);
for (const tab of TABS) {
  tab.addEventListener("click", () => { location.hash = tabName(tab); });
  tab.addEventListener("keydown", onTabKey);
}
window.addEventListener("hashchange", follow);
follow();
field("job-view").addEventListener("change", showJobs);
field("post-view").addEventListener("change", showPosts);
for (const id of ["view", "stage", "search"]) field(id).addEventListener("input", showRows);
field("group-by").addEventListener("change", showStats);
// a link to one job (#job-...) can only scroll once the jobs are there
refresh().then(() => location.hash.startsWith("#job-") && follow());
