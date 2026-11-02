"use strict";

const DAY_NAMES = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const $ = (sel) => document.querySelector(sel);

const state = {
  devices: [],
  schedules: [],
  editId: null,
  days: new Set(),
  waking: new Set(),
  pollTimer: null,
};

// ---------- Speicher (Token bleibt nur auf diesem Handy) ----------
const storage = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};

// ---------- API ----------
class AuthError extends Error {}

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: {
      "Authorization": "Bearer " + (storage.get("pcwake-token") || ""),
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  let data = {};
  try { data = await res.json(); } catch { /* leer */ }
  if (res.status === 401) throw new AuthError(data.error || "Ungültiges Token");
  if (!res.ok) throw new Error(data.error || `Fehler ${res.status}`);
  return data;
}

// ---------- UI-Hilfen ----------
let toastTimer;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) node.append(c instanceof Node ? c : document.createTextNode(c));
  return node;
}

function showView(name) {
  for (const v of document.querySelectorAll(".view")) v.classList.add("hidden");
  $("#view-" + name).classList.remove("hidden");
}

function handleError(err) {
  if (err instanceof AuthError) {
    storage.del("pcwake-token");
    $("#login-error").textContent = err.message;
    stopPolling();
    showView("login");
  } else {
    toast(navigator.onLine ? err.message : "Keine Internetverbindung");
  }
}

// Zeiten immer in der Zeitzone des Servers anzeigen (nicht in der des Handys)
function fmtServerTime(iso, withSeconds = false) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/.exec(iso || "");
  if (!m) return "–";
  const wd = DAY_NAMES[(new Date(Date.UTC(+m[1], m[2] - 1, +m[3])).getUTCDay() + 6) % 7];
  return `${wd}, ${m[3]}.${m[2]}., ${m[4]}:${m[5]}` + (withSeconds && m[6] ? `:${m[6]}` : "") + " Uhr";
}

// ---------- Geräte ----------
async function loadDevices() {
  const data = await api("GET", "/api/devices");
  state.devices = data.devices;
  for (const d of state.devices) if (d.online) state.waking.delete(d.id);
  renderDevices();
  $("#server-time").textContent = "Serverzeit: " + fmtServerTime(data.server_time, true);
}

function renderDevices() {
  const list = $("#device-list");
  list.replaceChildren(...state.devices.map((d) => {
    const waking = state.waking.has(d.id);
    let dotClass = "dot", label = "Aus";
    if (d.online === null) label = "Status unbekannt";
    if (d.online) { dotClass += " on"; label = "Online"; }
    else if (waking) { dotClass += " wait"; label = "Startet …"; }
    return el("div", { class: "card device" },
      el("div", { class: "name" }, d.name),
      el("div", { class: "status" }, el("span", { class: dotClass }), label),
      el("button", {
        class: "power" + (d.online ? " on" : ""),
        "aria-label": `${d.name} starten`,
        onclick: () => wake(d),
      }, "⏻"),
      el("div", { class: "muted small" }, d.online ? "PC läuft bereits" : "Tippen zum Einschalten"),
    );
  }));
}

async function wake(device) {
  if (navigator.vibrate) navigator.vibrate(30);
  try {
    const res = await api("POST", `/api/devices/${encodeURIComponent(device.id)}/wake`);
    toast(res.message || "Gesendet");
    state.waking.add(device.id);
    renderDevices();
    // Nach 3 Minuten "Startet …" wieder entfernen, falls der PC nicht hochkommt
    setTimeout(() => { state.waking.delete(device.id); renderDevices(); }, 180000);
  } catch (e) { handleError(e); }
}

// ---------- Zeitpläne ----------
async function loadSchedules() {
  const data = await api("GET", "/api/schedules");
  state.schedules = data.schedules.sort((a, b) => a.time.localeCompare(b.time));
  renderSchedules();
}

function describeDays(days) {
  const key = days.join(",");
  if (key === "0,1,2,3,4,5,6") return "Täglich";
  if (key === "0,1,2,3,4") return "Mo–Fr";
  if (key === "5,6") return "Wochenende";
  return days.map((d) => DAY_NAMES[d]).join(", ");
}

function renderSchedules() {
  const list = $("#schedule-list");
  if (!state.schedules.length) {
    list.replaceChildren(el("div", { class: "card muted" },
      "Noch kein Autostart eingerichtet. Lege fest, wann dein PC automatisch starten soll."));
    return;
  }
  const devName = (id) => (state.devices.find((d) => d.id === id) || {}).name || id;
  list.replaceChildren(...state.schedules.map((s) => {
    const next = s.next_run ? fmtServerTime(s.next_run) : "–";
    const toggle = el("input", { type: "checkbox", checked: s.enabled,
      onchange: async (e) => {
        try {
          await api("POST", `/api/schedules/${s.id}`, { enabled: e.target.checked });
          await loadSchedules();
        } catch (err) { e.target.checked = !e.target.checked; handleError(err); }
      } });
    return el("div", { class: "card schedule" + (s.enabled ? "" : " disabled") },
      el("div", { class: "info", onclick: () => openScheduleDialog(s) },
        el("div", { class: "time" }, s.time),
        el("div", { class: "meta" }, [s.label, devName(s.device), describeDays(s.days)].filter(Boolean).join(" · ")),
        el("div", { class: "meta" }, "Nächster Start: " + next),
      ),
      el("label", { class: "switch", "aria-label": "Aktiv" }, toggle, el("span")),
    );
  }));
}

function renderDayButtons() {
  $("#day-buttons").replaceChildren(...DAY_NAMES.map((n, i) =>
    el("button", { type: "button", class: state.days.has(i) ? "on" : "",
      onclick: () => { state.days.has(i) ? state.days.delete(i) : state.days.add(i); renderDayButtons(); } }, n)));
}

function openScheduleDialog(s) {
  const form = $("#form-schedule");
  state.editId = s ? s.id : null;
  $("#dlg-title").textContent = s ? "Autostart bearbeiten" : "Neuer Autostart";
  $("#sel-device").replaceChildren(...state.devices.map((d) => el("option", { value: d.id }, d.name)));
  form.label.value = s ? s.label : "";
  form.device.value = s ? s.device : (state.devices[0] || {}).id;
  form.time.value = s ? s.time : "07:00";
  state.days = new Set(s ? s.days : [0, 1, 2, 3, 4]);
  renderDayButtons();
  $("#schedule-error").textContent = "";
  $("#btn-delete-schedule").classList.toggle("hidden", !s);
  $("#dlg-schedule").showModal();
}

async function saveSchedule(ev) {
  ev.preventDefault();
  const form = ev.target;
  const body = {
    label: form.label.value.trim(),
    device: form.device.value,
    time: form.time.value,
    days: [...state.days].sort(),
  };
  if (!body.days.length) { $("#schedule-error").textContent = "Bitte mindestens einen Tag wählen."; return; }
  try {
    if (state.editId) await api("POST", `/api/schedules/${state.editId}`, body);
    else await api("POST", "/api/schedules", { ...body, enabled: true });
    $("#dlg-schedule").close();
    toast("Autostart gespeichert");
    await loadSchedules();
  } catch (e) {
    if (e instanceof AuthError) { $("#dlg-schedule").close(); handleError(e); }
    else $("#schedule-error").textContent = e.message;
  }
}

async function deleteSchedule() {
  if (!state.editId || !confirm("Diesen Autostart löschen?")) return;
  try {
    await api("DELETE", `/api/schedules/${state.editId}`);
    $("#dlg-schedule").close();
    toast("Gelöscht");
    await loadSchedules();
  } catch (e) { handleError(e); }
}

// ---------- Ablauf ----------
function startPolling() {
  stopPolling();
  state.pollTimer = setInterval(() => {
    if (document.visibilityState === "visible") loadDevices().catch(handleError);
  }, 5000);
}
function stopPolling() { clearInterval(state.pollTimer); }

async function enterMain() {
  showView("main");
  try {
    await loadDevices();
    await loadSchedules();
    startPolling();
  } catch (e) { handleError(e); }
}

function init() {
  $("#btn-login").addEventListener("click", async () => {
    const token = $("#in-token").value.trim();
    if (!token) return;
    storage.set("pcwake-token", token);
    $("#login-error").textContent = "";
    await enterMain();
  });
  $("#in-token").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#btn-login").click(); });

  $("#btn-settings").addEventListener("click", () => {
    if (confirm("Abmelden und Token von diesem Gerät entfernen?")) {
      storage.del("pcwake-token");
      stopPolling();
      $("#in-token").value = "";
      showView("login");
    }
  });

  for (const btn of document.querySelectorAll(".tabs button")) {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
      $("#tab-devices").classList.toggle("hidden", btn.dataset.tab !== "devices");
      $("#tab-schedules").classList.toggle("hidden", btn.dataset.tab !== "schedules");
    });
  }

  $("#btn-add-schedule").addEventListener("click", () => openScheduleDialog(null));
  $("#form-schedule").addEventListener("submit", saveSchedule);
  $("#btn-cancel").addEventListener("click", () => $("#dlg-schedule").close());
  $("#btn-delete-schedule").addEventListener("click", deleteSchedule);
  for (const b of document.querySelectorAll("[data-preset]")) {
    b.addEventListener("click", () => {
      state.days = new Set(b.dataset.preset.split(",").map(Number));
      renderDayButtons();
    });
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && storage.get("pcwake-token")) loadDevices().catch(handleError);
  });

  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }

  if (storage.get("pcwake-token")) enterMain();
  else showView("login");
}

init();
