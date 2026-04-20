import { checkAvailability, whoami } from "/js/api.js";
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
  const actionRow = document.createElement("div");
  actionRow.className = "action-row";

  if (action.href) {
    const a = document.createElement("a");
    a.href = action.href;
    a.className = "btn-primary";
    a.textContent = action.label;
    a.target = "_blank";
    a.rel = "noopener";
    actionRow.appendChild(a);
  } else if (action.label) {
    const span = document.createElement("span");
    span.className = "pill";
    span.textContent = action.label;
    actionRow.appendChild(span);
  }

  const fd = new FormData(form);
  const date = fd.get("date");
  const timeVal = fd.get("time");
  const party = fd.get("party");
  if (
    candidate.booking_platform === "resy" &&
    candidate.resy_venue_id &&
    date &&
    timeVal &&
    party
  ) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-secondary";
    btn.textContent = "Check availability";
    const slotsEl = document.createElement("div");
    slotsEl.className = "slots";
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      slotsEl.textContent = "Checking…";
      const { status, body } = await checkAvailability({
        restaurantId: candidate.id,
        party,
        date,
        time: timeVal,
      });
      slotsEl.innerHTML = "";
      if (status === 200) {
        if ((body.slots ?? []).length === 0) {
          slotsEl.textContent = "No slots within ±2h. Try another time.";
        } else {
          for (const slot of body.slots) {
            const a = document.createElement("a");
            a.className = "slot-pill";
            a.href = slot.book_url;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = slot.time;
            slotsEl.appendChild(a);
          }
        }
      } else if (status === 400 && body.detail === "use_booking_url") {
        slotsEl.textContent = "Book directly — availability not available here.";
      } else if (status === 404 && body.detail === "venue_not_found") {
        slotsEl.textContent = "Venue missing on Resy. Flagged for review.";
      } else if (status === 503) {
        slotsEl.textContent = "Resy unreachable — try the booking link above.";
      } else {
        slotsEl.textContent = "Could not check availability.";
      }
      btn.disabled = false;
    });
    actionRow.appendChild(btn);
    card.appendChild(actionRow);
    card.appendChild(slotsEl);
    return card;
  }

  card.appendChild(actionRow);
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
