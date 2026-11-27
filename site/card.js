"use strict";

const select = (selector) => document.querySelector(selector);
const itemId = new URLSearchParams(location.search).get("item");
const title = select("main h1");
const status = select("#card-status");

async function readJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(path);
  return response.json();
}

function imageFor(item, images, social) {
  const prepared = images.galleryImages.find((entry) => entry.itemId === item.itemId);
  const owner = social && images.assets.find((asset) =>
    asset.path.startsWith(`verification/specimens/${social.specimenId}.`) &&
    asset.imageScope === "exact-printing");
  if (owner?.preview && (!prepared || prepared.source !== owner.path || prepared.scope !== "exact-printing")) {
    return {path: owner.preview, exact: true};
  }
  if (prepared?.images.length) {
    return {path: prepared.images.at(-1).path, exact: prepared.scope === "exact-printing"};
  }
  const asset = images.assets.find((entry) => entry.assetId === item.imageAssetId);
  const path = asset?.preview || asset?.path;
  return {path: path?.startsWith("images/") ? path : null, exact: asset?.imageScope === "exact-printing"};
}

function showImage({path, exact}, name) {
  const photo = select("#card-photo");
  const caption = select("#image-caption");
  if (!path) {
    caption.textContent = "Image unavailable";
    return;
  }
  photo.addEventListener("error", () => {
    photo.hidden = true;
    caption.textContent = "Image unavailable";
  }, {once: true});
  photo.alt = `Card front: ${name}`;
  photo.src = path;
  photo.hidden = false;
  caption.textContent = exact ? "" : "Representative card image";
}

function showFacts(facts) {
  for (const [label, value] of Object.entries(facts)) {
    if (!value || value === "unknown") continue;
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    select("#card-facts").append(term, detail);
  }
}

function showLinks(section, links) {
  for (const [label, url] of links) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = url;
    link.textContent = label;
    item.append(link);
    select(`${section} ul`).append(item);
  }
  select(section).hidden = links.length === 0;
}

function showCard(item, sets, images, social, evidence) {
  const edition = sets.setEditions.find((entry) => entry.setEditionId === item.setEditionId);
  const set = sets.localSets.find((entry) => entry.localSetId === edition?.localSetId);
  const code = sets.setEditionCodes.find((entry) => entry.setEditionId === item.setEditionId);
  const language = sets.localizations.find((entry) => entry.localizationId === edition?.localizationId);
  const name = item.localCardName || item.cardName;
  const number = [item.collectorNumber, item.collectorNumberDenominator].filter(Boolean).join("/");
  title.textContent = [name, number, language?.displayName, item.finish, item.foilPattern].filter(Boolean).join(" · ");
  document.title = `${title.textContent} · Snoredex`;
  showImage(imageFor(item, images, social), name);
  showFacts({Set: set?.localSetName, "Set code": code?.printedSetCode || set?.localSetCode,
    "Card number": number, Language: language?.displayName, Edition: item.edition, Finish: item.finish,
    "Foil pattern": item.foilPattern, Artist: item.artist, Markings: item.markings.map((mark) => mark.text).join(", "),
    "Evidence status": item.itemKind === "verified-printing" ? item.finishVerificationStatus : "Open research"});
  showLinks("#card-posts", socialPosts(social));
  showLinks("#card-evidence", (evidence?.sourceLinks || [])
    .filter((url) => /^https?:\/\//i.test(url)).map((url) => [url, url]));
  status.hidden = true;
  select("#card-content").hidden = false;
}

async function loadCard() {
  const [printings, sets, images, social, evidence] = await Promise.all(
    ["printings", "sets", "images", "social", "evidence"].map((file) => readJSON(`data/${file}.json`)));
  const item = printings.printings.find((entry) => entry.itemId === itemId);
  if (!item?.active) {
    status.textContent = item ? "This printing is no longer in the active collection." : "Printing not found.";
    return;
  }
  showCard(item, sets, images, social.find((entry) => entry.itemId === itemId),
    evidence.printings.find((entry) => entry.itemId === itemId));
}

loadCard().catch(() => { status.textContent = "Card details could not be loaded. Try reloading this page."; });
