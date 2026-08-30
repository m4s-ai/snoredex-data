/* Snoredex public site behaviour: table filtering and sorting (#10), checklist builder (#9).
 *
 * Vanilla JS, no dependencies, no network calls. Row and checklist data are embedded in the page
 * as JSON script blocks rather than fetched, because `fetch` of a sibling file is blocked under
 * file:// and the page must work from a local checkout as well as from GitHub Pages.
 *
 * Two invariants hold throughout:
 *   - a row is identified by its stable `rowId`, never by its position, so sorting and filtering
 *     cannot retarget a correction link or a checklist scope;
 *   - nothing here infers data. The page shows what the export says, including the difference
 *     between "no evidence" and "not attributable to this product".
 */
(function () {
  "use strict";

  const readJSON = (id) => JSON.parse(document.getElementById(id).textContent);
  const ROWS = readJSON("data-rows");
  const CHECKLIST = readJSON("data-checklist");
  const ARTWORK_REVIEW = readJSON("data-artwork-review");
  const META = readJSON("data-meta");
  const LANGS = META.languages;
  // 18 fixed columns from scripts/site.py's COLUMNS, the language matrix, then the narrow-screen
  // disclosure column and the correction column. Named because three call sites need it and the
  // literal drifted the moment #121 added a column.
  const DETAIL_SPAN = 18 + LANGS.length + 2;

  const FINISH_LABELS = {
    "non-holo": "Non-Holo",
    "holo": "Holo",
    "reverse-holo": "Reverse Holo",
    "unresolved": "Unresolved",
  };
  const PATTERN_LABELS = {
    "cosmos": "Cosmos", "crosshatch": "Crosshatch", "poke-ball": "Poké Ball",
    "master-ball": "Master Ball", "colorless-energy-star": "Colorless energy star",
    "energy-symbol-artwork-poke-ball": "Energy symbol + Poké Ball artwork",
    "tiled-type-symbol": "Tiled type symbol",
    "intricate-tiled-type-symbol": "Intricate tiled type symbol",
    "type-symbol-background": "Type symbol background",
    "large-type-symbol-left": "Large type symbol (left)",
    "plain-foil-background": "Plain foil background",
    "plain-foil-on-pokemon": "Plain foil on the Pokémon",
    "flat-foil-card-body": "Flat foil card body", "fireworks": "Fireworks",
  };

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));


  function initTheme() {
    const root = document.documentElement;
    const button = $("#theme-toggle");
    const icon = $(".theme-toggle-icon", button);
    const label = $(".theme-toggle-text", button);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    let saved = null;

    try { saved = window.localStorage.getItem("snoredex-theme"); }
    catch (error) { /* Storage can be unavailable for local files or hardened browsers. */ }

    let explicitChoice = saved === "light" || saved === "dark";

    const apply = (theme, persist) => {
      const dark = theme === "dark";
      root.dataset.theme = dark ? "dark" : "light";
      root.style.colorScheme = dark ? "dark" : "light";
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", "Color theme: " + (dark ? "dark" : "light") +
        ". Switch to " + (dark ? "light" : "dark") + " mode");
      label.textContent = dark ? "Dark mode" : "Light mode";
      icon.textContent = dark ? "☾" : "☀";
      if (persist) {
        explicitChoice = true;
        try { window.localStorage.setItem("snoredex-theme", dark ? "dark" : "light"); }
        catch (error) { /* The selected theme still applies for the current page. */ }
      }
      window.dispatchEvent(new CustomEvent("snoredex:themechange", { detail: { theme } }));
    };

    apply(root.dataset.theme || (media.matches ? "dark" : "light"), false);
    button.addEventListener("click", () => {
      apply(root.dataset.theme === "dark" ? "light" : "dark", true);
    });
    const followSystem = (event) => {
      if (!explicitChoice) apply(event.matches ? "dark" : "light", false);
    };
    if (media.addEventListener) media.addEventListener("change", followSystem);
    else if (media.addListener) media.addListener(followSystem);
  }

  function escapeHTML(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  const finishLabel = (value) => FINISH_LABELS[value] || value;
  const patternLabel = (value) => PATTERN_LABELS[value] ||
    String(value || "").replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
  const collectorFinish = (item) => item.finishFamily ||
    (item.finish === "mirror-holo" ? "reverse-holo" : item.finish);


  // Collector numbers are not lexicographic: "9" sorts before "10", and "TG10" before "TG2"
  // only if the digit runs are compared as numbers. Split into alternating text/number parts.
  function naturalKey(value) {
    const parts = String(value == null ? "" : value).match(/(\d+|\D+)/g) || [];
    return parts.map((part) => (/^\d+$/.test(part) ? part.padStart(12, "0") : part.toLowerCase()));
  }

  function compareNatural(a, b) {
    const ka = naturalKey(a);
    const kb = naturalKey(b);
    for (let i = 0; i < Math.max(ka.length, kb.length); i += 1) {
      const x = ka[i] === undefined ? "" : ka[i];
      const y = kb[i] === undefined ? "" : kb[i];
      if (x !== y) return x < y ? -1 : 1;
    }
    return 0;
  }

  const SORTERS = {
    release: (r) => r.dateSort,
    name: (r) => (r.name || "").toLowerCase(),
    setCode: (r) => (r.setCode || "").toLowerCase(),
    setName: (r) => (r.setName || "").toLowerCase(),
    number: null, // natural
    variant: (r) => ((r.variant || "") + " " + (r.variantName || "")).toLowerCase(),
    variantName: (r) => (r.variantName || "").toLowerCase(),
    rarity: (r) => (r.rarity || "").toLowerCase(),
    artist: (r) => (r.artist || "").toLowerCase(),
    edition: (r) => (r.edition || "").toLowerCase(),
    finish: (r) => (r.finishes || []).join(","),
    pattern: (r) => (r.patterns || []).join(","),
    marking: (r) => (r.markings || []).join(","),
    markingRole: (r) => (r.markingRoles || []).join(","),
    size: (r) => (r.sizes || []).join(","),
    distribution: (r) => (r.distributions || []).join(","),
    evidence: (r) => (r.evidence || []).join(","),
    langCount: (r) => r.confirmedLanguages.length,
  };
  LANGS.forEach((lang) => {
    SORTERS["lang-" + lang.code] = (r) => r.langCodes.includes(lang.code) ? 1 : 0;
  });

  let sortKey = "release";
  let sortDir = 1;

  function sortRows(rows) {
    const get = SORTERS[sortKey];
    const sorted = rows.slice();
    sorted.sort((a, b) => {
      let cmp;
      if (sortKey === "number") cmp = compareNatural(a.number, b.number);
      else {
        const x = get(a);
        const y = get(b);
        cmp = x === y ? 0 : x < y ? -1 : 1;
      }
      // Stable, deterministic tie-break so equal keys never reorder between renders.
      if (cmp === 0) cmp = compareNatural(a.rowId, b.rowId);
      return cmp * sortDir;
    });
    return sorted;
  }


  const state = {
    q: "",
    dateStatus: [],
    name: [],
    setCode: [],
    setName: [],
    number: [],
    edition: [],
    variant: [],
    variantName: [],
    rarity: [],
    artist: [],
    finish: [],
    pattern: [],
    marking: [],
    markingRole: [],
    size: [],
    distribution: [],
    evidence: [],
    yearFrom: "",
    yearTo: "",
    langMin: "",
    langMax: "",
    lang: {}, // code -> "" | "present" | "absent"
  };

  const MULTI = ["dateStatus", "name", "setCode", "setName", "number", "edition",
    "variant", "variantName", "rarity", "artist", "finish", "pattern", "marking",
    "markingRole", "size", "distribution", "evidence"];

  const valuesOrNone = (values) => values && values.length ? values : ["—"];

  const ROW_FIELD = {
    dateStatus: (r) => [r.dateStatus],
    name: (r) => [r.name],
    setCode: (r) => [r.setCode],
    setName: (r) => [r.setName],
    number: (r) => [r.number || "—"],
    edition: (r) => [r.edition],
    variant: (r) => [r.variant],
    variantName: (r) => [r.variantName || "—"],
    rarity: (r) => [r.rarity || "—"],
    artist: (r) => [r.artist || "—"],
    finish: (r) => valuesOrNone(r.finishes),
    pattern: (r) => valuesOrNone(r.patterns),
    marking: (r) => valuesOrNone(r.markings),
    markingRole: (r) => valuesOrNone(r.markingRoles),
    size: (r) => valuesOrNone(r.sizes),
    distribution: (r) => valuesOrNone(r.distributions),
    evidence: (r) => valuesOrNone(r.evidence),
  };

  function matches(row) {
    if (state.q) {
      const needle = state.q.toLowerCase();
      if (!row.search.includes(needle)) return false;
    }
    // AND between fields, OR within a field.
    for (const field of MULTI) {
      const chosen = state[field];
      if (!chosen.length) continue;
      const values = ROW_FIELD[field](row);
      if (!values.some((v) => chosen.includes(v))) return false;
    }
    const year = parseInt(row.dateSort.slice(0, 4), 10);
    if (state.yearFrom && year < parseInt(state.yearFrom, 10)) return false;
    if (state.yearTo && year > parseInt(state.yearTo, 10)) return false;

    const n = row.confirmedLanguages.length;
    if (state.langMin !== "" && n < parseInt(state.langMin, 10)) return false;
    if (state.langMax !== "" && n > parseInt(state.langMax, 10)) return false;

    for (const code of Object.keys(state.lang)) {
      const mode = state.lang[code];
      if (!mode) continue;
      const has = row.langCodes.includes(code);
      if (mode === "present" && !has) return false;
      if (mode === "absent" && has) return false;
    }
    return true;
  }


  function writeURL() {
    const params = new URLSearchParams();
    if (state.q) params.set("q", state.q);
    MULTI.forEach((f) => { if (state[f].length) params.set(f, state[f].join("~")); });
    ["yearFrom", "yearTo", "langMin", "langMax"].forEach((f) => {
      if (state[f] !== "") params.set(f, state[f]);
    });
    const langBits = Object.entries(state.lang)
      .filter(([, v]) => v)
      .map(([k, v]) => `${k}:${v === "present" ? "1" : "0"}`);
    if (langBits.length) params.set("lang", langBits.join("~"));
    if (sortKey !== "release" || sortDir !== 1) params.set("sort", `${sortKey}:${sortDir > 0 ? "a" : "d"}`);
    const query = params.toString();
    const url = window.location.pathname + (query ? "?" + query : "") + window.location.hash;
    window.history.replaceState(null, "", url);
  }

  function readURL() {
    const params = new URLSearchParams(window.location.search);
    state.q = params.get("q") || "";
    MULTI.forEach((f) => { state[f] = (params.get(f) || "").split("~").filter(Boolean); });
    ["yearFrom", "yearTo", "langMin", "langMax"].forEach((f) => { state[f] = params.get(f) || ""; });
    state.lang = {};
    (params.get("lang") || "").split("~").filter(Boolean).forEach((bit) => {
      const [code, flag] = bit.split(":");
      state.lang[code] = flag === "1" ? "present" : "absent";
    });
    const sort = params.get("sort");
    if (sort) {
      const [key, dir] = sort.split(":");
      if (SORTERS.hasOwnProperty(key)) { sortKey = key; sortDir = dir === "d" ? -1 : 1; }
    }
  }


  function distinct(getter) {
    const set = new Set();
    ROWS.forEach((row) => getter(row).forEach((v) => { if (v) set.add(v); }));
    return Array.from(set).sort((a, b) => compareNatural(a, b));
  }

  function buildControls() {
    MULTI.forEach((field) => {
      const select = document.getElementById("f-" + field);
      if (!select) return;
      distinct(ROW_FIELD[field]).forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = field === "finish" ? finishLabel(value)
          : field === "pattern" ? patternLabel(value) : value;
        select.appendChild(option);
      });
      select.addEventListener("change", () => {
        state[field] = Array.from(select.selectedOptions).map((o) => o.value);
        render();
      });
    });

    const langGrid = document.getElementById("langfilters");
    LANGS.forEach((lang) => {
      const wrap = document.createElement("div");
      wrap.className = "field";
      const id = "f-lang-" + lang.code;
      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = lang.code;
      const select = document.createElement("select");
      select.id = id;
      [["", "any"], ["present", "present"], ["absent", "absent"]].forEach(([value, text]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        select.appendChild(option);
      });
      wrap.append(label, select);
      langGrid.appendChild(wrap);
      select.addEventListener("change", (event) => {
        state.lang[lang.code] = event.target.value;
        render();
      });
    });

    $("#mobile-sort-key").addEventListener("change", (event) => {
      if (!Object.prototype.hasOwnProperty.call(SORTERS, event.target.value)) return;
      sortKey = event.target.value;
      sortDir = 1;
      render();
    });
    $("#mobile-sort-direction").addEventListener("click", () => {
      sortDir = -sortDir;
      render();
    });

    $("#f-q").addEventListener("input", (event) => { state.q = event.target.value; render(); });
    ["yearFrom", "yearTo", "langMin", "langMax"].forEach((field) => {
      $("#f-" + field).addEventListener("input", (event) => { state[field] = event.target.value; render(); });
    });
    $("#reset").addEventListener("click", () => {
      MULTI.forEach((f) => { state[f] = []; });
      state.q = ""; state.yearFrom = ""; state.yearTo = ""; state.langMin = ""; state.langMax = "";
      state.lang = {};
      sortKey = "release"; sortDir = 1;
      syncControls();
      render();
    });

    // Delegated rather than bound per button: the sticky heading is a clone of this row, and a
    // clone carries no listeners. Delegation keeps the visible copy and the real one in step.
    document.addEventListener("click", (event) => {
      const button = event.target.closest && event.target.closest("button.sort");
      if (!button) return;
      activateSort(button.dataset.key);
    });
  }

  function syncSortControls() {
    $("#mobile-sort-key").value = sortKey;
    const direction = $("#mobile-sort-direction");
    const ascending = sortDir > 0;
    direction.textContent = ascending ? "↑ Ascending" : "↓ Descending";
    direction.setAttribute("aria-label", ascending ? "Sort ascending" : "Sort descending");
  }

  function syncControls() {
    $("#f-q").value = state.q;
    MULTI.forEach((field) => {
      const select = document.getElementById("f-" + field);
      if (!select) return;
      Array.from(select.options).forEach((o) => { o.selected = state[field].includes(o.value); });
    });
    ["yearFrom", "yearTo", "langMin", "langMax"].forEach((f) => { $("#f-" + f).value = state[f]; });
    LANGS.forEach((lang) => {
      const select = document.getElementById("f-lang-" + lang.code);
      if (select) select.value = state.lang[lang.code] || "";
    });
    syncSortControls();
  }

  function activateSort(key) {
    if (!Object.prototype.hasOwnProperty.call(SORTERS, key)) return;
    if (sortKey === key) sortDir = -sortDir;
    else { sortKey = key; sortDir = 1; }
    render();
  }

  function renderChips() {
    const box = $("#chips");
    box.innerHTML = "";
    const add = (label, clear) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = label + " ";
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("aria-label", "Remove filter " + label);
      button.textContent = "×";
      button.addEventListener("click", () => { clear(); syncControls(); render(); });
      chip.appendChild(button);
      box.appendChild(chip);
    };
    if (state.q) add('search "' + state.q + '"', () => { state.q = ""; });
    MULTI.forEach((field) => {
      state[field].forEach((value) => {
        add(field + ": " + value, () => { state[field] = state[field].filter((v) => v !== value); });
      });
    });
    if (state.yearFrom) add("from " + state.yearFrom, () => { state.yearFrom = ""; });
    if (state.yearTo) add("to " + state.yearTo, () => { state.yearTo = ""; });
    if (state.langMin !== "") add("min langs " + state.langMin, () => { state.langMin = ""; });
    if (state.langMax !== "") add("max langs " + state.langMax, () => { state.langMax = ""; });
    Object.entries(state.lang).forEach(([code, mode]) => {
      if (mode) add(code + " " + mode, () => { state.lang[code] = ""; });
    });
  }


  let visibleRows = [];
  let refreshLanguageEvidence = () => {};

  function pill(text, cls) {
    return '<span class="pill ' + escapeHTML(cls) + '">' + escapeHTML(text) + "</span>";
  }

  function clippedCell(value, classes, rendered) {
    const text = value || "—";
    return '<td class="secondary ' + classes + '"><span class="cell-clip" title="' +
      escapeHTML(text) + '">' + (rendered === undefined ? escapeHTML(text) : rendered) +
      "</span></td>";
  }

  /* How strong the evidence behind a confirmed language is (#32). Confirmed is not one thing:
     an official database entry and an uncorroborated owner attestation are both "present" and a
     reader deciding whether to trust a row needs to be able to tell them apart. Tier comes from
     the provider registry; "checkable" means the citation is a URL a reader can follow. */
  function evidenceNote(row, code) {
    const ev = row.langEvidence && row.langEvidence[code];
    if (!ev) return null;
    const parts = [];
    if (ev.provider) parts.push(ev.provider);
    if (ev.tier) parts.push("tier " + ev.tier);
    parts.push(ev.corroborated ? "corroborated" : "single source");
    if (!ev.checkable) parts.push("no public URL");
    return { text: parts.join(", "), tier: ev.tier || 0,
             weak: !ev.checkable && !ev.corroborated };
  }

  /* Values the narrow breakpoint takes off screen, restated for the per-row disclosure (#121).
   * Built from the same row object the cells use, so the panel cannot drift out of step with the
   * table it stands in for. Languages are summarised as the confirmed list: the 17-column matrix
   * conveys presence by position, which a stacked panel cannot reproduce, and the confirmed names
   * are what that position was being read for. */
  function rowDetailHTML(row) {
    const variant = row.variant + (row.variantName ? " — " + row.variantName : "");
    const entries = [
      ["Release", escapeHTML(row.dateDisplay)],
      ["Expansion", escapeHTML(row.setName || "—")],
      ["Variant", escapeHTML(variant)],
      ["Rarity", escapeHTML(row.rarity || "—")],
      ["Artist", escapeHTML(row.artist || "—")],
      ["Edition", escapeHTML(row.edition)],
      ["Pattern", escapeHTML(row.patterns.join(", ") || "—")],
      ["Stamp / marking", escapeHTML(row.markings.join(", ") || "—")],
      ["Marking role", escapeHTML(row.markingRoles.join(", ") || "—")],
      ["Size", escapeHTML(row.sizes.join(", ") || "—")],
      ["Distribution", escapeHTML(row.distributions.join(", ") || "—")],
      ["Confirmed languages", row.confirmedLanguages.length
        ? escapeHTML(row.confirmedLanguages.join(", ")) +
          ' <span class="detail-count">(' + row.confirmedLanguages.length + ")</span>"
        : "—"],
    ];
    return '<dl class="rowdetail-list">' + entries
      .map(([term, value]) => "<dt>" + term + "</dt><dd>" + value + "</dd>").join("") + "</dl>";
  }

  function rowHTML(row, index) {
    const detailId = "rowdetail-" + index;
    const langCells = LANGS.map((lang) => {
      const has = row.langCodes.includes(lang.code);
      const state = has ? "present" : "absent";
      const note = has ? evidenceNote(row, lang.code) : null;
      // Keep the cell label to the compact state used across the 17-column matrix. The evidence
      // control carries the full accessible label and opens a touch/keyboard detail popover.
      const label = lang.name + ": " + state;
      const attrs = note
        ? ' data-tier="' + note.tier + '"' + (note.weak ? ' data-unverifiable="true"' : "")
        : "";
      const symbol = note
        ? '<button type="button" class="lang-evidence-trigger" aria-expanded="false" ' +
          'aria-label="' + escapeHTML(label + " — " + note.text) + '" ' +
          'data-label="' + escapeHTML(label) + '" data-evidence="' + escapeHTML(note.text) + '">' +
          '<span aria-hidden="true">✓</span></button>'
        : '<span aria-hidden="true">' + (has ? "✓" : "—") + "</span>";
      return '<td class="langcell ' + (has ? "yes" : "no") + '" data-state="' + state + '"' +
        attrs + ' title="' + escapeHTML(note ? label + " — " + note.text : label) +
        '" aria-label="' + escapeHTML(label) + '">' +
        symbol + "</td>";
    }).join("");
    const finishPills = row.finishDisplay.map((f) => pill(f.label, f.status)).join("");
    const variant = row.variant + (row.variantName ? " — " + row.variantName : "");
    const evidence = row.evidence.join(", ") || "—";
    const image = row.image
      ? '<button type="button" class="card-preview-trigger" aria-expanded="false" ' +
        'aria-label="Enlarge card image: ' + escapeHTML(row.name) + '" title="Enlarge card image">' +
        '<img loading="lazy" src="' + escapeHTML(row.image) + '" alt="' + escapeHTML(row.name) + '">' +
        "</button>"
      : "";
    const patternBadges = row.patterns.map((pattern) =>
      '<span class="treatment">' + escapeHTML(patternLabel(pattern)) + "</span>").join("");
    const release = row.dateSource && row.dateSource.url
      ? '<a class="release-source" href="' + escapeHTML(row.dateSource.url) +
        '" target="_blank" rel="noopener" title="' +
        escapeHTML("Source: " + row.dateSource.page + " (" + row.dateSource.field + ")") + '">' +
        escapeHTML(row.dateDisplay) + "</a>"
      : escapeHTML(row.dateDisplay);
    return (
      "<tr>" +
      // Identity block, in the order and with the classes scripts/site.py emits for the header —
      // app.css pins exactly these five columns, so the two must not drift apart (#124).
      '<td class="img">' + image + "</td>" +
      '<td class="col-release">' + release + "</td>" +
      '<td class="col-card">' + escapeHTML(row.name) + "</td>" +
      '<td class="col-set">' + escapeHTML(row.setCode) + "</td>" +
      '<td class="col-number">' + escapeHTML(row.number || "—") + "</td>" +
      clippedCell(row.setName, "col-expansion") +
      clippedCell(variant, "col-variant") +
      clippedCell(row.rarity || "—", "col-rarity") +
      clippedCell(row.artist || "—", "col-artist") +
      '<td class="col-edition">' + escapeHTML(row.edition) + "</td>" +
      '<td class="col-finish">' + (finishPills || '<span class="pill pending">no evidence</span>') + "</td>" +
      clippedCell(row.patterns.join(", ") || "—", "col-pattern", patternBadges || "—") +
      clippedCell(row.markings.join(", ") || "—", "col-marking") +
      clippedCell(row.markingRoles.join(", ") || "—", "col-marking-role") +
      clippedCell(row.sizes.join(", "), "col-size") +
      clippedCell(row.distributions.join(", ") || "—", "col-distribution") +
      clippedCell(evidence, "col-evidence", row.evidence.map((e) => pill(e, e)).join("") || "—") +
      '<td class="langcount">' + row.confirmedLanguages.length + "</td>" +
      langCells +
      '<td class="col-more">' +
      '<button type="button" class="rowmore" aria-expanded="false" aria-controls="' + detailId + '" ' +
      'data-row-id="' + escapeHTML(row.rowId) + '" data-detail-id="' + detailId + '" ' +
      'aria-label="More details for ' +
      escapeHTML(row.name + " " + row.setCode + " " + (row.number || "")) + '">More info</button>' +
      "</td>" +
      '<td class="corr"><a href="' + escapeHTML(row.correctionUrl) + '" target="_blank" rel="noopener" ' +
      'aria-label="Report a correction for ' + escapeHTML(row.name + " " + row.setCode + " " + (row.number || "")) +
      '">Correction?</a></td>' +
      "</tr>"
    );
  }

  function render() {
    visibleRows = sortRows(ROWS.filter(matches));

    syncSortControls();

    $$("thead th[data-key]").forEach((th) => {
      th.setAttribute("aria-sort",
        th.dataset.key === sortKey ? (sortDir > 0 ? "ascending" : "descending") : "none");
    });

    const body = $("#rows");
    if (!visibleRows.length) {
      body.innerHTML = '<tr><td class="empty" colspan="' + DETAIL_SPAN +
        '">No rows match these filters. Use <strong>Reset all</strong> to start over.</td></tr>';
    } else {
      // Year separators are only meaningful in chronological order. Under any other sort they
      // would attach a heading to cards that are not from that year, so they are omitted and
      // restored automatically when the release sort returns.
      const chronological = sortKey === "release";
      let previousYear = null;
      const parts = [];
      visibleRows.forEach((row) => {
        if (chronological) {
          const year = row.dateSort.slice(0, 4);
          if (year !== previousYear) {
            previousYear = year;
            parts.push('<tr class="yearsep"><td colspan="' + DETAIL_SPAN + '">' +
              (year === "9999" ? "Undated" : year) + "</td></tr>");
          }
        }
        parts.push(rowHTML(row, parts.length));
      });
      body.innerHTML = parts.join("");
    }

    $("#count").textContent = "Showing " + visibleRows.length + " of " + ROWS.length + " rows";
    renderChips();
    writeURL();
    updateChecklistPreview();
    window.requestAnimationFrame(() => {
      refreshTableOverflow();
      refreshClippedCells();
      refreshStickyHeader();
      refreshLanguageEvidence();
    });
  }


  let refreshClippedCells = () => {};

  function initClippedCells() {
    // Runs after every render — including every keystroke in the search field — over roughly two
    // thousand cells. Measuring and marking in one pass interleaves reads with writes, so each
    // attribute write invalidates style for the next scrollWidth read and layout runs again. The
    // measurements are taken first, then applied, and a cell already in the right state is left
    // alone: 10.9ms to 4.1ms per pass at 3072px, which is the difference between fitting in a
    // frame and dropping one.
    const update = () => {
      const cells = $$(".cell-clip");
      const clipping = cells.map((cell) =>
        cell.classList.contains("is-expanded") ? null : cell.scrollWidth > cell.clientWidth + 1);
      cells.forEach((cell, index) => {
        const clipped = clipping[index];
        if (clipped === null) return;
        if (clipped) {
          if (cell.dataset.clipped === "true") return;
          const text = cell.getAttribute("title") || cell.textContent.trim();
          cell.dataset.clipped = "true";
          cell.tabIndex = 0;
          cell.setAttribute("role", "button");
          cell.setAttribute("aria-expanded", "false");
          cell.setAttribute("aria-label", text + ". Show full value");
        } else if (cell.dataset.clipped) {
          delete cell.dataset.clipped;
          cell.removeAttribute("tabindex");
          cell.removeAttribute("role");
          cell.removeAttribute("aria-expanded");
          cell.removeAttribute("aria-label");
        }
      });
    };

    const toggle = (cell, force) => {
      if (!cell || (cell.dataset.clipped !== "true" && !cell.classList.contains("is-expanded"))) return;
      const expanded = force === undefined ? !cell.classList.contains("is-expanded") : force;
      const text = cell.getAttribute("title") || cell.textContent.trim();
      cell.classList.toggle("is-expanded", expanded);
      cell.dataset.clipped = "true";
      cell.tabIndex = 0;
      cell.setAttribute("role", "button");
      cell.setAttribute("aria-expanded", String(expanded));
      cell.setAttribute("aria-label", text + (expanded ? ". Hide full value" : ". Show full value"));
      window.requestAnimationFrame(() => {
        refreshTableOverflow();
        refreshStickyHeader();
        if (!expanded) update();
      });
    };

    document.addEventListener("click", (event) => {
      const cell = event.target.closest && event.target.closest(".cell-clip");
      if (cell) toggle(cell);
    });
    document.addEventListener("keydown", (event) => {
      const cell = event.target.closest && event.target.closest(".cell-clip");
      if (!cell) return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggle(cell);
      } else if (event.key === "Escape" && cell.classList.contains("is-expanded")) {
        event.preventDefault();
        toggle(cell, false);
      }
    });
    // A window drag fires resize continuously; one measurement per frame is enough.
    let scheduled = 0;
    window.addEventListener("resize", () => {
      if (scheduled) return;
      scheduled = window.requestAnimationFrame(() => { scheduled = 0; update(); });
    });
    return update;
  }


  function initLanguageEvidence() {
    const popover = document.createElement("div");
    popover.id = "collection-language-evidence";
    popover.className = "lang-evidence-popover";
    popover.hidden = true;
    popover.setAttribute("aria-hidden", "true");
    popover.setAttribute("role", "status");
    popover.setAttribute("aria-live", "polite");
    document.body.appendChild(popover);

    let active = null;

    const position = () => {
      if (!active || popover.hidden) return;
      const anchor = active.getBoundingClientRect();
      const box = popover.getBoundingClientRect();
      const gap = 10;
      const margin = 12;
      let left;
      let top;

      if (window.innerWidth <= 720) {
        left = (window.innerWidth - box.width) / 2;
        top = (window.innerHeight - box.height) / 2;
      } else {
        left = anchor.left;
        top = anchor.bottom + gap;
        if (left + box.width > window.innerWidth - margin) left = anchor.right - box.width;
        if (top + box.height > window.innerHeight - margin) top = anchor.top - box.height - gap;
      }

      popover.style.left = Math.round(Math.max(margin,
        Math.min(left, window.innerWidth - box.width - margin))) + "px";
      popover.style.top = Math.round(Math.max(margin,
        Math.min(top, window.innerHeight - box.height - margin))) + "px";
    };

    const hide = () => {
      if (active) {
        active.setAttribute("aria-expanded", "false");
        active.removeAttribute("aria-describedby");
      }
      active = null;
      popover.hidden = true;
      popover.setAttribute("aria-hidden", "true");
    };

    const show = (trigger) => {
      if (active && active !== trigger) {
        active.setAttribute("aria-expanded", "false");
        active.removeAttribute("aria-describedby");
      }
      active = trigger;
      popover.textContent = trigger.dataset.label + " — " + trigger.dataset.evidence;
      popover.hidden = false;
      popover.setAttribute("aria-hidden", "false");
      trigger.setAttribute("aria-expanded", "true");
      trigger.setAttribute("aria-describedby", popover.id);
      window.requestAnimationFrame(position);
    };

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest && event.target.closest(".lang-evidence-trigger");
      if (trigger) {
        if (active === trigger) hide();
        else show(trigger);
        return;
      }
      if (active) hide();
    });
    document.addEventListener("focusout", (event) => {
      const trigger = event.target.closest && event.target.closest(".lang-evidence-trigger");
      if (!trigger) return;
      window.setTimeout(() => {
        if (active === trigger && document.activeElement !== trigger) hide();
      }, 0);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || !active) return;
      const trigger = active;
      hide();
      trigger.focus();
    });
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, { passive: true });

    return () => {
      if (active && !active.isConnected) hide();
      else position();
    };
  }


  let refreshTableOverflow = () => {};

  function initTableOverflow() {
    const frame = $("#collection-table-frame");
    const scroller = $("#collection-table-scroll");
    const tools = $("#collection-scroll-tools");
    const hint = $(".scroll-hint-text", tools);
    const left = $("#collection-scroll-left");
    const right = $("#collection-scroll-right");

    const update = () => {
      const max = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
      const overflowing = max > 2;
      const canLeft = overflowing && scroller.scrollLeft > 2;
      const canRight = overflowing && scroller.scrollLeft < max - 2;

      tools.hidden = !overflowing;
      frame.classList.toggle("is-overflowing", overflowing);
      frame.classList.toggle("can-scroll-left", canLeft);
      frame.classList.toggle("can-scroll-right", canRight);
      left.disabled = !canLeft;
      right.disabled = !canRight;

      if (canLeft && canRight) hint.textContent = "More columns on both sides";
      else if (canLeft) hint.textContent = "More columns to the left";
      else hint.textContent = "More columns to the right — scroll horizontally";
    };

    const scrollByPage = (direction) => {
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      scroller.scrollBy({
        left: direction * Math.max(280, Math.round(scroller.clientWidth * 0.72)),
        behavior: reducedMotion ? "auto" : "smooth",
      });
    };

    left.addEventListener("click", () => scrollByPage(-1));
    right.addEventListener("click", () => scrollByPage(1));
    scroller.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    if (window.ResizeObserver) new ResizeObserver(update).observe(scroller);
    update();
    return update;
  }


  let refreshStickyHeader = () => {};

  function initStickyTableHeader() {
    const scroller = $("#collection-table-scroll");
    const tools = $("#collection-scroll-tools");
    const table = $("#collection-table");
    const sourceHead = $("thead", table);
    const overlay = document.createElement("div");
    overlay.id = "collection-sticky-header";
    overlay.className = "table-sticky-header";
    overlay.setAttribute("aria-hidden", "true");

    const cloneTable = document.createElement("table");
    const colgroup = document.createElement("colgroup");
    const cloneHead = sourceHead.cloneNode(true);
    $$("button.sort", cloneHead).forEach((button) => {
      const label = document.createElement("span");
      label.className = "sort-clone-label";
      label.textContent = button.textContent;
      button.replaceWith(label);
    });
    cloneTable.append(colgroup, cloneHead);

    const correction = document.createElement("div");
    correction.className = "table-sticky-correction";
    correction.textContent = $("th.corr", sourceHead).textContent.trim();
    overlay.append(cloneTable, correction);
    document.body.appendChild(overlay);

    let scheduled = 0;

    const sync = () => {
      scheduled = 0;
      if (window.matchMedia("print").matches) {
        overlay.classList.remove("is-visible");
        return;
      }

      const sourceCells = $$("th", sourceHead);
      const cloneCells = $$("th", cloneHead);
      const widths = sourceCells.map((cell) => cell.getBoundingClientRect().width);
      colgroup.innerHTML = widths.map((width) => '<col style="width:' + width + 'px">').join("");
      cloneCells.forEach((cell, index) => {
        cell.setAttribute("aria-sort", sourceCells[index].getAttribute("aria-sort") || "none");
      });

      const scrollerBox = scroller.getBoundingClientRect();
      const headBox = sourceHead.getBoundingClientRect();
      const tableBox = table.getBoundingClientRect();
      const toolOffset = tools.hidden ? 0 : tools.getBoundingClientRect().height;
      const headerHeight = headBox.height;
      const correctionWidth = widths[widths.length - 1];
      const visible = headBox.top <= toolOffset && scrollerBox.bottom > toolOffset + headerHeight;

      // Everything focusable inside the table scrolls clear of this band; see app.css.
      document.documentElement.style.setProperty(
        "--sticky-head-offset", Math.ceil(toolOffset + headerHeight) + "px");

      overlay.style.left = Math.round(scrollerBox.left) + "px";
      overlay.style.top = Math.round(toolOffset) + "px";
      overlay.style.width = Math.round(scrollerBox.width) + "px";
      overlay.style.height = Math.ceil(headerHeight) + "px";
      cloneTable.style.width = Math.ceil(tableBox.width) + "px";
      cloneTable.style.height = Math.ceil(headerHeight) + "px";
      cloneTable.style.transform = "translateX(" + Math.round(-scroller.scrollLeft) + "px)";
      correction.style.width = Math.ceil(correctionWidth) + "px";
      correction.style.height = Math.ceil(headerHeight) + "px";
      overlay.classList.toggle("is-visible", visible);
    };

    const schedule = () => {
      if (!scheduled) scheduled = window.requestAnimationFrame(sync);
    };

    // The overlay covers the real heading, so it has to answer for the interactions it hides.
    // Its visual sort labels activate the same sort routine; a click that misses one must stop here
    // rather than fall through to whichever row happens to be scrolling past underneath.
    overlay.addEventListener("mousedown", (event) => {
      // Focus stays out of an aria-hidden subtree; the real heading remains the keyboard target.
      event.preventDefault();
    });
    overlay.addEventListener("click", (event) => {
      const heading = event.target.closest && event.target.closest("th[data-key]");
      if (heading) activateSort(heading.dataset.key);
    });
    overlay.addEventListener("wheel", (event) => {
      if (!event.deltaX) return;
      scroller.scrollLeft += event.deltaX;
      event.preventDefault();
      schedule();
    }, { passive: false });

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("snoredex:themechange", schedule);
    scroller.addEventListener("scroll", schedule, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(schedule).observe(scroller);
    sync();
    return sync;
  }


  function initCardPreview() {
    const preview = document.createElement("figure");
    preview.className = "card-preview";
    preview.hidden = true;
    preview.setAttribute("aria-hidden", "true");
    preview.innerHTML = '<img alt=""><figcaption></figcaption>';
    document.body.appendChild(preview);

    const previewImage = $("img", preview);
    const caption = $("figcaption", preview);
    let active = null;
    let pinned = false;

    const position = () => {
      if (!active || preview.hidden) return;
      const anchor = active.getBoundingClientRect();
      const box = preview.getBoundingClientRect();
      const gap = 14;
      const margin = 12;
      let left;
      let top;

      if (window.innerWidth <= 720) {
        left = (window.innerWidth - box.width) / 2;
        top = (window.innerHeight - box.height) / 2;
      } else {
        left = anchor.right + gap;
        if (left + box.width > window.innerWidth - margin) left = anchor.left - gap - box.width;
        if (left < margin) left = (window.innerWidth - box.width) / 2;
        top = anchor.top + (anchor.height - box.height) / 2;
      }

      preview.style.left = Math.round(Math.max(margin, Math.min(left, window.innerWidth - box.width - margin))) + "px";
      preview.style.top = Math.round(Math.max(margin, Math.min(top, window.innerHeight - box.height - margin))) + "px";
    };

    const hide = () => {
      if (active) active.setAttribute("aria-expanded", "false");
      active = null;
      pinned = false;
      preview.hidden = true;
      preview.setAttribute("aria-hidden", "true");
    };

    const show = (trigger, keepOpen) => {
      if (active && active !== trigger) active.setAttribute("aria-expanded", "false");
      active = trigger;
      pinned = Boolean(keepOpen);
      const image = $("img", trigger);
      previewImage.src = image.currentSrc || image.src;
      caption.textContent = image.alt;
      trigger.setAttribute("aria-expanded", "true");
      preview.hidden = false;
      preview.setAttribute("aria-hidden", "false");
      window.requestAnimationFrame(position);
    };

    document.addEventListener("pointerover", (event) => {
      const trigger = event.target.closest && event.target.closest(".card-preview-trigger");
      if (!trigger || trigger.contains(event.relatedTarget) || event.pointerType === "touch") return;
      show(trigger, false);
    });
    document.addEventListener("pointerout", (event) => {
      const trigger = event.target.closest && event.target.closest(".card-preview-trigger");
      if (!trigger || trigger.contains(event.relatedTarget) || pinned) return;
      hide();
    });
    document.addEventListener("focusin", (event) => {
      const trigger = event.target.closest && event.target.closest(".card-preview-trigger");
      if (trigger) show(trigger, false);
    });
    document.addEventListener("focusout", (event) => {
      const trigger = event.target.closest && event.target.closest(".card-preview-trigger");
      if (trigger && !pinned) hide();
    });
    document.addEventListener("click", (event) => {
      const trigger = event.target.closest && event.target.closest(".card-preview-trigger");
      if (trigger) {
        if (active === trigger && pinned) hide();
        else show(trigger, true);
      } else if (pinned) hide();
    });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") hide(); });
    previewImage.addEventListener("load", position);
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, { passive: true });
  }


  function checklistSelection() {
    const scope = $("#cl-scope").value;
    const langs = Array.from($("#cl-langs").selectedOptions).map((o) => o.value);
    const editions = Array.from($("#cl-editions").selectedOptions).map((o) => o.value);
    const finishes = Array.from($("#cl-finishes").selectedOptions).map((o) => o.value);
    const includeUnresolved = $("#cl-unresolved").checked;

    let allowedChecklistKeys = null;
    if (scope === "filtered") {
      // A catalogue product can project to several dated physical rows. Keep filtered checklist
      // scope attached to the selected physical printing without changing the canonical row ID.
      allowedChecklistKeys = new Set();
      visibleRows.forEach((row) => {
        const sourceRowId = row.sourceRowId || row.rowId;
        if (row.splitPhysicalPrinting && row.printingIds.length) {
          row.printingIds.forEach((printingId) => {
            allowedChecklistKeys.add(sourceRowId + "|" + printingId);
          });
        } else {
          allowedChecklistKeys.add(sourceRowId + "|*");
        }
      });
    }

    return CHECKLIST.filter((item) => {
      if (allowedChecklistKeys
          && !allowedChecklistKeys.has(item.rowId + "|*")
          && !allowedChecklistKeys.has(item.rowId + "|" + item.printingId)) return false;
      if (langs.length && !langs.includes(item.language)) return false;
      if (editions.length && !editions.includes(item.edition)) return false;
      if (item.finish === "unresolved") return includeUnresolved;
      if (finishes.length && !finishes.includes(collectorFinish(item))) return false;
      return true;
    });
  }

  function updateChecklistPreview() {
    const items = checklistSelection();
    const unresolved = items.filter((i) => i.finish === "unresolved").length;
    const reverseItems = items.filter((i) => collectorFinish(i) === "reverse-holo");
    const reverseGroups = new Set(reverseItems.map((i) => i.finishGroupId)).size;
    $("#cl-preview").innerHTML =
      "<strong>" + items.length + "</strong> checklist items — " +
      (items.length - unresolved) + " documented printings, " +
      unresolved + " with unresolved finish. " + reverseItems.length +
      " Reverse Holo treatments in " + reverseGroups + " finish groups.";
  }

  function groupKey(item, mode) {
    if (mode === "set") return item.setCode + " — " + item.setName;
    if (mode === "card") return item.cardName + " (" + item.setCode + " " + (item.number || "—") + ")";
    if (mode === "language") return item.language;
    return (item.releaseDate || "undated") + " — " + item.setName;
  }

  function buildChecklistDocument() {
    const items = checklistSelection();
    const mode = $("#cl-group").value;
    const compact = $("#cl-layout").value === "compact";
    const paper = $("#cl-paper").value === "Letter" ? "Letter" : "A4";
    const today = new Date().toISOString().slice(0, 10);

    const groups = new Map();
    items.forEach((item) => {
      const key = groupKey(item, mode);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });

    const sections = Array.from(groups.entries()).map(([heading, list]) => {
      const rows = list.map((item) => {
        const family = collectorFinish(item);
        const markingText = (item.markings || []).join(", ") || item.marking;
        const distributionText = item.distribution && [
          item.distribution.name || item.distribution.kind,
          item.distribution.region,
        ].filter(Boolean).join(" — ");
        const detail = [
          escapeHTML(item.language),
          item.edition !== "—" ? escapeHTML(item.edition) : null,
          item.finish === "unresolved"
            ? "<em>finish unresolved — not a confirmed version</em>"
            : "<strong>" + escapeHTML(finishLabel(family)) + "</strong>",
          item.foilPattern ? "treatment: " + escapeHTML(patternLabel(item.foilPattern)) : null,
          markingText ? "markings: " + escapeHTML(markingText) : null,
          distributionText ? "distribution: " + escapeHTML(distributionText) : null,
          item.cardSize && item.cardSize !== "standard" ? escapeHTML(item.cardSize) : null,
        ].filter(Boolean).join(" · ");
        const image = !compact && item.image
          ? '<img src="' + escapeHTML(item.image) + '" alt="">' : "";
        return '<tr data-checklist-id="' + escapeHTML(item.checklistId) +
          '" data-finish-group-id="' + escapeHTML(item.finishGroupId) + '" class="' +
          (item.finish === "unresolved" ? "unresolved" : "") + '">' +
          '<td class="box"><span class="cb"></span></td>' +
          (compact ? "" : '<td class="thumb">' + image + "</td>") +
          "<td><strong>" + escapeHTML(item.cardName) + "</strong> — " +
          escapeHTML(item.setCode) + " " + escapeHTML(item.number || "—") +
          "<br><small>" + detail + "</small></td>" +
          '<td class="id"><code>' + escapeHTML(item.checklistId) + "</code></td>" +
          "</tr>";
      }).join("");
      return "<section><h2>" + escapeHTML(heading) + "</h2><table><thead><tr>" +
        "<th>Owned</th>" + (compact ? "" : "<th>Image</th>") +
        "<th>Printing</th><th>Checklist ID</th></tr></thead><tbody>" + rows +
        "</tbody></table></section>";
    }).join("");

    const unresolved = items.filter((i) => i.finish === "unresolved").length;
    const scopeLabel = $("#cl-scope").value === "filtered"
      ? "current filtered table rows" : "all documented items";

    return "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">" +
      '<meta name="viewport" content="width=device-width,initial-scale=1">' +
      "<title>Snoredex checklist " + today + "</title><style>" +
      "@page{size:" + paper + ";margin:14mm}" +
      "body{font:11pt/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;" +
      "color:#000;background:#fff;margin:0;padding:16px}" +
      "h1{font-size:17pt;margin:0 0 4px}h2{font-size:12pt;margin:16px 0 4px;border-bottom:1px solid #000;" +
      "page-break-after:avoid}" +
      ".meta{font-size:9pt;color:#333;margin-bottom:12px}" +
      "table{width:100%;border-collapse:collapse}" +
      "tr{page-break-inside:avoid;break-inside:avoid}" +
      "th,td{padding:3px 4px;border-bottom:1px solid #bbb;vertical-align:top;text-align:left}" +
      "thead{display:table-header-group}th{font-size:8pt}" +
      "td.box{width:20px}td.thumb{width:42px}td.thumb img{width:38px;height:auto}" +
      "td.id{width:24%;font-size:7pt;overflow-wrap:anywhere}" +
      ".cb{display:inline-block;width:12px;height:12px;border:1.4px solid #000;border-radius:2px}" +
      "tr.unresolved td{background:#f0f0f0}" +
      "small{color:#333}" +
      ".notice{font-size:8.5pt;color:#333;margin-top:18px;border-top:1px solid #000;padding-top:8px}" +
      "@media print{.noprint{display:none}}" +
      "@media screen{.sheet{max-width:820px;margin:0 auto}}" +
      "</style></head><body><div class=\"sheet\">" +
      '<button class="noprint" onclick="window.print()" style="float:right;padding:8px 14px;font:inherit">' +
      "Print / Save as PDF</button>" +
      "<h1>Snorlax collection checklist</h1>" +
      '<div class="meta">Generated ' + today + " · scope: " + scopeLabel +
      " · " + items.length + " items (" + unresolved + " with unresolved finish)" +
      " · paper: " + paper + "</div>" +
      sections +
      '<div class="notice"><strong>Positive evidence only.</strong> This lists printings this ' +
      "project has documented, not everything that exists. An item marked <em>finish unresolved" +
      "</em> is a card whose finish has not been established — it is not a confirmed physical " +
      "version, and must not be treated as one. Absence from this list means no evidence has been " +
      "found, never that a printing does not exist.<br><br>" +
      "Intended data terms: CC BY-NC-SA 4.0; the verbatim text is included in the project, but " +
      "the grant is not operative until the owner records publication approval. Pokémon card " +
      "artwork, images, names and trademarks " +
      "are excluded and remain © Pokémon / Nintendo / Creatures / GAME FREAK. " +
      "Unofficial fan project, not affiliated with or endorsed by any rights holder." +
      "</div></div></body></html>";
  }

  function initChecklist() {
    const languages = Array.from(new Set(CHECKLIST.map((i) => i.language))).sort();
    const editions = Array.from(new Set(CHECKLIST.map((i) => i.edition))).sort();
    const finishes = Array.from(new Set(CHECKLIST.map((i) => collectorFinish(i))))
      .filter((f) => f !== "unresolved").sort();
    const fill = (id, values, labeler) => {
      const select = document.getElementById(id);
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = labeler ? labeler(value) : value;
        select.appendChild(option);
      });
      select.addEventListener("change", updateChecklistPreview);
    };
    fill("cl-langs", languages);
    fill("cl-editions", editions);
    fill("cl-finishes", finishes, finishLabel);
    ["cl-scope", "cl-group", "cl-layout", "cl-paper"].forEach((id) => {
      document.getElementById(id).addEventListener("change", updateChecklistPreview);
    });
    $("#cl-unresolved").addEventListener("change", updateChecklistPreview);

    $("#cl-download").addEventListener("click", () => {
      const html = buildChecklistDocument();
      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "snoredex-checklist-" + new Date().toISOString().slice(0, 10) + ".html";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    });
  }


  function initArtworkReview() {
    const root = $("#artwork-review-app");
    if (!root || !ARTWORK_REVIEW) return;
    const groupsBox = $("#ar-groups");
    const summary = $("#ar-summary");
    const search = $("#ar-search");
    const scope = $("#ar-scope");
    const proposalFilter = $("#ar-proposal-filter");
    const reviewer = $("#ar-reviewer");
    const storageKey = "snoredex-artwork-review-proposals-v1";
    let drafts = {};

    try {
      const saved = window.localStorage.getItem(storageKey);
      if (saved) drafts = JSON.parse(saved) || {};
    } catch (error) { /* Offline/file:// storage may be unavailable. */ }

    const persist = () => {
      try { window.localStorage.setItem(storageKey, JSON.stringify(drafts)); }
      catch (error) { /* The download remains available even without storage. */ }
    };
    const members = () => ARTWORK_REVIEW.groups.flatMap((group) => group.members);
    const memberById = new Map(members().map((member) => [member.cardReleaseId, member]));
    const groupById = new Map(ARTWORK_REVIEW.groups.map((group) => [group.groupId, group]));

    const textFor = (member) => [
      member.cardReleaseId, member.workId, member.locality, member.language, member.localSetCode,
      member.localNumber, member.detection.cardName, member.detection.artist,
      member.detection.variant, member.detection.finish.join(" "),
    ].filter(Boolean).join(" ").toLowerCase();

    const draftFor = (member) => drafts[member.cardReleaseId] || null;
    const draftState = (member) => draftFor(member) ? "reviewed" : "unreviewed";
    const actionLabel = (action) => ({
      confirm: "Confirm group",
      correct: "Correct detection",
      reassign: "Reassign artwork group",
      split: "Split from group",
      unclear: "Mark unclear",
      "propose-variant": "Propose new variant",
    }[action] || action);
    const imageDependentActions = new Set(["confirm", "correct", "reassign", "split", "propose-variant"]);
    const structuredActions = new Set(["correct", "propose-variant"]);
    const hasVerifiedImages = (member) => {
      const images = member.images || [];
      return images.length > 0 && images.every((image) => image && image.src && image.reviewable && image.contentHash);
    };

    const imageHTML = (member) => {
      const images = (member.images || []).filter((image) => image && image.src);
      if (!images.length) return '<div class="artwork-images"><div class="artwork-image missing">No reviewable image recorded</div></div>';
      return '<div class="artwork-images">' + images.map((image, index) =>
        '<figure class="artwork-image"><img loading="lazy" src="' + escapeHTML(image.src) +
        '" alt="' + escapeHTML((member.detection && member.detection.cardName) || member.cardReleaseId) +
        ' — image ' + (index + 1) + '"><figcaption>' + escapeHTML(image.label || 'source image') +
        (image.reviewable && image.contentHash
          ? '<br><code>' + escapeHTML(image.contentHash) + '</code>'
          : '<br><span class="artwork-unverified">image bytes are not pinned</span>') +
        '</figcaption></figure>').join('') + '</div>';
    };

    const evidenceHTML = (member) => {
      const observations = member.observations || [];
      if (!observations.length) return '<p class="artwork-muted">No observation record linked.</p>';
      return '<details class="artwork-evidence"><summary>Evidence (' + observations.length +
        ' observations)</summary><ul>' + observations.map((observation) => {
          const link = observation.url
            ? '<a href="' + escapeHTML(observation.url) + '" target="_blank" rel="noopener nofollow">' +
              escapeHTML(observation.url) + '</a>'
            : '<span>' + escapeHTML(observation.observationId) + '</span>';
          return '<li>' + link + '<br><code>' + escapeHTML(observation.observationId) +
            '</code> <small>hash ' + escapeHTML(observation.contentHash) + '</small>' +
            (observation.evidence ? '<p>' + escapeHTML(observation.evidence) + '</p>' : '') +
            '</li>';
        }).join('') + '</ul></details>';
    };

    const actionOptionsHTML = (selectedAction, imageReviewable) => ["", "confirm", "correct", "reassign", "split", "unclear", "propose-variant"]
      .map((action) => '<option value="' + escapeHTML(action) + '"' +
        (imageDependentActions.has(action) && !imageReviewable ? ' disabled' : '') +
        (selectedAction === action ? ' selected' : '') + '>' +
        escapeHTML(action ? actionLabel(action) : 'Choose a review action') + '</option>').join('');

    const structuredFieldsHTML = (selectedAction, existing, proposed, cleared) => {
      const value = (key) => escapeHTML(Object.prototype.hasOwnProperty.call(proposed, key)
        ? proposed[key] : (cleared.has(key) ? "" : existing[key]));
      const touched = (key) => Object.prototype.hasOwnProperty.call(proposed, key) || cleared.has(key);
      const input = (className, key, placeholder) => '<input class="' + className + '" data-detection-field="' + key +
        '" data-touched="' + (touched(key) ? 'true' : 'false') + '" value="' + value(key) +
        '" placeholder="' + placeholder + '">';
      return '<div class="ar-structured-fields"' +
        (structuredActions.has(selectedAction) ? '' : ' hidden') + '>' +
        '<p class="artwork-muted">Edit a field to set it; clear it to explicitly remove it.</p>' +
        '<label>Card name' + input('ar-proposed-name', 'cardName', 'Corrected card name') + '</label>' +
        '<label>Artist' + input('ar-proposed-artist', 'artist', 'Corrected artist') + '</label>' +
        '<label>Variant identity' + input('ar-proposed-variant', 'variant', 'e.g. V2') + '</label>' +
        '<label>Local set code' + input('ar-proposed-set', 'localSetCode', 'Set code for a new variant') + '</label>' +
        '<label>Local number' + input('ar-proposed-number', 'localNumber', 'Collector number for a new variant') + '</label>' +
        '<label>Finish' + input('ar-proposed-finish', 'finish', 'Finish') + '</label>' +
        '<label>Foil pattern' + input('ar-proposed-foil', 'foilPattern', 'Foil pattern') + '</label>' +
        '<label>Markings' + input('ar-proposed-markings', 'markings', 'Stamp or marking') + '</label></div>';
    };

    const physicalInputsHTML = (physical, physicalIds, selectedPhysicalIds) => physicalIds.length
      ? '<fieldset class="ar-physical-targets"><legend>Affected physical printings</legend>' +
        physical.map((item) => '<label><input class="ar-physical" type="checkbox" value="' +
          escapeHTML(item.physicalPrintingId) + '"' +
          (selectedPhysicalIds.has(item.physicalPrintingId) ? ' checked' : '') + '> <code>' +
          escapeHTML(item.physicalPrintingId) + '</code> · ' + escapeHTML(item.finish || 'printing') +
          '</label>').join('') + '</fieldset>'
      : '<p class="artwork-muted">No physical-printing identity is linked.</p>';

    const detectionSummaryHTML = (detection) => escapeHTML([
      detection.variant, detection.artist, detection.finish && detection.finish.join(', '),
      detection.foilPattern && detection.foilPattern.join(', '),
    ].filter(Boolean).join(' · ') || 'no fields');

    const memberCollections = (member, draft) => {
      const physical = member.physicalPrintings || [];
      const images = member.images || [];
      const imageHashes = images.map((image) => image.contentHash).filter(Boolean);
      const physicalIds = physical.map((item) => item.physicalPrintingId).filter(Boolean);
      const selectedPhysicalIds = new Set(
          draft && Array.isArray(draft.affectedPhysicalPrintingIds)
            ? draft.affectedPhysicalPrintingIds : physicalIds,
      );
      return { physical, images, imageHashes, physicalIds, selectedPhysicalIds };
    };

    const memberExistingFields = (member, detection) => ({
      cardName: detection.cardName || "",
      artist: detection.artist || "",
      variant: detection.variant || "",
      localSetCode: member.localSetCode || "",
      localNumber: member.localNumber || "",
      finish: (detection.finish || []).join(", "),
      foilPattern: (detection.foilPattern || []).join(", "),
      markings: (detection.markings || []).join(", "),
    });

    const memberDetection = (member, draft) => {
      const detection = member.detection || {};
      const proposed = draft && draft.proposedAfter && draft.proposedAfter.detection || {};
      const cleared = new Set(draft && draft.proposedAfter && draft.proposedAfter.clearDetectionFields || []);
      const selectedAction = draft ? draft.action : "";
      return { detection, proposed, cleared, selectedAction,
        existing: memberExistingFields(member, detection) };
    };

    const memberIdentityLabels = (member, detection) => ({
      title: detection.cardName || member.cardReleaseId,
      language: member.language || '—',
      locality: member.locality || '—',
      localSetCode: member.localSetCode || '—',
      localNumber: member.localNumber || '—',
    });

    const memberStatusLabels = (draft) => ({
      statusClass: draft ? 'confirmed' : 'pending',
      statusLabel: draft ? actionLabel(draft.action) : 'unreviewed',
      note: draft && draft.note || '',
    });

    const memberView = (member, draft) => {
      const collections = memberCollections(member, draft);
      const state = memberDetection(member, draft);
      const imageReviewable = hasVerifiedImages(member);
      const identity = memberIdentityLabels(member, state.detection);
      const status = memberStatusLabels(draft);
      const target = draft && draft.proposedAfter ? draft.proposedAfter.targetGroupId || "" : "";
      return {
        member,
        detection: state.detection,
        physical: collections.physical,
        imageHashes: collections.imageHashes,
        identity,
        status,
        target,
        actionOptions: actionOptionsHTML(state.selectedAction, imageReviewable),
        structuredFields: structuredFieldsHTML(
          state.selectedAction, state.existing, state.proposed, state.cleared,
        ),
        physicalInputs: physicalInputsHTML(
          collections.physical, collections.physicalIds, collections.selectedPhysicalIds,
        ),
        detectionSummary: detectionSummaryHTML(state.detection),
        imageWarning: imageReviewable
          ? '' : '<span class="artwork-muted">No verified image hash; only “Mark unclear” can be proposed.</span>',
      };
    };

    const memberMarkup = (view) => '<article class="artwork-member" data-release-id="' + escapeHTML(view.member.cardReleaseId) + '">' +
      imageHTML(view.member) +
      '<div class="artwork-member-body"><h4>' + escapeHTML(view.identity.title) +
      ' <span class="pill ' + view.status.statusClass + '">' +
      escapeHTML(view.status.statusLabel) + '</span></h4>' +
      '<p><strong>' + escapeHTML(view.identity.language) + '</strong> · ' +
      escapeHTML(view.identity.locality) + ' · <code>' + escapeHTML(view.identity.localSetCode) +
      ' ' + escapeHTML(view.identity.localNumber) + '</code><br>' +
      '<small>' + escapeHTML(view.member.cardReleaseId) + '</small></p>' +
      '<dl class="artwork-detection"><dt>Detection</dt><dd>' +
      view.detectionSummary +
      '</dd><dt>Physical printings</dt><dd>' + escapeHTML(String(view.physical.length)) +
      '</dd><dt>Image hash</dt><dd><code>' + escapeHTML(view.imageHashes[0] || 'not available') +
      '</code></dd></dl>' +
      evidenceHTML(view.member) +
      view.physicalInputs + view.structuredFields +
      '<div class="artwork-decision"><label>Decision<select class="ar-action" aria-label="Review action for ' +
      escapeHTML(view.member.cardReleaseId) + '">' + view.actionOptions + '</select></label>' +
      '<label>Target group (for reassign)<input class="ar-target" value="' + escapeHTML(view.target) +
      '" placeholder="APPEARANCE:…" aria-label="Target artwork group"></label>' +
      '<label>Note<textarea class="ar-note" rows="2" placeholder="What did you inspect?">' +
      escapeHTML(view.status.note) + '</textarea></label>' +
      '<button type="button" class="ghost ar-save">Save proposal</button>' +
      view.imageWarning +
      '<span class="artwork-save-status" role="status"></span></div></div></article>';

    const memberHTML = (group, member) => {
      return memberMarkup(memberView(member, draftFor(member)));
    };

    const groupHTML = (group) => '<article class="artwork-group" data-group-id="' + escapeHTML(group.groupId) +
      '"><header><div><h3>' + escapeHTML(group.label) + '</h3><p><code>' +
      escapeHTML(group.groupId) + '</code> · ' + escapeHTML(group.members.length + ' local releases') +
      '</p></div><span class="pill ' + (group.groupKind === 'mapped-appearance' ? 'confirmed' : 'pending') + '">' +
      escapeHTML(group.groupKind === 'mapped-appearance' ? 'verified artwork appearance' : 'unresolved appearance') +
      '</span></header><div class="artwork-members">' +
      group.members.map((member) => memberHTML(group, member)).join('') + '</div></article>';

    const filteredGroups = () => {
      const needle = search.value.trim().toLowerCase();
      const mode = scope.value;
      const proposalMode = proposalFilter.value;
      return ARTWORK_REVIEW.groups.filter((group) => {
        if (mode === "mapped" && group.groupKind !== "mapped-appearance") return false;
        if (mode === "unmapped" && group.groupKind !== "unmapped-release") return false;
        const groupMatches = !needle || (group.label + " " + group.groupId).toLowerCase().includes(needle);
        const visibleMembers = group.members.filter((member) => {
          if (proposalMode === "reviewed" && !draftFor(member)) return false;
          if (proposalMode === "unreviewed" && draftFor(member)) return false;
          return !needle || groupMatches || textFor(member).includes(needle);
        });
        if (!visibleMembers.length) return false;
        group.__visibleMembers = visibleMembers;
        return true;
      });
    };

    const render = () => {
      const groups = filteredGroups();
      const reviewed = members().filter((member) => draftFor(member)).length;
      summary.textContent = groups.length + ' groups shown · ' + groups.reduce((n, group) => n + group.__visibleMembers.length, 0) +
        ' releases · ' + reviewed + ' proposals saved locally · projection ' + ARTWORK_REVIEW.projectionVersion.slice(0, 12);
      groupsBox.innerHTML = groups.map((group) => {
        const original = group.members;
        group.members = group.__visibleMembers;
        const html = groupHTML(group);
        group.members = original;
        return html;
      }).join('') || '<p class="artwork-muted">No groups match the current filters.</p>';
    };

    const makeProposal = (member, group, card) => {
      const action = $(".ar-action", card).value;
      const targetGroupId = $(".ar-target", card).value.trim();
      const note = $(".ar-note", card).value.trim();
      const name = reviewer.value.trim();
      const status = $(".artwork-save-status", card);
      const imageReviewable = hasVerifiedImages(member);
      if (!name) { status.textContent = "Reviewer name required."; reviewer.focus(); return; }
      if (!action) { status.textContent = "Choose an action first."; return; }
      if (!imageReviewable && imageDependentActions.has(action)) {
        status.textContent = "A reviewable image is required for this action; choose Mark unclear.";
        return;
      }
      if (action === "reassign" && !targetGroupId) { status.textContent = "Target group required."; return; }
      const detection = {};
      const clearDetectionFields = [];
      card.querySelectorAll("[data-detection-field]").forEach((field) => {
        if (field.dataset.touched !== "true") return;
        const key = field.dataset.detectionField;
        const value = field.value.trim();
        if (value) detection[key] = value;
        else clearDetectionFields.push(key);
      });
      if (action === "correct" && !Object.keys(detection).length && !clearDetectionFields.length) {
        status.textContent = "Enter at least one structured corrected value.";
        return;
      }
      if (action === "propose-variant" && !detection.variant) {
        status.textContent = "Variant identity is required for a new variant proposal.";
        return;
      }
      const observationIds = (member.observations || []).map((item) => item.observationId);
      const sourceHashes = (member.observations || []).map((item) => item.contentHash);
      const affectedPhysicalPrintingIds = Array.from(card.querySelectorAll(".ar-physical:checked"))
        .map((input) => input.value);
      drafts[member.cardReleaseId] = {
        proposalId: "PROPOSAL:" + member.cardReleaseId + ":" + Date.now(),
        schema: ARTWORK_REVIEW.proposalSchema,
        schemaVersion: ARTWORK_REVIEW.proposalSchemaVersion,
        projectionVersion: ARTWORK_REVIEW.projectionVersion,
        action,
        groupId: group.groupId,
        affectedCardReleaseIds: [member.cardReleaseId],
        reviewer: name,
        evidenceClass: "human-review",
        sourceObservationIds: observationIds,
        sourceContentHashes: sourceHashes,
        imageHashes: (member.images || []).map((item) => item.contentHash).filter(Boolean),
        affectedPhysicalPrintingIds,
        before: { groupId: group.groupId, workId: member.workId, detection: member.detection },
        proposedAfter: {
          action,
          targetGroupId: targetGroupId || null,
          detection: structuredActions.has(action) ? detection : null,
          clearDetectionFields: structuredActions.has(action) ? clearDetectionFields : [],
          note,
        },
        note,
        createdAt: new Date().toISOString(),
      };
      persist();
      status.textContent = "Saved locally.";
      render();
    };

    root.addEventListener("click", (event) => {
      const button = event.target.closest && event.target.closest(".ar-save");
      if (!button) return;
      const card = button.closest(".artwork-member");
      const member = memberById.get(card && card.dataset.releaseId);
      const group = groupById.get(button.closest(".artwork-group").dataset.groupId);
      if (member && group) makeProposal(member, group, card);
    });
    root.addEventListener("change", (event) => {
      if (!event.target.matches || !event.target.matches(".ar-action")) return;
      const fields = event.target.closest(".artwork-member").querySelector(".ar-structured-fields");
      if (fields) fields.hidden = !structuredActions.has(event.target.value);
    });
    root.addEventListener("input", (event) => {
      if (event.target.matches && event.target.matches("[data-detection-field]")) {
        event.target.dataset.touched = "true";
      }
    });
    [search, scope, proposalFilter].forEach((control) => control.addEventListener("input", render));
    [scope, proposalFilter].forEach((control) => control.addEventListener("change", render));
    $("#ar-clear").addEventListener("click", () => { drafts = {}; persist(); render(); });
    $("#ar-download").addEventListener("click", () => {
      const proposals = Object.values(drafts);
      if (!proposals.length) { summary.textContent = "No proposals saved locally yet."; return; }
      const payload = {
        schema: ARTWORK_REVIEW.proposalSchema,
        schemaVersion: ARTWORK_REVIEW.proposalSchemaVersion,
        projectionVersion: ARTWORK_REVIEW.projectionVersion,
        reviewer: reviewer.value.trim() || proposals[0].reviewer,
        createdAt: new Date().toISOString(),
        proposals,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "snoredex-artwork-review-proposals.json";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    });
    render();
  }

  /* Section navigation (#123): native details owns the disclosure; this only syncs its initial
   * responsive state and closes it after a narrow-screen section link is followed. */
  function initSectionNav() {
    const details = $("#section-nav-disclosure");
    if (!details) return;
    const narrow = window.matchMedia("(max-width: 720px)");
    const sync = () => { details.open = !narrow.matches; };
    sync();
    narrow.addEventListener("change", sync);
    details.addEventListener("click", (event) => {
      if (event.target.closest("a") && narrow.matches) details.open = false;
    });
  }

  /* Per-row disclosure for the narrow breakpoint (#121).
   *
   * Delegated from the tbody rather than bound per row, because render() replaces the whole body on
   * every filter and sort — per-row listeners would be rebound hundreds of times and any open panel
   * would be lost. The rows are re-rendered collapsed, which is intended: after a re-sort the panel
   * would otherwise belong to whichever row happened to land in that position. */
  function initRowDetails() {
    const body = $("#rows");
    if (!body) return;
    const byRowId = new Map(ROWS.map((row) => [row.rowId, row]));

    body.addEventListener("click", (event) => {
      const button = event.target.closest(".rowmore");
      if (!button) return;
      const detailId = button.dataset.detailId;
      let panel = document.getElementById(detailId);

      // Built on first use rather than with every row. Emitting all of them up front added a
      // second <tr> per printing that a reader above the breakpoint never sees — 204 spare rows
      // in the DOM, and enough of them to make the row-counting checks read double.
      if (!panel) {
        const row = byRowId.get(button.dataset.rowId);
        if (!row) return;
        panel = document.createElement("tr");
        panel.className = "rowdetail";
        panel.id = detailId;
        panel.hidden = true;
        const cell = document.createElement("td");
        cell.colSpan = DETAIL_SPAN;
        cell.innerHTML = rowDetailHTML(row);
        panel.appendChild(cell);
        button.closest("tr").after(panel);
      }

      const open = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", open ? "false" : "true");
      button.textContent = open ? "More info" : "Less";
      panel.hidden = open;
    });
  }

  /* Raw export of the current view (#125).
   *
   * TSV rather than CSV on purpose: the values here carry commas routinely — evidence lists, artist
   * names, "Stamp / marking" — and every one of those would need quoting and escaping in CSV. Tabs
   * do not occur in the data, so a tab-separated file needs no quoting rules at all and pastes
   * straight into a spreadsheet. Newlines and stray tabs are still collapsed defensively, because a
   * single one would silently break the row structure of the whole file.
   *
   * Exports what the reader is looking at — current filters, current sort order — since that is the
   * view they asked for. The language matrix becomes one column per language holding yes/no, which
   * is the same information the ticks carry, in a form a spreadsheet can filter. */
  function initExport() {
    const button = $("#export-tsv");
    if (!button) return;
    const clean = (value) => String(value == null ? "" : value).replace(/[\t\r\n]+/g, " ").trim();

    button.addEventListener("click", () => {
      // visibleRows is what render() last produced — already filtered and in the displayed sort
      // order — so the file and the table cannot disagree about what "the current view" means.
      const rows = visibleRows;
      const header = [
        "Release", "Card", "Set", "No.", "Expansion", "Variant", "Variant name", "Rarity",
        "Artist", "Edition", "Finish", "Pattern", "Stamp / marking", "Marking role", "Size",
        "Distribution", "Evidence", "Confirmed languages", "Language count",
      ].concat(LANGS.map((lang) => lang.name));

      const body = rows.map((row) => [
        row.dateDisplay, row.name, row.setCode, row.number || "", row.setName || "",
        row.variant || "", row.variantName || "", row.rarity || "", row.artist || "",
        row.edition || "", (row.finishes || []).map(finishLabel).join("; "),
        (row.patterns || []).map(patternLabel).join("; "), (row.markings || []).join("; "),
        (row.markingRoles || []).join("; "), (row.sizes || []).join("; "),
        (row.distributions || []).join("; "), (row.evidence || []).join("; "),
        row.confirmedLanguages.join("; "), row.confirmedLanguages.length,
      ].concat(LANGS.map((lang) => (row.langCodes.includes(lang.code) ? "yes" : "no")))
        .map(clean).join("\t"));

      // A BOM so a spreadsheet opening this by double-click reads it as UTF-8 rather than as the
      // local 8-bit codepage, which mangles the accented card and artist names.
      const text = "﻿" + [header.join("\t")].concat(body).join("\r\n") + "\r\n";
      const blob = new Blob([text], { type: "text/tab-separated-values;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "snoredex-collection-" + new Date().toISOString().slice(0, 10) + ".tsv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    });
  }


  initTheme();
  initSectionNav();
  initRowDetails();
  initExport();
  readURL();
  buildControls();
  initChecklist();
  initArtworkReview();
  refreshTableOverflow = initTableOverflow();
  refreshClippedCells = initClippedCells();
  refreshStickyHeader = initStickyTableHeader();
  refreshLanguageEvidence = initLanguageEvidence();
  initCardPreview();
  syncControls();
  render();
})();
