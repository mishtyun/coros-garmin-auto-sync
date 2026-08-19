const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

let me = null;

async function api(path, opts = {}) {
  const resp = await fetch(path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": tg.initData,
      ...(opts.headers || {}),
    },
  });
  let body = null;
  try {
    body = await resp.json();
  } catch (e) {
    /* non-json error page */
  }
  if (!resp.ok) {
    throw new Error(body?.error?.message || `Request failed (${resp.status})`);
  }
  return body;
}

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3500);
}

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

/* ---------- tabs ---------- */

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("hidden");
  });
});

/* ---------- stats ---------- */

async function loadStats(period) {
  const card = document.getElementById("stats-card");
  card.innerHTML = '<div class="placeholder">Loading…</div>';
  try {
    const s = await api(`/api/stats?period=${period}`);
    if (s.totals.count === 0) {
      card.innerHTML = `<div class="stats-header">${esc(s.label)}</div>
        <div class="stats-period">${esc(s.start_date)} → ${esc(s.end_date)}</div>
        <div class="empty">No workouts yet 💤</div>`;
      return;
    }
    const totals = [
      `${s.totals.count} workouts`,
      s.totals.distance_text,
      s.totals.duration_text,
    ]
      .filter(Boolean)
      .join(" · ");
    const rows = s.by_type
      .map((t) => {
        const details = [t.count, t.distance_text, t.duration_text]
          .filter(Boolean)
          .join(" · ");
        return `<div class="type-row"><div class="row-name">${esc(t.emoji)} ${esc(
          t.label
        )}</div><div class="row-details">${esc(details)}</div></div>`;
      })
      .join("");
    card.innerHTML = `<div class="stats-header">${esc(s.label)}</div>
      <div class="stats-period">${esc(s.start_date)} → ${esc(s.end_date)}</div>
      <div class="stats-totals">${esc(totals)}</div>${rows}`;
  } catch (e) {
    card.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

document.querySelectorAll(".seg").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".seg").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    loadStats(btn.dataset.period);
  });
});

/* ---------- activities ---------- */

async function loadActivities() {
  const list = document.getElementById("activities-list");
  try {
    const data = await api("/api/activities?days=7");
    if (!data.activities.length) {
      list.innerHTML = '<div class="empty">No workouts in the last 7 days 💤</div>';
      return;
    }
    list.innerHTML = data.activities
      .map((a) => {
        const details = [a.distance_text, a.duration_text].filter(Boolean).join(" · ");
        return `<div class="activity-row">
          <div>
            <div class="row-name">${esc(a.emoji)} ${esc(a.name)}</div>
            <div class="row-date">${esc(a.date)}</div>
          </div>
          <div class="row-details">${esc(details)}</div>
        </div>`;
      })
      .join("");
  } catch (e) {
    list.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

/* ---------- sync actions ---------- */

function renderSyncResult(lines) {
  document.getElementById("sync-result").innerHTML = lines
    .map((l) => `<div class="line">${l}</div>`)
    .join("");
}

async function runSync(btn, path, formatResult) {
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Syncing…";
  try {
    const data = await api(path, { method: "POST" });
    renderSyncResult(formatResult(data));
    loadActivities();
    tg.HapticFeedback?.notificationOccurred?.("success");
  } catch (e) {
    toast(e.message);
    tg.HapticFeedback?.notificationOccurred?.("error");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

document.getElementById("btn-sync-today").addEventListener("click", (e) =>
  runSync(e.currentTarget, "/api/sync/today", (data) => {
    const lines = data.synced.map(
      (s) => `✅ <a href="${esc(s.url)}" target="_blank">${esc(s.title)}</a>`
    );
    if (data.already_synced) lines.push(`↔️ ${data.already_synced} already synced`);
    if (!lines.length) lines.push("Nothing to sync today 💤");
    return lines;
  })
);

document.getElementById("btn-sync-latest").addEventListener("click", (e) =>
  runSync(e.currentTarget, "/api/sync/latest", (data) => {
    if (!data.latest) return ["No activities in Coros yet 💤"];
    const icon = data.latest.uploaded ? "✅" : "↔️ already synced:";
    return [
      `${icon} <a href="${esc(data.latest.url)}" target="_blank">${esc(
        data.latest.title
      )}</a>`,
    ];
  })
);

/* ---------- settings ---------- */

const TOGGLES = [
  { key: "autosync", label: "Autosync", hint: "Upload new workouts to Garmin automatically" },
  { key: "autosync_quiet", label: "Quiet mode", hint: "Sync without notifications", needsAutosync: true },
  { key: "digest", label: "Daily digest", hint: "Evening summary + weekly one on Sundays" },
];

function renderSettings() {
  const card = document.getElementById("settings-card");
  card.innerHTML = TOGGLES.map((t) => {
    const disabled = t.needsAutosync && !me.autosync;
    return `<div class="toggle-row ${disabled ? "disabled" : ""}">
      <div>
        <div class="toggle-label">${esc(t.label)}</div>
        <div class="toggle-hint">${esc(t.hint)}</div>
      </div>
      <label class="switch">
        <input type="checkbox" data-key="${t.key}" ${me[t.key] ? "checked" : ""} ${
      disabled ? "disabled" : ""
    }>
        <span class="slider"></span>
      </label>
    </div>`;
  }).join("");

  card.querySelectorAll("input[data-key]").forEach((input) => {
    input.addEventListener("change", async () => {
      const key = input.dataset.key;
      const value = input.checked;
      try {
        me = await api("/api/settings", {
          method: "POST",
          body: JSON.stringify({ [key]: value }),
        });
        tg.HapticFeedback?.selectionChanged?.();
      } catch (e) {
        toast(e.message);
      }
      renderSettings();
    });
  });

  document.getElementById("account-card").innerHTML = `
    <h3 class="card-title">Linked accounts</h3>
    <div class="account-line"><span>Coros:</span> ${esc(me.coros_email)}</div>
    <div class="account-line"><span>Garmin:</span> ${esc(me.garmin_email)}</div>`;
}

/* ---------- boot ---------- */

async function boot() {
  try {
    me = await api("/api/me");
    renderSettings();
  } catch (e) {
    document.getElementById("settings-card").innerHTML = `<div class="empty">${esc(
      e.message
    )}</div>`;
    document.getElementById("stats-card").innerHTML = `<div class="empty">${esc(
      e.message
    )}</div>`;
    document.getElementById("activities-list").innerHTML = "";
    return;
  }
  loadStats("week");
  loadActivities();
}

boot();
