"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { trustedImageUrl, gameScreenshots } = require("../storefront.js");

const base = "https://chobitschii.github.io/chii-arcade/assets/kaskellia/";
const cover = base + "cover-e9ced9459ef7.webp";
const screenshots = [
  "screenshot-01-ac671da7c467.webp",
  "screenshot-02-a4cc9e1a240e.webp",
  "screenshot-03-090a72b35735.webp",
  "screenshot-04-26cd449d53a5.webp",
  "screenshot-05-7822cb4d3170.webp",
  "screenshot-06-790b753d4770.webp"
].map(name => base + name);

test("accepts live Kaskellia cover and all six published screenshot URLs", () => {
  assert.equal(trustedImageUrl("kaskellia", cover), cover);
  assert.deepEqual(gameScreenshots({id:"kaskellia", screenshots}), screenshots);
});

test("does not leak foreign hosts, paths, script/data URLs or cross-game assets", () => {
  for (const url of [
    "https://evil.example/cover-e9ced9459ef7.webp",
    "http://chobitschii.github.io/chii-arcade/assets/kaskellia/cover-e9ced9459ef7.webp",
    "https://chobitschii.github.io/chii-arcade/assets/tintaloria/cover-e9ced9459ef7.webp",
    base + "cover-e9ced9459ef7.webp?x=1",
    base + "../cover-e9ced9459ef7.webp",
    "javascript:alert(1)",
    "data:image/webp;base64,AAA",
    null, {}, 1,
  ]) assert.equal(trustedImageUrl("kaskellia", url), null, String(url));
});

test("handles absent or invalid screenshot arrays and limits at eight", () => {
  assert.deepEqual(gameScreenshots({ id: "kaskellia" }), []);
  assert.deepEqual(gameScreenshots({ id: "kaskellia", screenshots: "no" }), []);
  assert.deepEqual(gameScreenshots({ id: "kaskellia", screenshots: [cover, "https://evil.example/bad.webp"] }), [cover]);
  assert.equal(gameScreenshots({id:"kaskellia", screenshots: Array(20).fill(cover)}).length,8);
});

test("HTML references stylesheet, script, download endpoint and accessible viewer", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  for (const required of [
    './storefront.css', './storefront.js', './store-release.json',
    './catalog-v1.json', 'id="games"', 'id="screenshot-dialog"',
    'id="gallery-close"', 'id="gallery-prev"', 'id="gallery-next"',
    'id="gallery-counter"', 'id="gallery-image"',
    'class="brand-icon"', './favicon.ico'
  ]) {
    // The JSON paths are used in the JavaScript module rather than inline HTML.
    if (required.endsWith(".json")) {
      assert.ok(fs.readFileSync(path.join(__dirname, "..", "storefront.js"), "utf8").includes(required), required);
    } else assert.ok(html.includes(required), required);
  }
});

test("footer exposes readable, directly reachable imprint and privacy pages", () => {
  const root = path.join(__dirname, "..");
  const storefront = fs.readFileSync(path.join(root, "index.html"), "utf8");
  assert.match(storefront, /<nav class="footer-nav" aria-label="Rechtliche Informationen">/);
  assert.match(storefront, /href="\.\/impressum\.html"/);
  assert.match(storefront, /href="\.\/datenschutz\.html"/);

  for (const [file, ownTitle, companion] of [
    ["impressum.html", "Impressum", "datenschutz.html"],
    ["datenschutz.html", "Datenschutz", "impressum.html"],
  ]) {
    const html = fs.readFileSync(path.join(root, file), "utf8");
    assert.ok(html.includes("<title>" + ownTitle + " – Chii Arcade</title>"), file);
    for (const required of [
      'href="./storefront.css"', 'chii-arcade-icon.webp',
      'href="./"', 'href="./' + companion + '"',
      "Jennifer Graßl", "webmaster@jgserver.de"
    ]) assert.ok(html.includes(required), file + ": " + required);
  }
  const privacy = fs.readFileSync(path.join(root, "datenschutz.html"), "utf8");
  for (const requirement of [
    "GitHub Pages", "Android-App", "Offline", "APK", "WhatsApp",
    "DSGVO", "Datenschutzrechte", "GitHub"
  ]) assert.ok(privacy.includes(requirement), requirement);
});
