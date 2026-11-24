"use strict";

const field = (id) => document.getElementById(id);
const DATE = new Intl.DateTimeFormat("de-DE", {dateStyle: "medium", timeStyle: "short"});
const DAY = new Intl.DateTimeFormat("de-DE", {dateStyle: "medium"});
const STAGE_NAMES = {none: "kein eigenes Foto", assigned: "hochgeladen, zugeordnet", filed: "verarbeitet",
                     online: "online", ready: "bereit für Instagram", posted: "gepostet"};
const state = {overview: null, labels: new Map(), catalogue: false};

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
  return item;
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

async function refresh() {
  await showOverview();
  await Promise.all([showJobs(), showTrash()]);
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
for (const id of ["view", "stage", "search"]) field(id).addEventListener("input", showRows);
field("group-by").addEventListener("change", showStats);
// a link to one job (#job-...) can only scroll once the jobs are there
refresh().then(() => location.hash.startsWith("#job-") && follow());
