async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    throw new Error(`search failed: ${res.status}`);
  }
  return res.json();
}

export async function search(payload) {
  return postJSON("/api/search", payload);
}

export async function whoami() {
  const res = await fetch("/api/whoami", { credentials: "same-origin" });
  if (!res.ok) return null;
  return res.json();
}

export async function checkAvailability({ restaurantId, party, date, time }) {
  const params = new URLSearchParams({
    restaurant_id: restaurantId,
    party: String(party),
    date,
    time,
  });
  const res = await fetch(`/api/availability?${params.toString()}`, {
    credentials: "same-origin",
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  const body = await res.json().catch(() => ({}));
  return { status: res.status, body };
}
