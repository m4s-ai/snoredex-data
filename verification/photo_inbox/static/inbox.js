"use strict";

const field = (id) => document.getElementById(id);
const statusLine = field("status");

function show(kind, text, id) {
  statusLine.className = kind;
  statusLine.textContent = text;
  if (id) {
    const code = document.createElement("code");
    code.textContent = id;
    statusLine.append(code);
  }
}

function failure(response, reply) {
  // waitress itself answers an oversized body before the app, without JSON
  if (response.status === 413) return "Bitte wähle ein Foto bis 200 MB.";
  return reply.error || `Der Upload ist fehlgeschlagen (HTTP ${response.status}).`;
}

async function upload(event) {
  event.preventDefault();
  const specimen = field("specimen").value.trim().toUpperCase();
  const note = field("note").value.trim();
  if (!specimen && !note) return show("error", "Gib die SPEC-Nummer oder eine kurze Notiz zur Karte an.");
  const headers = {"Content-Type": "application/octet-stream", "X-Snoredex-Owner": "yes"};
  if (specimen) headers["X-Snoredex-Specimen"] = specimen;
  if (note) headers["X-Snoredex-Note"] = encodeURIComponent(note);
  const button = event.target.querySelector("button");
  button.disabled = true;
  show("", "Wird hochgeladen … ein DNG kann im WLAN eine halbe Minute dauern.");
  try {
    const response = await fetch("/uploads", {method: "POST", headers, body: field("photo").files[0]});
    const reply = await response.json().catch(() => ({}));
    if (!response.ok) return show("error", failure(response, reply));
    show("ok", reply.existing ? "Dieses Foto lag schon im Eingang. Auftragsnummer:" : "Foto empfangen. Auftragsnummer:",
         reply.id);
  } catch {
    show("error", "Keine Verbindung zum Eingang. Ist das Handy im Heim-WLAN?");
  } finally {
    button.disabled = false;
  }
}

field("upload").addEventListener("submit", upload);
