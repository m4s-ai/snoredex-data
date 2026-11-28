"use strict";

// Platform glyphs from Simple Icons 16.38.1 (CC0-1.0, https://simpleicons.org); the marks themselves are
// trademarks of Meta, shown unmodified in one plain colour to link to our own posts (THIRD_PARTY_NOTICES.md).
const SOCIAL_ICONS = {
  Instagram: "M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077",
  Facebook: "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z",
  Threads: "M18.263 11.097c-.03-3.486-1.92-5.586-5.111-5.586-2.13 0-3.922.963-4.863 2.499l2.062 1.438c.535-.843 1.272-1.543 2.628-1.543 1.528 0 2.318.85 2.544 2.431a15 15 0 0 0-2.236-.173c-4.125 0-6.068 1.867-6.068 4.336s1.943 3.99 4.804 3.99c3.139 0 5.013-2.115 5.781-4.735.798.361 1.348 1.204 1.348 2.47 0 3.387-3.907 5.232-7.22 5.232-4.885 0-8.077-3.207-8.077-8.424 0-6.392 4.223-10.487 9.9-10.487 3.808 0 5.69 1.671 6.97 3.914l2.108-1.475C21.44 2.078 18.331 0 13.663 0 6.227 0 1.168 5.277 1.168 12.934c0 7 4.953 11.066 10.856 11.066 4.878 0 9.809-2.846 9.809-7.716 0-2.545-1.46-4.231-3.569-5.187m-6.33 4.855c-1.077 0-2.026-.512-2.026-1.453 0-1.483 1.822-1.934 3.606-1.934.678 0 1.34.045 1.927.173-.422 1.927-1.671 3.215-3.508 3.214Z",
};

// Link text names the site, never the full URL (owner, 2026-11-28); the link itself keeps the full URL.
// Keys are a whole host or the label before the registrable suffix (`ebay` covers ebay.de and ebay.co.uk).
const SITE_NAMES = {
  "asia.pokemon-card.com": "Pokémon Card Asia", "pokemon-card.com": "Pokémon Card Japan",
  "play.pokemon.com": "Play! Pokémon", "pokemon.cn": "Pokémon China", "drive.google.com": "Google Drive",
  "web.archive.org": "Wayback Machine", "auctions.yahoo.co.jp": "Yahoo! Auctions",
  "paypayfleamarket.yahoo.co.jp": "PayPay Flea Market", "efour.b-cdn.net": "Elite Fourum",
  "52poke": "52Poké", archive: "Internet Archive", beehivetcg: "Beehive TCG", bulbagarden: "Bulbapedia",
  bunjang: "Bunjang", cardmarket: "Cardmarket", cgccards: "CGC", collectory: "Collectory", ebay: "eBay",
  ebayimg: "eBay", elitefourum: "Elite Fourum", excaliburtcg: "Excalibur TCG", gamespress: "Pokémon Press",
  github: "GitHub", githubusercontent: "GitHub", globalbunjang: "Bunjang", imgur: "Imgur",
  instagram: "Instagram", limitlesstcg: "Limitless TCG", pikaqian: "PikaQian", pkparaiso: "PKParaiso",
  pokecardex: "PokéCardex", pokemon: "Pokémon", pokemoncard: "Pokémon Card Korea",
  pokemonkorea: "Pokémon Korea", pokepedia: "Poképédia", pokewiki: "PokéWiki", pokumon: "Pokumon",
  psacard: "PSA", shopee: "Shopee", snkrdunk: "SNKRDUNK", susercontent: "Shopee", target: "Target",
  tcgcsv: "TCGCSV", tcgdex: "TCGdex", vinted: "Vinted", wikidex: "WikiDex", yahoo: "Yahoo! Japan",
  yimg: "Yahoo! Auctions",
};

function siteName(url) {
  let host;
  try {
    host = new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
  const labels = host.split(".");
  const cut = labels.length > 2 && /^(?:co|com|or|ne|go|ac)$/.test(labels.at(-2)) ? 3 : 2;
  return SITE_NAMES[host] || SITE_NAMES[labels.at(-cut)] || labels.slice(-cut).join(".");
}

// [label, url] pairs; a second link to the same site reads "eBay 2".
function siteLinks(urls) {
  const seen = new Map();
  return urls.map((url) => {
    const name = siteName(url);
    const count = (seen.get(name) || 0) + 1;
    seen.set(name, count);
    return [count > 1 ? `${name} ${count}` : name, url];
  });
}

// Keep the accepted permalink forms aligned with scripts/card_pages.py.
function socialPosts(entry) {
  const platforms = [
    ["instagramPosts", "Instagram", /^https:\/\/www\.instagram\.com\/(?:p|reel)\/[A-Za-z0-9_-]+\/$/],
    ["facebookPosts", "Facebook", /^https:\/\/www\.facebook\.com\/[A-Za-z0-9_./?=&%-]+$/],
    ["threadsPosts", "Threads", /^https:\/\/www\.threads\.(?:net|com)\/@[A-Za-z0-9_.]+\/post\/[A-Za-z0-9_-]+\/?$/],
  ];
  return platforms.flatMap(([field, label, pattern]) =>
    (Array.isArray(entry?.[field]) ? entry[field] : [])
      .filter((url) => typeof url === "string" && pattern.test(url))
      .map((url, index) => [`${label} post ${index + 1}`, url, label]));
}

// A post link shows the platform's glyph; its accessible name and tooltip stay "Instagram post 1".
function socialLink(label, url, platform) {
  const link = document.createElement("a");
  link.href = url;
  link.className = "post-icon";
  link.title = label;
  link.setAttribute("aria-label", label);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", SOCIAL_ICONS[platform]);
  svg.append(path);
  link.append(svg);
  return link;
}
