import { whoami } from "/js/api.js";
import { streamSSE } from "/js/stream.js";

const whoEl = document.getElementById("who");
const form = document.getElementById("search-form");
const resultsEl = document.getElementById("results");
const button = document.getElementById("search-btn");

whoami().then((info) => {
  if (info) whoEl.textContent = `Logged in as ${info.display_name}`;
});

function splitCSV(value) {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function multiSelectValues(select) {
  return Array.from(select.selectedOptions).map((o) => o.value);
}

function buildPayload() {
  const fd = new FormData(form);
  const priceRaw = fd.get("price_ceiling");
  return {
    neighborhoods: splitCSV(fd.get("neighborhoods") ?? ""),
    boroughs: multiSelectValues(form.elements.boroughs),
    cuisines: splitCSV(fd.get("cuisines") ?? ""),
    vibes: multiSelectValues(form.elements.vibes),
    price_ceiling: priceRaw ? parseInt(priceRaw, 10) : null,
    preferences_text: fd.get("preferences_text") ?? "",
  };
}

function priceLabel(tier) {
  if (!tier) return "";
  return "$".repeat(tier);
}

function bookingAction(card) {
  if (card.booking_platform === "resy" && card.resy_venue_id) {
    return {
      href: card.booking_url ?? `https://resy.com/cities/ny/${card.id}`,
      label: "Book on Resy",
    };
  }
  if (card.booking_url) {
    return { href: card.booking_url, label: "Book" };
  }
  if (card.booking_platform === "walk_in") {
    return { href: null, label: "Walk-in" };
  }
  return { href: null, label: "" };
}

function sourceChip(source) {
  const chip = document.createElement("span");
  chip.className = "source-chip";
  chip.textContent = source.list_name
    ? `${source.publication} · ${source.list_name}`
    : source.publication;
  if (source.blurb) chip.title = source.blurb;
  return chip;
}

function renderCard(candidate, reason) {
  const card = document.createElement("article");
  card.className = "card";
  card.dataset.id = candidate.id;

  const header = document.createElement("header");
  const title = document.createElement("h2");
  title.textContent = candidate.name;
  header.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "meta";
  const bits = [candidate.neighborhood, candidate.borough, priceLabel(candidate.price_tier)].filter(
    Boolean,
  );
  meta.textContent = bits.join(" · ");
  header.appendChild(meta);

  card.appendChild(header);

  const why = document.createElement("p");
  why.className = "why";
  why.dataset.role = "reason";
  why.textContent = reason || "…";
  card.appendChild(why);

  const tags = document.createElement("p");
  tags.className = "tags";
  tags.textContent = [...candidate.cuisine_tags, ...candidate.vibe_tags].join(" · ");
  card.appendChild(tags);

  const chips = document.createElement("div");
  chips.className = "chips";
  for (const s of candidate.sources ?? []) chips.appendChild(sourceChip(s));
  card.appendChild(chips);

  const action = bookingAction(candidate);
  if (action.href) {
    const a = document.createElement("a");
    a.href = action.href;
    a.className = "btn-primary";
    a.textContent = action.label;
    a.target = "_blank";
    a.rel = "noopener";
    card.appendChild(a);
  } else if (action.label) {
    const span = document.createElement("span");
    span.className = "pill";
    span.textContent = action.label;
    card.appendChild(span);
  }

  return card;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  resultsEl.innerHTML = "<p>Searching&hellip;</p>";
  try {
    const payload = buildPayload();
    let candidatesById = new Map();
    const renderedIds = new Set();
    for await (const evt of streamSSE("/api/search/stream", payload)) {
      if (evt.event === "candidates") {
        candidatesById = new Map(evt.data.candidates.map((c) => [c.id, c]));
      } else if (evt.event === "card") {
        const candidate = candidatesById.get(evt.data.id);
        if (!candidate) continue;
        if (renderedIds.size === 0) resultsEl.innerHTML = "";
        if (renderedIds.has(evt.data.id)) {
          const existing = resultsEl.querySelector(
            `[data-id="${evt.data.id}"] [data-role="reason"]`,
          );
          if (existing) existing.textContent = evt.data.reason || existing.textContent;
        } else {
          renderedIds.add(evt.data.id);
          resultsEl.appendChild(renderCard(candidate, evt.data.reason));
        }
      } else if (evt.event === "done") {
        if (renderedIds.size === 0) {
          resultsEl.innerHTML = "<p>No matches. Try relaxing your filters.</p>";
        }
      }
    }
  } catch (err) {
    resultsEl.innerHTML = `<p class="error">${err.message}</p>`;
  } finally {
    button.disabled = false;
  }
});
