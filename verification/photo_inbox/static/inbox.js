"use strict";

const field = (id) => document.getElementById(id);
const statusLine = field("status");
const CODE_KEY = "snoredex-upload-code";
// storage can be blocked (private tab); the code is then simply asked for again
const store = (action) => { try { return action(localStorage); } catch { return null; } };

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
  if (response.status === 413) return "Bitte wähle ein JPEG bis 24 MB.";
  return reply.error || `Der Upload ist fehlgeschlagen (HTTP ${response.status}).`;
}

async function upload(event) {
  event.preventDefault();
  const specimen = field("specimen").value.trim().toUpperCase();
  const note = field("note").value.trim();
  if (!specimen && !note) return show("error", "Gib die SPEC-Nummer oder eine kurze Notiz zur Karte an.");
  const code = field("code").value.trim();
  const headers = {
    "Content-Type": "application/octet-stream",
    "Authorization": "Bearer " + code,
    "X-Snoredex-Owner": "yes",
  };
  if (specimen) headers["X-Snoredex-Specimen"] = specimen;
  if (note) headers["X-Snoredex-Note"] = encodeURIComponent(note);
  const button = event.target.querySelector("button");
  button.disabled = true;
  show("", "Wird hochgeladen …");
  try {
    const response = await fetch("/uploads", {method: "POST", headers, body: field("photo").files[0]});
    const reply = await response.json().catch(() => ({}));
    if (response.status === 401) store((s) => s.removeItem(CODE_KEY));
    if (!response.ok) return show("error", failure(response, reply));
    store((s) => s.setItem(CODE_KEY, code));
    show("ok", reply.existing ? "Dieses Foto lag schon im Eingang. Auftragsnummer:" : "Foto empfangen. Auftragsnummer:",
         reply.id);
  } catch {
    show("error", "Keine Verbindung zum Eingang. Ist das Handy im Heim-WLAN?");
  } finally {
    button.disabled = false;
  }
}

field("code").value = store((s) => s.getItem(CODE_KEY)) || "";
field("upload").addEventListener("submit", upload);
