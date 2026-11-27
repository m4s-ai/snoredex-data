"use strict";

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
      .map((url, index) => [`${label} post ${index + 1}`, url]));
}
