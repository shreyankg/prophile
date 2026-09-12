(() => {
  "use strict";

  const MAX_FILE_BYTES = 5 * 1024 * 1024;
  const profiles = [];
  const duplicateKeys = new Set();
  let colorSequence = 0;

  const elements = {
    input: document.querySelector("#file-input"),
    dropZone: document.querySelector("#drop-zone"),
    status: document.querySelector("#status"),
    messages: document.querySelector("#messages"),
    section: document.querySelector("#profiles-section"),
    rows: document.querySelector("#profile-rows"),
    legend: document.querySelector("#profile-legend"),
    controls: document.querySelector("#curve-controls"),
    selectAll: document.querySelector("#select-all"),
    selectNone: document.querySelector("#select-none"),
    clearAll: document.querySelector("#clear-all"),
  };

  const chart = new window.RoastOverlayChart(
    document.querySelector("#chart"),
    document.querySelector("#tooltip"),
    document.querySelector("#chart-empty"),
    document.querySelector("#chart-summary"),
  );

  const PROFILE_PALETTE = [
    "#3d6f8e", "#b45f4b", "#4f7a5b", "#80649a", "#b08a3e", "#3f7f7a",
    "#a5526b", "#c0783e", "#5966a1", "#76824a", "#397d9a", "#8d5a75",
  ];

  function adjustColor(hex, amount) {
    const value = Number.parseInt(hex.slice(1), 16);
    const adjust = channel => Math.max(0, Math.min(255, channel + amount));
    const red = adjust(value >> 16);
    const green = adjust((value >> 8) & 255);
    const blue = adjust(value & 255);
    return `#${[red, green, blue].map(channel => channel.toString(16).padStart(2, "0")).join("")}`;
  }

  function profileColor(index) {
    const base = PROFILE_PALETTE[index % PROFILE_PALETTE.length];
    const cycle = Math.floor(index / PROFILE_PALETTE.length) % 3;
    return cycle === 0 ? base : adjustColor(base, cycle === 1 ? 20 : -18);
  }

  function visibility() {
    return Object.fromEntries([...elements.controls.querySelectorAll("input[data-series]")].map(input => [input.dataset.series, input.checked]));
  }

  function updateChart() {
    chart.setData(profiles, visibility());
    renderLegend();
  }

  function setStatus(message) { elements.status.textContent = message; }

  function addMessage(message, type = "warning") {
    const item = document.createElement("div");
    item.className = `message ${type === "error" ? "error" : ""}`;
    item.textContent = message;
    elements.messages.append(item);
  }

  function formatDuration(seconds) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds)) return null;
    const rounded = Math.max(0, Math.round(seconds));
    return `${String(Math.floor(rounded / 60)).padStart(2, "0")}:${String(rounded % 60).padStart(2, "0")}`;
  }

  function phaseText(phase) {
    const duration = phase ? formatDuration(phase.seconds) : null;
    if (!duration) return "—";
    return typeof phase.percent === "number" ? `${duration} · ${Math.round(phase.percent)}%` : duration;
  }

  function eventTemperature(profile, key) {
    const event = (profile.events || []).find(item => item.key === key);
    return event && typeof event.bt === "number" && Number.isFinite(event.bt) ? `${event.bt.toFixed(1)} °C` : "—";
  }

  function renderProfiles() {
    elements.section.hidden = profiles.length === 0;
    elements.rows.replaceChildren();
    for (const profile of profiles) {
      const row = document.createElement("tr");
      if (!profile.enabled) row.className = "profile-disabled";

      const compare = document.createElement("td"); compare.className = "compare-cell";
      const check = document.createElement("input"); check.type = "checkbox"; check.checked = profile.enabled;
      check.setAttribute("aria-label", `Compare ${profile.displayName}`);
      check.addEventListener("change", () => { profile.enabled = check.checked; renderProfiles(); updateChart(); });
      compare.append(check);

      const name = document.createElement("td"); name.className = "profile-name"; name.textContent = profile.displayName; name.style.color = profile.color;

      const chargeTemp = document.createElement("td"); chargeTemp.className = "temperature-value"; chargeTemp.textContent = eventTemperature(profile, "charge");
      const dropTemp = document.createElement("td"); dropTemp.className = "temperature-value"; dropTemp.textContent = eventTemperature(profile, "drop");
      const drying = document.createElement("td"); drying.className = "phase-value phase-drying"; drying.textContent = phaseText(profile.phases.drying);
      const browning = document.createElement("td"); browning.className = "phase-value phase-browning"; browning.textContent = phaseText(profile.phases.browning);
      const development = document.createElement("td"); development.className = "phase-value phase-development"; development.textContent = phaseText(profile.phases.development);

      const actions = document.createElement("td");
      const remove = document.createElement("button"); remove.type = "button"; remove.className = "remove-button"; remove.textContent = "×";
      remove.title = `Remove ${profile.displayName}`; remove.setAttribute("aria-label", remove.title);
      remove.addEventListener("click", () => removeProfile(profile.id)); actions.append(remove);
      row.append(compare, name, chargeTemp, dropTemp, drying, browning, development, actions);
      elements.rows.append(row);
    }
  }

  function renderLegend() {
    elements.legend.replaceChildren();
    for (const profile of profiles) {
      const key = document.createElement("span"); key.className = `profile-key${profile.enabled ? "" : " disabled"}`;
      const dot = document.createElement("i"); dot.style.backgroundColor = profile.color;
      const label = document.createElement("span"); label.textContent = profile.displayName;
      key.append(dot, label); elements.legend.append(key);
    }
  }

  function removeProfile(id) {
    const index = profiles.findIndex(profile => profile.id === id);
    if (index < 0) return;
    duplicateKeys.delete(profiles[index].duplicateKey);
    profiles.splice(index, 1);
    renderProfiles(); updateChart();
    setStatus(profiles.length ? `${profiles.length} profile${profiles.length === 1 ? "" : "s"} loaded.` : "");
  }

  function clearAll() {
    profiles.splice(0); duplicateKeys.clear(); elements.messages.replaceChildren();
    renderProfiles(); updateChart(); setStatus("");
  }

  async function importFiles(fileList) {
    const files = [...fileList];
    if (!files.length) return;
    elements.messages.replaceChildren();
    const accepted = [];
    for (const file of files) {
      const key = `${file.name}::${file.size}`;
      if (!file.name.toLowerCase().endsWith(".alog")) { addMessage(`${file.name}: unsupported extension; choose an .alog file.`, "error"); continue; }
      if (file.size > MAX_FILE_BYTES) { addMessage(`${file.name}: file exceeds the 5 MB limit.`, "error"); continue; }
      if (file.size === 0) { addMessage(`${file.name}: file is empty.`, "error"); continue; }
      if (duplicateKeys.has(key)) { addMessage(`${file.name}: already loaded.`); continue; }
      duplicateKeys.add(key);
      accepted.push({ file, key });
    }
    if (!accepted.length) { setStatus("No new profiles were loaded."); return; }

    setStatus(`Loading ${accepted.length} profile${accepted.length === 1 ? "" : "s"}…`);
    let loaded = 0;
    for (const { file, key } of accepted) {
      const id = globalThis.crypto?.randomUUID?.() || `profile-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      try {
        const response = await fetch("/api/parse", {
          method: "POST",
          headers: { "Content-Type": "text/plain; charset=utf-8", "X-Filename": encodeURIComponent(file.name), "X-Profile-Id": id },
          body: file,
        });
        let payload;
        try { payload = await response.json(); }
        catch { throw new Error("The server returned an unreadable response."); }
        if (!response.ok) throw new Error(payload.error || "The profile could not be imported.");
        payload.enabled = true;
        payload.color = profileColor(colorSequence++);
        payload.duplicateKey = key;
        profiles.push(payload);
        loaded += 1;
        for (const warning of payload.warnings || []) addMessage(`${file.name}: ${warning}`);
      } catch (error) {
        duplicateKeys.delete(key);
        const networkMessage = error instanceof TypeError ? "server/network failure." : error.message;
        addMessage(`${file.name}: ${networkMessage}`, "error");
      }
    }
    renderProfiles(); updateChart();
    setStatus(`${loaded} profile${loaded === 1 ? "" : "s"} loaded${accepted.length !== loaded ? `; ${accepted.length - loaded} failed` : ""}.`);
    elements.input.value = "";
  }

  elements.input.addEventListener("change", () => importFiles(elements.input.files));
  elements.controls.addEventListener("change", event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement)) return;
    const measurements = [...elements.controls.querySelectorAll("input[data-series]:not([data-series='events'])")];
    if (!measurements.some(item => item.checked)) {
      input.checked = true;
      setStatus("At least one measurement must remain visible.");
      return;
    }
    updateChart();
  });
  elements.selectAll.addEventListener("click", () => { profiles.forEach(profile => { profile.enabled = true; }); renderProfiles(); updateChart(); });
  elements.selectNone.addEventListener("click", () => { profiles.forEach(profile => { profile.enabled = false; }); renderProfiles(); updateChart(); });
  elements.clearAll.addEventListener("click", clearAll);

  for (const type of ["dragenter", "dragover"]) elements.dropZone.addEventListener(type, event => { event.preventDefault(); elements.dropZone.classList.add("dragging"); });
  for (const type of ["dragleave", "drop"]) elements.dropZone.addEventListener(type, event => { event.preventDefault(); elements.dropZone.classList.remove("dragging"); });
  elements.dropZone.addEventListener("drop", event => importFiles(event.dataTransfer.files));

  renderProfiles(); updateChart();
})();
