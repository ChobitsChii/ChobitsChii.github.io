"use strict";

// Mirrors the Chii Arcade Android client's restricted public WebP image paths.
const MEDIA_PATTERN = /^https:\/\/chobitschii\.github\.io\/chii-arcade\/assets\/([a-z0-9-]+)\/[a-zA-Z0-9_-]+-[a-f0-9]{12}\.webp$/;
const RELEASE_PATTERN = /^https:\/\/github\.com\/ChobitsChii\/chii-arcade-releases\/releases\/download\/store-v[\w.-]+\/chii-arcade-v[\w.-]+\.apk$/;

function trustedImageUrl(gameId, value) {
  if (typeof value !== "string") return null;
  const match = MEDIA_PATTERN.exec(value);
  return match && match[1] === gameId ? value : null;
}

function gameScreenshots(game) {
  if (!Array.isArray(game.screenshots)) return [];
  return game.screenshots.slice(0, 8)
    .map(url => trustedImageUrl(game.id, url))
    .filter(Boolean);
}

function node(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = String(content);
  return element;
}

function picture(game, url, imageClass, alt, loading = "lazy") {
  const image = node("img", imageClass);
  image.src = url;
  image.alt = alt;
  image.loading = loading;
  image.decoding = "async";
  image.addEventListener("error", () => { image.hidden = true; });
  return image;
}

let currentGallery = null;
let returnFocus = null;

function showPhoto() {
  if (!currentGallery) return;
  const { game, shots, index } = currentGallery;
  const shown = document.getElementById("gallery-image");
  shown.src = shots[index];
  shown.alt = game.title + " – Screenshot " + (index + 1) + " von " + shots.length;
  document.getElementById("gallery-title").textContent = game.title + " – Screenshots";
  document.getElementById("gallery-counter").textContent = (index + 1) + " / " + shots.length;
  document.getElementById("gallery-prev").disabled = index === 0;
  document.getElementById("gallery-next").disabled = index === shots.length - 1;
}

function movePhoto(step) {
  if (!currentGallery) return;
  currentGallery.index = Math.max(0, Math.min(
    currentGallery.shots.length - 1, currentGallery.index + step
  ));
  showPhoto();
}

function openGallery(game, shots, index, trigger) {
  if (!shots.length) return;
  const dialog = document.getElementById("screenshot-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  currentGallery = { game, shots, index: Math.max(0, Math.min(shots.length - 1, index)) };
  returnFocus = trigger;
  showPhoto();
  dialog.showModal();
  document.body.classList.add("gallery-open");
  document.getElementById("gallery-close").focus();
}

function renderGame(game) {
  const article = node("article", "game");
  const shots = gameScreenshots(game);
  const coverUrl = trustedImageUrl(game.id, game.coverImage);
  const cover = node(shots.length ? "button" : "div", "game-cover");
  if (shots.length) {
    cover.type = "button";
    cover.setAttribute("aria-label", game.title + ": Screenshots ansehen");
    cover.addEventListener("click", () => openGallery(game, shots, 0, cover));
  }
  cover.appendChild(node("div", "game-cover-fallback", game.symbol || "🎮"));
  if (coverUrl) {
    const image = picture(game, coverUrl, "", game.title + " – Store-Cover");
    cover.appendChild(image);
  }
  article.appendChild(cover);

  const content = node("div", "game-content");
  const meta = node("div", "game-topline");
  meta.appendChild(node("span", "game-category", game.category || "Spiel"));
  if (game.androidRelease && game.androidRelease.versionName) {
    meta.appendChild(node("span", "game-version", "Android " + game.androidRelease.versionName));
  }
  content.appendChild(meta);
  content.appendChild(node("h3", "game-title", game.title));
  content.appendChild(node("p", "game-teaser", game.teaser));

  if (typeof game.description === "string" && game.description.trim()) {
    const details = node("details", "game-description");
    details.appendChild(node("summary", "", "Mehr über das Spiel"));
    details.appendChild(node("p", "", game.description));
    content.appendChild(details);
  }

  if (shots.length) {
    content.appendChild(node("h4", "game-shots-title", "Screenshots"));
    const thumbnails = node("div", "screenshot-strip");
    thumbnails.setAttribute("aria-label", game.title + " – Screenshots");
    shots.forEach((url, index) => {
      const button = node("button", "screenshot-thumb");
      button.type = "button";
      button.setAttribute("aria-label", "Screenshot " + (index + 1) + " von " + shots.length + " öffnen");
      button.title = "Screenshot " + (index + 1) + " ansehen";
      button.appendChild(picture(game, url, "", game.title + " – Screenshot " + (index + 1)));
      button.appendChild(node("span", "", index + 1 + " / " + shots.length));
      button.addEventListener("click", () => openGallery(game, shots, index, button));
      thumbnails.appendChild(button);
    });
    content.appendChild(thumbnails);
    content.appendChild(node("p", "game-shots-hint", "Zum Vergrößern antippen · danach wischen oder blättern"));
  }
  article.appendChild(content);
  return article;
}

async function getJSON(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error("HTTP " + response.status);
  return response.json();
}

async function showStore() {
  const status = document.getElementById("download-status");
  try {
    const metadata = await getJSON("./store-release.json");
    const release = metadata.release;
    if (release && RELEASE_PATTERN.test(release.apkUrl)) {
      const anchor = node("a", "button", "Chii Arcade " + release.versionName + " herunterladen");
      anchor.href = release.apkUrl;
      document.getElementById("download").replaceChildren(anchor);
      status.textContent = "Aktuelle Android-Version " + release.versionName + ".";
    } else {
      status.textContent = "Der öffentliche Download ist momentan nicht verfügbar.";
    }
  } catch (_) {
    status.textContent = "Der Store-Download ist momentan nicht verfügbar.";
  }
}

async function showGames() {
  const root = document.getElementById("games");
  try {
    const catalog = await getJSON("./catalog-v1.json");
    if (!catalog || !Array.isArray(catalog.games)) throw new Error("Invalid catalog");
    const games = catalog.games.filter(g => !g.preview && g.androidRelease);
    root.replaceChildren();
    games.forEach(game => root.appendChild(renderGame(game)));
    if (!games.length) root.textContent = "Noch keine Spiele veröffentlicht.";
  } catch (_) {
    root.textContent = "Der Spielekatalog konnte nicht geladen werden.";
  }
}

function setupGallery() {
  const dialog = document.getElementById("screenshot-dialog");
  document.getElementById("gallery-close").addEventListener("click", () => dialog.close());
  document.getElementById("gallery-prev").addEventListener("click", () => movePhoto(-1));
  document.getElementById("gallery-next").addEventListener("click", () => movePhoto(1));
  dialog.addEventListener("keydown", event => {
    if (event.key === "ArrowLeft") { event.preventDefault(); movePhoto(-1); }
    if (event.key === "ArrowRight") { event.preventDefault(); movePhoto(1); }
    // Escape is handled by the native dialog element.
  });
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    document.body.classList.remove("gallery-open");
    currentGallery = null;
    document.getElementById("gallery-image").removeAttribute("src");
    if (returnFocus && returnFocus.isConnected) returnFocus.focus();
    returnFocus = null;
  });

  // Use directional swipe recognition; vertical scrolling is left to the browser.
  const stage = dialog.querySelector(".viewer-stage");
  let start = null;
  stage.addEventListener("touchstart", event => {
    if (event.touches.length === 1) {
      start = { x: event.touches[0].clientX, y: event.touches[0].clientY };
    } else start = null;
  }, { passive: true });
  stage.addEventListener("touchend", event => {
    if (!start || event.changedTouches.length !== 1) return;
    const dx = event.changedTouches[0].clientX - start.x;
    const dy = event.changedTouches[0].clientY - start.y;
    start = null;
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.2) {
      movePhoto(dx < 0 ? 1 : -1);
    }
  }, { passive: true });
  stage.addEventListener("touchcancel", () => { start = null; }, { passive: true });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    setupGallery();
    showStore();
    showGames();
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { trustedImageUrl, gameScreenshots };
}
