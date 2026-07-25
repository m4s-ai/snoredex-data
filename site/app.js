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

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

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
    variant: (r) => (r.variant || "").toLowerCase(),
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
    setCode: [],
    edition: [],
    rarity: [],
    artist: [],
    finish: [],
    pattern: [],
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

  const MULTI = ["setCode", "edition", "rarity", "artist", "finish", "pattern",
    "markingRole", "size", "distribution", "evidence"];

  const ROW_FIELD = {
    setCode: (r) => [r.setCode],
    edition: (r) => [r.edition],
    rarity: (r) => [r.rarity || ""],
    artist: (r) => [r.artist || ""],
    finish: (r) => r.finishes,
    pattern: (r) => r.patterns,
    markingRole: (r) => r.markingRoles,
    size: (r) => r.sizes,
    distribution: (r) => r.distributions,
    evidence: (r) => r.evidence,
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
        option.textContent = value;
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
      wrap.innerHTML =
        '<label for="' + id + '">' + lang.code + "</label>" +
        '<select id="' + id + '"><option value="">any</option>' +
        '<option value="present">present</option><option value="absent">absent</option></select>';
      langGrid.appendChild(wrap);
      wrap.querySelector("select").addEventListener("change", (event) => {
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
    return '<span class="pill ' + cls + '">' + text + "</span>";
  }

  function rowHTML(row) {
    const langCells = LANGS.map((lang) => {
      const has = row.langCodes.includes(lang.code);
      return '<td class="langcell ' + (has ? "yes" : "no") + '">' + (has ? "●" : "·") + "</td>";
    }).join("");
    const finishPills = row.finishDisplay.map((f) => pill(f.label, f.status)).join("");
    return (
      "<tr>" +
      '<td class="img">' + (row.image ? '<img loading="lazy" src="' + row.image + '" alt="' + row.name + '">' : "") + "</td>" +
      "<td>" + row.dateDisplay + "</td>" +
      "<td>" + row.name + "</td>" +
      "<td>" + row.setCode + "</td>" +
      '<td class="secondary">' + row.setName + "</td>" +
      "<td>" + (row.number || "—") + "</td>" +
      '<td class="secondary">' + row.variant + (row.variantName ? "<br><small>" + row.variantName + "</small>" : "") + "</td>" +
      '<td class="secondary">' + (row.rarity || "—") + "</td>" +
      '<td class="secondary">' + (row.artist || "—") + "</td>" +
      "<td>" + row.edition + "</td>" +
      "<td>" + (finishPills || '<span class="pill pending">no evidence</span>') + "</td>" +
      '<td class="secondary">' + (row.patterns.join(", ") || "—") + "</td>" +
      '<td class="secondary">' + (row.markings.join(", ") || "—") + "</td>" +
      '<td class="secondary">' + (row.markingRoles.join(", ") || "—") + "</td>" +
      '<td class="secondary">' + row.sizes.join(", ") + "</td>" +
      '<td class="secondary">' + (row.distributions.join(", ") || "—") + "</td>" +
      '<td class="secondary">' + row.evidence.map((e) => pill(e, e)).join("") + "</td>" +
      '<td class="langcell">' + row.confirmedLanguages.length + "</td>" +
      langCells +
      '<td class="corr"><a href="' + row.correctionUrl + '" target="_blank" rel="noopener" ' +
      'aria-label="Report a correction for ' + row.name + " " + row.setCode + " " + (row.number || "") +
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
  }

  /* ------------------------------------------------------- checklist builder */

  function checklistSelection() {
    const scope = $("#cl-scope").value;
    const langs = Array.from($("#cl-langs").selectedOptions).map((o) => o.value);
    const editions = Array.from($("#cl-editions").selectedOptions).map((o) => o.value);
    const finishes = Array.from($("#cl-finishes").selectedOptions).map((o) => o.value);
    const includeUnresolved = $("#cl-unresolved").checked;

    let allowedRowIds = null;
    if (scope === "filtered") {
      // Scope follows stable row IDs, never the rendered order.
      allowedRowIds = new Set(visibleRows.map((r) => r.rowId));
    }

    return CHECKLIST.filter((item) => {
      if (allowedRowIds && !allowedRowIds.has(item.rowId)) return false;
      if (langs.length && !langs.includes(item.language)) return false;
      if (editions.length && !editions.includes(item.edition)) return false;
      if (item.finish === "unresolved") return includeUnresolved;
      if (finishes.length && !finishes.includes(item.finish)) return false;
      return true;
    });
  }

  function updateChecklistPreview() {
    const items = checklistSelection();
    const unresolved = items.filter((i) => i.finish === "unresolved").length;
    $("#cl-preview").innerHTML =
      "<strong>" + items.length + "</strong> checklist items — " +
      (items.length - unresolved) + " documented printings, " +
      unresolved + " with unresolved finish.";
  }

  function groupKey(item, mode) {
    if (mode === "set") return item.setCode + " — " + item.setName;
    if (mode === "card") return item.cardName + " (" + item.setCode + " " + (item.number || "—") + ")";
    if (mode === "language") return item.language;
    return (item.releaseDate || "undated") + " — " + item.setName;
  }

  function escapeHTML(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function buildChecklistDocument() {
    const items = checklistSelection();
    const mode = $("#cl-group").value;
    const compact = $("#cl-layout").value === "compact";
    const today = new Date().toISOString().slice(0, 10);

    const groups = new Map();
    items.forEach((item) => {
      const key = groupKey(item, mode);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });

    const sections = Array.from(groups.entries()).map(([heading, list]) => {
      const rows = list.map((item) => {
        const detail = [
          item.language,
          item.edition !== "—" ? item.edition : null,
          item.finish === "unresolved"
            ? "<em>finish unresolved — not a confirmed version</em>"
            : escapeHTML(item.finish),
          item.foilPattern ? "pattern: " + escapeHTML(item.foilPattern) : null,
          item.marking ? "stamp: " + escapeHTML(item.marking) : null,
          item.cardSize && item.cardSize !== "standard" ? escapeHTML(item.cardSize) : null,
        ].filter(Boolean).join(" · ");
        const image = !compact && item.image
          ? '<img src="' + escapeHTML(item.image) + '" alt="">' : "";
        return '<tr class="' + (item.finish === "unresolved" ? "unresolved" : "") + '">' +
          '<td class="box"><span class="cb"></span></td>' +
          (compact ? "" : '<td class="thumb">' + image + "</td>") +
          "<td><strong>" + escapeHTML(item.cardName) + "</strong> — " +
          escapeHTML(item.setCode) + " " + escapeHTML(item.number || "—") +
          "<br><small>" + detail + "</small></td>" +
          "</tr>";
      }).join("");
      return "<section><h2>" + escapeHTML(heading) + "</h2><table>" + rows + "</table></section>";
    }).join("");

    const unresolved = items.filter((i) => i.finish === "unresolved").length;
    const scopeLabel = $("#cl-scope").value === "filtered"
      ? "current filtered table rows" : "all documented items";

    return "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">" +
      '<meta name="viewport" content="width=device-width,initial-scale=1">' +
      "<title>Snoredex checklist " + today + "</title><style>" +
      "@page{size:A4;margin:14mm}" +
      "body{font:11pt/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;" +
      "color:#000;background:#fff;margin:0;padding:16px}" +
      "h1{font-size:17pt;margin:0 0 4px}h2{font-size:12pt;margin:16px 0 4px;border-bottom:1px solid #000;" +
      "page-break-after:avoid}" +
      ".meta{font-size:9pt;color:#333;margin-bottom:12px}" +
      "table{width:100%;border-collapse:collapse}" +
      "tr{page-break-inside:avoid;break-inside:avoid}" +
      "td{padding:3px 4px;border-bottom:1px solid #bbb;vertical-align:top}" +
      "td.box{width:20px}td.thumb{width:42px}td.thumb img{width:38px;height:auto}" +
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
      " · paper: A4 and US Letter</div>" +
      sections +
      '<div class="notice"><strong>Positive evidence only.</strong> This lists printings this ' +
      "project has documented, not everything that exists. An item marked <em>finish unresolved" +
      "</em> is a card whose finish has not been established — it is not a confirmed physical " +
      "version, and must not be treated as one. Absence from this list means no evidence has been " +
      "found, never that a printing does not exist.<br><br>" +
      "Data: snoredex-data, noncommercial — original selection, arrangement and verification " +
      "annotations under CC BY-NC-SA 4.0. Pokémon card artwork, images, names and trademarks " +
      "are excluded and remain © Pokémon / Nintendo / Creatures / GAME FREAK. " +
      "Unofficial fan project, not affiliated with or endorsed by any rights holder." +
      "</div></div></body></html>";
  }

  function initChecklist() {
    const languages = Array.from(new Set(CHECKLIST.map((i) => i.language))).sort();
    const editions = Array.from(new Set(CHECKLIST.map((i) => i.edition))).sort();
    const finishes = Array.from(new Set(CHECKLIST.map((i) => i.finish)))
      .filter((f) => f !== "unresolved").sort();
    const fill = (id, values) => {
      const select = document.getElementById(id);
      values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
      select.addEventListener("change", updateChecklistPreview);
    };
    fill("cl-langs", languages);
    fill("cl-editions", editions);
    fill("cl-finishes", finishes);
    ["cl-scope", "cl-group", "cl-layout"].forEach((id) => {
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

  readURL();
  buildControls();
  initChecklist();
  syncControls();
  render();
})();
