"use strict";

const cards = JSON.parse(document.querySelector("#gallery-data").textContent);
const artworkOrder = document.querySelector("#artwork-order");
let orderedCards = cards;
const container = document.querySelector("#gallery-cards");
const toggle = document.querySelector("#binder-toggle");
const controls = document.querySelector("#binder-controls");
const settings = document.querySelector("#binder-settings");
const previous = document.querySelector("#binder-prev");
const next = document.querySelector("#binder-next");
const position = document.querySelector("#binder-position");
const dialog = document.querySelector("#card-dialog");
let binder = false;
let rows = 3;
let columns = 3;
let order = "page";
let spread = 0;
let opener;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function picture(card, detail = false) {
  const path = detail ? card.preview : card.thumbnail;
  if (!path) return element("span", "Image unavailable", "gallery-placeholder");
  const image = element("img");
  image.alt = detail ? card.name : "";
  image.decoding = "async";
  if (!detail) image.loading = "lazy";
  image.addEventListener("error", () => {
    image.replaceWith(element("span", "Image unavailable", "gallery-placeholder"));
  });
  image.src = path;
  return image;
}

function openCard(card, button) {
  opener = button;
  document.querySelector("#card-title").textContent = card.name;
  document.querySelector("#card-picture").replaceChildren(picture(card, true));
  if (card.imageScope === "representative") {
    document.querySelector("#card-picture").append(element("p", "Representative card image"));
  }
  const facts = document.querySelector("#card-facts");
  facts.replaceChildren();
  const release = card.date
    ? [card.date, card.datePrecision, card.approximate ? "approximate" : ""].filter(Boolean).join(" · ")
    : "Undated";
  for (const [label, value] of Object.entries({
    Set: card.set, "Set code / number": [card.setCode, card.number].filter(Boolean).join(" "),
    Artist: card.artist, Language: card.language, Edition: card.edition, Finish: card.finish,
    "Foil pattern": card.foilPattern, Markings: card.markings.join(", "), Distribution: card.distribution,
    "Card size": card.cardSize, Release: release, "Artwork group": `#${card.artworkNumber}`,
    "Evidence status": card.kind === "verified-printing" ? card.status : `Open research · ${card.status}`,
  })) {
    facts.append(element("dt", label), element("dd", value || "—"));
  }
  const note = document.querySelector("#card-note");
  note.textContent = card.note || "";
  note.hidden = !card.note;
  const sources = document.querySelector("#card-sources");
  sources.replaceChildren();
  for (const url of card.sources) {
    if (!/^https?:\/\//i.test(url)) continue;
    const link = element("a", url);
    link.href = url;
    const item = element("li");
    item.append(link);
    sources.append(item);
  }
  if (card.imageSource) {
    const imageSource = element("a", card.imageScope === "representative"
      ? "Retained representative image" : "Retained exact-printing image");
    imageSource.href = card.imageSource;
    const item = element("li");
    item.append(imageSource);
    sources.append(item);
  }
  dialog.showModal();
}

dialog.addEventListener("close", () => {
  document.querySelector("#card-picture").replaceChildren();
  opener?.focus();
});

function tile(card) {
  const button = element("button", "", "gallery-card");
  button.type = "button";
  button.dataset.cardId = card.id;
  button.setAttribute("aria-label", [card.name, card.set, card.number, card.language,
    card.edition, card.finish, card.foilPattern, card.distribution,
    card.kind === "verified-printing" ? "" : "Open research"].filter(Boolean).join(", "));
  const caption = element("span", "", "gallery-caption");
  caption.append(element("strong", card.set || "Unknown set"),
    element("span", [card.setCode, card.number].filter(Boolean).join(" ")),
    element("span", card.artist || "Unknown artist"));
  button.append(picture(card), caption);
  button.addEventListener("click", () => openCard(card, button));
  return button;
}

function render() {
  container.classList.toggle("binder-scroll", binder);
  if (!binder) {
    container.replaceChildren(...orderedCards.map(tile));
    return;
  }
  const pageSize = rows * columns;
  const spreadSize = 2 * pageSize;
  const count = Math.max(1, Math.ceil(cards.length / spreadSize));
  const grid = element("div", "", "binder-grid");
  grid.style.setProperty("--columns", columns);
  for (let slot = 0; slot < spreadSize; slot++) {
    const card = orderedCards[spread * spreadSize + slot];
    const cell = card ? tile(card) : element("span", "", "binder-empty");
    const offset = order === "page" ? slot % pageSize : slot % (2 * columns);
    const side = order === "page" ? Math.floor(slot / pageSize) : Math.floor(offset / columns);
    const row = order === "page" ? Math.floor(offset / columns) : Math.floor(slot / (2 * columns));
    cell.style.gridArea = `${row + 1} / ${offset % columns + 1 + side * (columns + 1)}`;
    grid.append(cell);
  }
  container.replaceChildren(grid);
  position.textContent = `${spread + 1} / ${count}`;
  previous.disabled = spread === 0;
  next.disabled = spread + 1 === count;
}

artworkOrder.addEventListener("change", () => {
  orderedCards = artworkOrder.value === "descending"
    ? [...cards].sort((left, right) => right.artworkNumber - left.artworkNumber)
    : cards;
  spread = 0;
  render();
});

toggle.addEventListener("click", () => {
  binder = !binder;
  toggle.setAttribute("aria-pressed", binder);
  controls.hidden = !binder;
  render();
});

settings.addEventListener("submit", (event) => {
  event.preventDefault();
  rows = settings.elements.rows.valueAsNumber;
  columns = settings.elements.columns.valueAsNumber;
  order = settings.elements.order.value;
  spread = 0;
  render();
});

settings.querySelectorAll("[data-size]").forEach((preset) => {
  preset.addEventListener("click", () => {
    settings.elements.rows.value = preset.dataset.size;
    settings.elements.columns.value = preset.dataset.size;
    settings.requestSubmit();
  });
});

previous.addEventListener("click", () => { spread--; render(); });
next.addEventListener("click", () => { spread++; render(); });
render();
