/**
 * admin.js — Admin page for NYC Dining.
 *
 * Handles:
 *  - Restaurant list with status/name filters
 *  - Add-by-URL, Add-by-Name, Manual add forms
 *  - Inline edit, close/resolve, delete per restaurant
 *  - Reseed preview + apply for Eater Essentials
 */

// ---------------------------------------------------------------------------
// Low-level helpers
// ---------------------------------------------------------------------------

/**
 * Perform a JSON API call. Redirects to /login on 401.
 * Returns { ok: boolean, status: number, data: any }.
 */
async function apiCall(method, url, body = null) {
  const opts = {
    method,
    credentials: "same-origin",
    headers: {},
  };
  if (body !== null) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  // 204 No Content has no body
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  return { ok: res.ok, status: res.status, data };
}

/** Split a comma-separated string into a trimmed, non-empty array. */
function splitCSV(str) {
  return (str || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Show/hide a DOM element by toggling the `hidden` attribute. */
function setVisible(el, visible) {
  if (visible) {
    el.removeAttribute("hidden");
  } else {
    el.setAttribute("hidden", "");
  }
}

/** Display an error message in a given element, or clear it. */
function showError(el, msg) {
  if (msg) {
    el.textContent = msg;
    setVisible(el, true);
  } else {
    el.textContent = "";
    setVisible(el, false);
  }
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function statusBadge(status) {
  const span = document.createElement("span");
  span.className = `status-badge status-${status}`;
  span.textContent = status.replace("_", " ");
  return span;
}

// ---------------------------------------------------------------------------
// Restaurant list
// ---------------------------------------------------------------------------

let _listDebounceTimer = null;

async function loadRestaurants() {
  const listEl = document.getElementById("restaurant-list");
  const status = document.getElementById("status-filter").value;
  const q = document.getElementById("search-filter").value.trim();

  const params = new URLSearchParams({ status });
  if (q) params.set("q", q);

  listEl.innerHTML = "<p class='spinner'>Loading…</p>";

  const { ok, data } = await apiCall("GET", `/api/admin/restaurants?${params}`);
  if (!ok) {
    listEl.innerHTML = "<p class='error-msg'>Failed to load restaurants.</p>";
    return;
  }
  renderRestaurantList(listEl, data);
}

function renderRestaurantList(container, restaurants) {
  container.innerHTML = "";
  if (!restaurants.length) {
    container.innerHTML = "<p>No restaurants found.</p>";
    return;
  }
  for (const r of restaurants) {
    container.appendChild(buildRestaurantCard(r));
  }
}

/**
 * Build a restaurant card element with action buttons.
 * The card includes: name, meta line, status badge, source count,
 * and action buttons: Edit, Close/Resolve, Delete.
 */
function buildRestaurantCard(r) {
  const card = document.createElement("div");
  card.className = "admin-card";
  card.dataset.id = r.id;

  // Header row
  const headerRow = document.createElement("div");
  headerRow.style.display = "flex";
  headerRow.style.justifyContent = "space-between";
  headerRow.style.alignItems = "flex-start";

  const titleWrap = document.createElement("div");
  const h3 = document.createElement("h3");
  h3.textContent = r.name;
  titleWrap.appendChild(h3);

  const meta = document.createElement("p");
  meta.className = "meta";
  const bits = [
    r.neighborhood,
    r.borough,
    r.price_tier ? "$".repeat(r.price_tier) : null,
    `${r.source_count} source${r.source_count !== 1 ? "s" : ""}`,
  ].filter(Boolean);
  meta.textContent = bits.join(" · ");
  titleWrap.appendChild(meta);

  headerRow.appendChild(titleWrap);
  headerRow.appendChild(statusBadge(r.status));
  card.appendChild(headerRow);

  // Tags line
  if (r.cuisine_tags.length || r.vibe_tags.length) {
    const tagsEl = document.createElement("p");
    tagsEl.className = "tags";
    tagsEl.style.fontSize = "0.85rem";
    tagsEl.textContent = [...r.cuisine_tags, ...r.vibe_tags].join(" · ");
    card.appendChild(tagsEl);
  }

  // Action buttons
  const actions = document.createElement("div");
  actions.className = "actions";

  // Edit button — toggles an inline edit form
  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "btn-secondary";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => toggleEditForm(card, r));
  actions.appendChild(editBtn);

  // Close or Resolve depending on current status
  if (r.status !== "closed") {
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-warning";
    closeBtn.textContent = "Close";
    closeBtn.addEventListener("click", () => closeRestaurant(r.id));
    actions.appendChild(closeBtn);
  } else {
    const resolveBtn = document.createElement("button");
    resolveBtn.type = "button";
    resolveBtn.className = "btn-success";
    resolveBtn.textContent = "Re-open";
    resolveBtn.addEventListener("click", () => resolveRestaurant(r.id));
    actions.appendChild(resolveBtn);
  }

  // Delete button
  const delBtn = document.createElement("button");
  delBtn.type = "button";
  delBtn.className = "btn-danger";
  delBtn.textContent = "Delete";
  delBtn.addEventListener("click", () => deleteRestaurant(r.id, r.name));
  actions.appendChild(delBtn);

  card.appendChild(actions);
  return card;
}

// ---------------------------------------------------------------------------
// Inline edit form
// ---------------------------------------------------------------------------

/**
 * Toggle an inline edit form below the action buttons on the card.
 * If one already exists, remove it (collapse).
 */
function toggleEditForm(card, r) {
  const existing = card.querySelector(".inline-form");
  if (existing) {
    existing.remove();
    return;
  }

  const form = document.createElement("form");
  form.className = "inline-form";

  // Helper: create a labelled input inside the form
  function field(label, name, value, type = "text") {
    const lbl = document.createElement("label");
    lbl.innerHTML = `<span>${label}</span>`;
    const inp = document.createElement(type === "textarea" ? "textarea" : "input");
    inp.name = name;
    if (type !== "textarea") inp.type = type;
    if (type === "textarea") inp.rows = 2;
    inp.value = value ?? "";
    lbl.appendChild(inp);
    return lbl;
  }

  // Helper: borough select
  function boroughSelect(current) {
    const lbl = document.createElement("label");
    lbl.innerHTML = "<span>Borough</span>";
    const sel = document.createElement("select");
    sel.name = "borough";
    const opts = ["", "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];
    for (const o of opts) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o || "—";
      if (o === (current || "")) opt.selected = true;
      sel.appendChild(opt);
    }
    lbl.appendChild(sel);
    return lbl;
  }

  // Helper: booking platform select
  function platformSelect(current) {
    const lbl = document.createElement("label");
    lbl.innerHTML = "<span>Booking platform</span>";
    const sel = document.createElement("select");
    sel.name = "booking_platform";
    const opts = ["", "resy", "opentable", "tock", "walk_in", "other"];
    for (const o of opts) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o || "—";
      if (o === (current || "")) opt.selected = true;
      sel.appendChild(opt);
    }
    lbl.appendChild(sel);
    return lbl;
  }

  const row1 = document.createElement("div");
  row1.className = "form-row";
  row1.appendChild(field("Name *", "name", r.name));
  row1.appendChild(field("Price tier", "price_tier", r.price_tier, "number"));
  form.appendChild(row1);

  const row2 = document.createElement("div");
  row2.className = "form-row";
  row2.appendChild(field("Neighborhood", "neighborhood", r.neighborhood));
  row2.appendChild(boroughSelect(r.borough));
  form.appendChild(row2);

  form.appendChild(field("Address", "address", r.address));

  const row3 = document.createElement("div");
  row3.className = "form-row";
  row3.appendChild(platformSelect(r.booking_platform));
  row3.appendChild(field("Resy venue ID", "resy_venue_id", r.resy_venue_id));
  form.appendChild(row3);

  const row4 = document.createElement("div");
  row4.className = "form-row";
  row4.appendChild(field("Booking URL", "booking_url", r.booking_url));
  row4.appendChild(field("Website URL", "website_url", r.website_url));
  form.appendChild(row4);

  form.appendChild(field("Description", "description", r.description, "textarea"));
  form.appendChild(field("Cuisine tags (comma-sep)", "cuisine_tags", r.cuisine_tags.join(", ")));
  form.appendChild(field("Vibe tags (comma-sep)", "vibe_tags", r.vibe_tags.join(", ")));
  form.appendChild(field("Feature tags (comma-sep)", "feature_tags", r.feature_tags.join(", ")));

  const errorEl = document.createElement("div");
  errorEl.className = "error-msg";
  errorEl.hidden = true;
  form.appendChild(errorEl);

  // Form buttons
  const btnRow = document.createElement("div");
  btnRow.className = "form-actions";

  const saveBtn = document.createElement("button");
  saveBtn.type = "submit";
  saveBtn.className = "btn-primary";
  saveBtn.textContent = "Save";
  btnRow.appendChild(saveBtn);

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "btn-secondary";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", () => form.remove());
  btnRow.appendChild(cancelBtn);

  form.appendChild(btnRow);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    showError(errorEl, null);
    saveBtn.disabled = true;

    const fd = new FormData(form);
    const payload = {};
    for (const [k, v] of fd.entries()) {
      const s = v.toString().trim();
      if (k === "price_tier") {
        payload[k] = s ? parseInt(s, 10) : null;
      } else if (k === "cuisine_tags" || k === "vibe_tags" || k === "feature_tags") {
        payload[k] = splitCSV(s);
      } else {
        payload[k] = s || null;
      }
    }

    const { ok, data } = await apiCall("PUT", `/api/admin/restaurants/${r.id}`, payload);
    if (!ok) {
      showError(errorEl, data?.detail || "Save failed.");
      saveBtn.disabled = false;
      return;
    }
    // Reload list to reflect the edit
    loadRestaurants();
  });

  card.appendChild(form);
}

// ---------------------------------------------------------------------------
// Close / Resolve / Delete
// ---------------------------------------------------------------------------

async function closeRestaurant(id) {
  const { ok } = await apiCall("POST", `/api/admin/restaurants/${id}/close`);
  if (ok) loadRestaurants();
}

async function resolveRestaurant(id) {
  const { ok } = await apiCall("POST", `/api/admin/restaurants/${id}/resolve`);
  if (ok) loadRestaurants();
}

async function deleteRestaurant(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  const { ok } = await apiCall("DELETE", `/api/admin/restaurants/${id}`);
  if (ok) loadRestaurants();
}

// ---------------------------------------------------------------------------
// Filter controls
// ---------------------------------------------------------------------------

document.getElementById("status-filter").addEventListener("change", () => loadRestaurants());

document.getElementById("search-filter").addEventListener("input", () => {
  // Debounce: wait 300 ms after user stops typing
  clearTimeout(_listDebounceTimer);
  _listDebounceTimer = setTimeout(loadRestaurants, 300);
});

// ---------------------------------------------------------------------------
// Tab switcher (By URL / By Name / Manual)
// ---------------------------------------------------------------------------

const addUrlForm = document.getElementById("add-url-form");
const addNameForm = document.getElementById("add-name-form");
const prefillFormWrap = document.getElementById("prefill-form-wrap");

function activateTab(tabId) {
  for (const t of document.querySelectorAll(".tab")) {
    t.classList.toggle("active", t.id === tabId);
  }
  setVisible(addUrlForm, tabId === "tab-url");
  setVisible(addNameForm, tabId === "tab-name");
  // Manual tab shows the prefill form directly (blank)
  if (tabId === "tab-manual") {
    clearPrefillForm();
    document.getElementById("prefill-heading").textContent = "New Restaurant";
    setVisible(prefillFormWrap, true);
  } else if (!prefillFormWrap.dataset.populated) {
    setVisible(prefillFormWrap, false);
  }
}

document.getElementById("tab-url").addEventListener("click", () => activateTab("tab-url"));
document.getElementById("tab-name").addEventListener("click", () => activateTab("tab-name"));
document.getElementById("tab-manual").addEventListener("click", () => activateTab("tab-manual"));

// ---------------------------------------------------------------------------
// Prefill form helpers
// ---------------------------------------------------------------------------

function clearPrefillForm() {
  const form = document.getElementById("prefill-form");
  form.reset();
  delete prefillFormWrap.dataset.populated;
  showError(document.getElementById("prefill-error"), null);
  setVisible(document.getElementById("prefill-success"), false);
}

/**
 * Populate the prefill form with data returned from add-by-url or add-by-name.
 * `seed` is a SeedRestaurant-shaped dict.
 */
function populatePrefillForm(seed) {
  const form = document.getElementById("prefill-form");

  function set(name, value) {
    const el = form.elements[name];
    if (!el) return;
    if (value === null || value === undefined) {
      el.value = "";
    } else if (Array.isArray(value)) {
      el.value = value.join(", ");
    } else {
      el.value = value;
    }
  }

  set("name", seed.name);
  set("address", seed.address);
  set("neighborhood", seed.neighborhood);
  set("borough", seed.borough);
  set("price_tier", seed.price_tier);
  set("booking_platform", seed.booking_platform);
  set("resy_venue_id", seed.resy_venue_id);
  set("booking_url", seed.booking_url);
  set("website_url", seed.website_url);
  set("description", seed.description);
  set("cuisine_tags", seed.cuisine_tags);
  set("vibe_tags", seed.vibe_tags);
  set("feature_tags", seed.feature_tags);

  prefillFormWrap.dataset.populated = "1";
  document.getElementById("prefill-heading").textContent = "Review & Save";
  setVisible(prefillFormWrap, true);
  prefillFormWrap.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Cancel / hide the prefill form. */
document.getElementById("prefill-cancel").addEventListener("click", () => {
  clearPrefillForm();
  setVisible(prefillFormWrap, false);
});

/**
 * Submit the prefill form — POST to /api/admin/restaurants, then reload list.
 */
document.getElementById("prefill-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("prefill-error");
  const successEl = document.getElementById("prefill-success");
  showError(errorEl, null);
  setVisible(successEl, false);

  const fd = new FormData(e.target);
  const payload = {};
  for (const [k, v] of fd.entries()) {
    const s = v.toString().trim();
    if (k === "price_tier") {
      payload[k] = s ? parseInt(s, 10) : null;
    } else if (k === "cuisine_tags" || k === "vibe_tags" || k === "feature_tags") {
      payload[k] = splitCSV(s);
    } else {
      payload[k] = s || null;
    }
  }
  // Remove null name (shouldn't happen, but belt-and-suspenders)
  if (!payload.name) {
    showError(errorEl, "Name is required.");
    return;
  }

  const submitBtn = e.target.querySelector('[type="submit"]');
  submitBtn.disabled = true;

  const { ok, data } = await apiCall("POST", "/api/admin/restaurants", payload);
  submitBtn.disabled = false;
  if (!ok) {
    showError(errorEl, data?.detail || "Save failed.");
    return;
  }

  successEl.textContent = `Saved! ID: ${data.id}`;
  setVisible(successEl, true);
  clearPrefillForm();
  setVisible(prefillFormWrap, false);
  loadRestaurants();
});

// ---------------------------------------------------------------------------
// Add by URL
// ---------------------------------------------------------------------------

addUrlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const urlInput = addUrlForm.elements["url"];
  const spinner = document.getElementById("url-spinner");
  const errorEl = document.getElementById("url-error");
  showError(errorEl, null);
  const btn = document.getElementById("fetch-url-btn");

  btn.disabled = true;
  setVisible(spinner, true);

  const { ok, data } = await apiCall("POST", "/api/admin/add-by-url", { url: urlInput.value });

  btn.disabled = false;
  setVisible(spinner, false);

  if (!ok) {
    showError(errorEl, data?.detail || "Failed to fetch / extract.");
    return;
  }
  populatePrefillForm(data);
});

// ---------------------------------------------------------------------------
// Add by Name
// ---------------------------------------------------------------------------

addNameForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(addNameForm);
  const spinner = document.getElementById("name-spinner");
  const errorEl = document.getElementById("name-error");
  showError(errorEl, null);
  const btn = document.getElementById("fetch-name-btn");

  btn.disabled = true;
  setVisible(spinner, true);

  const { ok, data } = await apiCall("POST", "/api/admin/add-by-name", {
    name: fd.get("name"),
    neighborhood: fd.get("neighborhood") || null,
  });

  btn.disabled = false;
  setVisible(spinner, false);

  if (!ok) {
    showError(errorEl, data?.detail || "Extraction failed.");
    return;
  }
  populatePrefillForm(data);
});

// ---------------------------------------------------------------------------
// Reseed
// ---------------------------------------------------------------------------

document.getElementById("preview-eater").addEventListener("click", async () => {
  const previewEl = document.getElementById("reseed-preview");
  const spinner = document.getElementById("reseed-spinner");
  const btn = document.getElementById("preview-eater");

  previewEl.innerHTML = "";
  btn.disabled = true;
  setVisible(spinner, true);

  const { ok, data } = await apiCall("GET", "/api/admin/reseed-preview/eater_essentials");

  btn.disabled = false;
  setVisible(spinner, false);

  if (!ok) {
    previewEl.innerHTML = "<p class='error-msg'>Scrape failed.</p>";
    return;
  }

  renderReseedPreview(previewEl, data);
});

/**
 * Render the reseed preview: counts + new restaurant names + Apply button.
 */
function renderReseedPreview(container, data) {
  const wrap = document.createElement("div");
  wrap.className = "reseed-summary";

  const summary = document.createElement("p");
  summary.innerHTML = `
    <strong>${data.new.length}</strong> new &nbsp;·&nbsp;
    <strong>${data.updated.length}</strong> updated &nbsp;·&nbsp;
    <strong>${data.unchanged.length}</strong> unchanged
  `;
  wrap.appendChild(summary);

  if (data.new.length) {
    const newHeading = document.createElement("p");
    newHeading.innerHTML = "<strong>New restaurants:</strong>";
    wrap.appendChild(newHeading);
    const ul = document.createElement("ul");
    for (const id of data.new) {
      // Find the seed by slug to show the name
      const seed = (data.seeds || []).find((s) => {
        // Recompute slug: slugify(name + neighborhood) — approximate
        const slug = [s.name, s.neighborhood]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "");
        return slug === id;
      });
      const li = document.createElement("li");
      li.textContent = seed ? seed.name : id;
      ul.appendChild(li);
    }
    wrap.appendChild(ul);
  }

  // Apply button — sends the seed list to /api/admin/reseed-apply
  const applyBtn = document.createElement("button");
  applyBtn.type = "button";
  applyBtn.className = "btn-primary";
  applyBtn.style.marginTop = "0.5rem";
  applyBtn.textContent = `Apply (${data.seeds.length} seeds)`;

  const resultEl = document.createElement("p");

  applyBtn.addEventListener("click", async () => {
    applyBtn.disabled = true;
    resultEl.textContent = "Applying…";

    const { ok, data: result } = await apiCall("POST", "/api/admin/reseed-apply", {
      seeds: data.seeds,
    });

    if (!ok) {
      resultEl.textContent = "Apply failed.";
      resultEl.className = "error-msg";
    } else {
      resultEl.textContent = `Done: ${result.inserted} inserted, ${result.updated} updated.`;
      resultEl.className = "success-msg";
      loadRestaurants();
    }
    applyBtn.disabled = false;
  });

  wrap.appendChild(applyBtn);
  wrap.appendChild(resultEl);
  container.appendChild(wrap);
}

// ---------------------------------------------------------------------------
// Initial page load
// ---------------------------------------------------------------------------

loadRestaurants();
