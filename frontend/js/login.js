const passwordForm = document.getElementById("password-form");
const passwordError = document.getElementById("password-error");
const passwordStep = document.getElementById("password-step");
const nameStep = document.getElementById("name-step");
const nameList = document.getElementById("name-list");
const newNameForm = document.getElementById("new-name-form");
const nameError = document.getElementById("name-error");

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  return res;
}

function showError(el, msg) {
  el.textContent = msg;
  el.hidden = false;
}

function renderUsers(users) {
  nameList.innerHTML = "";
  for (const u of users) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = u.display_name;
    btn.addEventListener("click", () => completeLogin(u.display_name));
    li.appendChild(btn);
    nameList.appendChild(li);
  }
}

async function loadUsers() {
  const res = await fetch("/api/login/users", { credentials: "same-origin" });
  if (!res.ok) return [];
  const body = await res.json();
  return body.users ?? [];
}

async function completeLogin(displayName) {
  nameError.hidden = true;
  const res = await postJSON("/api/login/complete", { display_name: displayName });
  if (!res.ok) {
    showError(nameError, "Could not complete login. Try another name.");
    return;
  }
  window.location.href = "/";
}

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  passwordError.hidden = true;
  const password = new FormData(passwordForm).get("password");
  const res = await postJSON("/api/login/verify-password", { password });
  if (!res.ok) {
    showError(passwordError, "Wrong password.");
    return;
  }
  passwordStep.hidden = true;
  nameStep.hidden = false;
  renderUsers(await loadUsers());
});

newNameForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = new FormData(newNameForm).get("display_name");
  await completeLogin(name);
});
