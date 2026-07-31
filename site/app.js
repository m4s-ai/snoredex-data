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
  const META = readJSON("data-meta");
  const LANGS = META.languages;

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

  /* --------------------------------------------------------------- theme */

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

  /* ---------------------------------------------------------------- sorting */

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

  /* -------------------------------------------------------------- filtering */

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

  /* ------------------------------------------------------------- URL state */

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

  /* --------------------------------------------------------------- controls */

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

    $$("th button.sort").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.key;
        if (sortKey === key) sortDir = -sortDir;
        else { sortKey = key; sortDir = 1; }
        render();
      });
    });
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

  /* ---------------------------------------------------------------- render */

  let visibleRows = [];

  function pill(text, cls) {
    return '<span class="pill ' + escapeHTML(cls) + '">' + escapeHTML(text) + "</span>";
  }

  function clippedCell(value, classes, rendered) {
    const text = value || "—";
    return '<td class="secondary ' + classes + '"><span class="cell-clip" title="' +
      escapeHTML(text) + '">' + (rendered === undefined ? escapeHTML(text) : rendered) +
      "</span></td>";
  }

  function rowHTML(row) {
    const langCells = LANGS.map((lang) => {
      const has = row.langCodes.includes(lang.code);
      const state = has ? "present" : "absent";
      return '<td class="langcell ' + (has ? "yes" : "no") + '" data-state="' + state +
        '" aria-label="' + escapeHTML(lang.name + ": " + state) + '">' +
        '<span aria-hidden="true">' + (has ? "✓" : "—") + "</span></td>";
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
      '<td class="img">' + image + "</td>" +
      "<td>" + release + "</td>" +
      "<td>" + escapeHTML(row.name) + "</td>" +
      "<td>" + escapeHTML(row.setCode) + "</td>" +
      clippedCell(row.setName, "col-expansion") +
      "<td>" + escapeHTML(row.number || "—") + "</td>" +
      clippedCell(variant, "col-variant") +
      clippedCell(row.rarity || "—", "col-rarity") +
      clippedCell(row.artist || "—", "col-artist") +
      "<td>" + escapeHTML(row.edition) + "</td>" +
      "<td>" + (finishPills || '<span class="pill pending">no evidence</span>') + "</td>" +
      clippedCell(row.patterns.join(", ") || "—", "col-pattern", patternBadges || "—") +
      clippedCell(row.markings.join(", ") || "—", "col-marking") +
      clippedCell(row.markingRoles.join(", ") || "—", "col-marking-role") +
      clippedCell(row.sizes.join(", "), "col-size") +
      clippedCell(row.distributions.join(", ") || "—", "col-distribution") +
      clippedCell(evidence, "col-evidence", row.evidence.map((e) => pill(e, e)).join("") || "—") +
      '<td class="langcount">' + row.confirmedLanguages.length + "</td>" +
      langCells +
      '<td class="corr"><a href="' + escapeHTML(row.correctionUrl) + '" target="_blank" rel="noopener" ' +
      'aria-label="Report a correction for ' + escapeHTML(row.name + " " + row.setCode + " " + (row.number || "")) +
      '">Correction?</a></td>' +
      "</tr>"
    );
  }

  function render() {
    visibleRows = sortRows(ROWS.filter(matches));

    $$("thead th[data-key]").forEach((th) => {
      th.setAttribute("aria-sort",
        th.dataset.key === sortKey ? (sortDir > 0 ? "ascending" : "descending") : "none");
    });

    const body = $("#rows");
    if (!visibleRows.length) {
      body.innerHTML = '<tr><td class="empty" colspan="' + (18 + LANGS.length + 1) +
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
            parts.push('<tr class="yearsep"><td colspan="' + (18 + LANGS.length + 1) + '">' +
              (year === "9999" ? "Undated" : year) + "</td></tr>");
          }
        }
        parts.push(rowHTML(row));
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
    });
  }

  /* ------------------------------------------- clipped-cell disclosure */

  let refreshClippedCells = () => {};

  function initClippedCells() {
    const update = () => {
      $$(".cell-clip").forEach((cell) => {
        if (cell.classList.contains("is-expanded")) return;
        const clipped = cell.scrollWidth > cell.clientWidth + 1;
        if (clipped) {
          const text = cell.getAttribute("title") || cell.textContent.trim();
          cell.dataset.clipped = "true";
          cell.tabIndex = 0;
          cell.setAttribute("role", "button");
          cell.setAttribute("aria-expanded", "false");
          cell.setAttribute("aria-label", text + ". Show full value");
        } else {
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
    window.addEventListener("resize", update);
    return update;
  }

  /* ------------------------------------------ horizontal table affordance */

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

  /* --------------------------------------------- sticky table heading */

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
    $$("button", cloneHead).forEach((button) => { button.tabIndex = -1; });
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

    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    window.addEventListener("snoredex:themechange", schedule);
    scroller.addEventListener("scroll", schedule, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(schedule).observe(scroller);
    sync();
    return sync;
  }

  /* ---------------------------------------------------- card image preview */

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

  /* ------------------------------------------------------- checklist builder */

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

  /* ------------------------------------------------------------------ boot */

  initTheme();
  readURL();
  buildControls();
  initChecklist();
  refreshTableOverflow = initTableOverflow();
  refreshClippedCells = initClippedCells();
  refreshStickyHeader = initStickyTableHeader();
  initCardPreview();
  syncControls();
  render();
})();
