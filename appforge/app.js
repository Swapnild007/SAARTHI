(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const STORE_KEY = "saarthi.appforge.projects.v1";
  const ACTIVE_KEY = "saarthi.appforge.active.v1";
  const SESSION_KEY = "saarthi.appforge.session.v1";
  const sessionId = getSessionId();
  const preview = $("preview");
  const prompt = $("prompt");
  const projectName = $("projectName");
  const changeRequest = $("changeRequest");
  let projects = readProjects();
  let activeId = localStorage.getItem(ACTIVE_KEY);
  let active = projects.find(p => p.id === activeId) || projects[0] || makeProject("Workforce Pulse");
  if (!projects.some(p => p.id === active.id)) projects.unshift(active);
  let view = "preview";
  let busy = false;
  persist(false);
  render();
  loadCloudProjects();

  function getSessionId() {
    try {
      let value = localStorage.getItem(SESSION_KEY);
      if (!value) {
        value = crypto.randomUUID ? crypto.randomUUID() : fallbackUuid();
        localStorage.setItem(SESSION_KEY, value);
      }
      return value;
    } catch {
      return fallbackUuid();
    }
  }
  function fallbackUuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, character => {
      const random = Math.random() * 16 | 0;
      return (character === "x" ? random : (random & 3 | 8)).toString(16);
    });
  }
  function readProjects() {
    try { const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); return Array.isArray(parsed) ? parsed.filter(p => p && typeof p.id === "string") : []; }
    catch { return []; }
  }
  function makeProject(name) {
    return {id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()), name, prompt: "", html: "", versions: [], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), provider: "not-generated"};
  }
  function persist(updateStatus = true) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(projects.slice(0, 30)));
      localStorage.setItem(ACTIVE_KEY, active.id);
      if (updateStatus) $("saveStatus").textContent = "Saved locally";
      $("projectCount").textContent = projects.length + (projects.length === 1 ? " project" : " projects");
    } catch {
      $("saveStatus").textContent = "Storage full · export your HTML";
    }
  }
  async function loadCloudProjects() {
    try {
      const response = await fetch("/api/appforge/projects?session_id=" + encodeURIComponent(sessionId));
      if (!response.ok) return;
      const result = await response.json();
      if (!result || !result.ok || !Array.isArray(result.projects)) return;
      const byId = new Map(projects.map(project => [project.id, project]));
      const newerLocal = [];
      for (const remote of result.projects) {
        if (!remote || typeof remote.id !== "string") continue;
        const local = byId.get(remote.id);
        const localTime = Date.parse(local?.updatedAt || "") || 0;
        const remoteTime = Date.parse(remote.updatedAt || "") || 0;
        if (local && localTime > remoteTime) {
          newerLocal.push(local);
          continue;
        }
        byId.set(remote.id, {
          id: remote.id,
          name: remote.name || "Untitled project",
          prompt: remote.prompt || "",
          html: remote.html || "",
          versions: Array.isArray(remote.versions) ? remote.versions.slice(-12) : [],
          createdAt: remote.createdAt || new Date().toISOString(),
          updatedAt: remote.updatedAt || new Date().toISOString(),
          provider: "Cloud backup"
        });
      }
      projects = Array.from(byId.values())
        .sort((a, b) => (Date.parse(b.updatedAt || "") || 0) - (Date.parse(a.updatedAt || "") || 0))
        .slice(0, 30);
      activeId = localStorage.getItem(ACTIVE_KEY);
      active = projects.find(project => project.id === activeId) || projects[0] || active;
      if (!projects.some(project => project.id === active.id)) projects.unshift(active);
      persist(false);
      render();
      for (const project of newerLocal) saveProjectToCloud(project);
      if (result.projects.length) $("saveStatus").textContent = "Synced with cloud";
    } catch {
      // Cloud sync is best-effort; browser-local work remains available offline.
    }
  }
  async function saveProjectToCloud(project = active) {
    if (!project || !project.id) return;
    const payload = {
      id: project.id,
      name: String(project.name || "Untitled project").slice(0, 80),
      prompt: String(project.prompt || "").slice(0, 4000),
      html: String(project.html || "").slice(0, 120000),
      versions: (Array.isArray(project.versions) ? project.versions : []).slice(-3).map(version => ({
        name: String(version.name || "").slice(0, 80),
        at: String(version.at || "").slice(0, 64),
        prompt: String(version.prompt || "").slice(0, 4000),
        provider: String(version.provider || "").slice(0, 80),
        html: String(version.html || "").slice(0, 120000)
      })),
      createdAt: project.createdAt || new Date().toISOString(),
      updatedAt: project.updatedAt || new Date().toISOString()
    };
    try {
      const response = await fetch("/api/appforge/projects", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({session_id: sessionId, project: payload})
      });
      const result = await response.json().catch(() => ({}));
      if (response.ok && result.ok) $("saveStatus").textContent = "Saved to cloud + browser";
    } catch {
      // Keep the browser copy as the source of truth when cloud storage is unavailable.
    }
  }
  function checkpoint() {
    if (!active.html) return;
    active.versions = Array.isArray(active.versions) ? active.versions : [];
    active.versions.push({html: active.html, name: active.name, at: new Date().toISOString(), prompt: active.prompt, provider: active.provider});
    active.versions = active.versions.slice(-12);
  }
  function render() {
    projectName.value = active.name;
    $("workspaceTitle").textContent = active.name;
    const picker = $("projectPicker");
    if (picker) {
      picker.innerHTML = "";
      projects.slice(0, 30).forEach(project => {
        const option = document.createElement("option");
        option.value = project.id;
        option.textContent = project.name || "Untitled project";
        picker.appendChild(option);
      });
      picker.value = active.id;
    }
    $("versionLabel").textContent = active.html ? "Draft · v" + (active.versions.length + 1) : "New draft";
    $("emptyState").classList.toggle("hidden", !!active.html);
    $("previewWrap").classList.toggle("hidden", view !== "preview");
    $("codeWrap").classList.toggle("hidden", view !== "code");
    $("previewLabel").textContent = view === "preview" ? "LIVE PREVIEW" : "SOURCE EDITOR";
    document.querySelectorAll("[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
    if (active.html) {
      preview.srcdoc = withPreviewPolicy(active.html);
      $("codeEditor").value = active.html;
      $("codeSize").textContent = active.html.length.toLocaleString() + " characters";
      $("providerLabel").textContent = "SAARTHI workspace · isolated preview";
      $("buildStatus").textContent = "Preview ready · no cloud build executed";
    } else {
      $("codeEditor").value = "";
      $("codeSize").textContent = "0 characters";
      $("providerLabel").textContent = "Ready for first generation";
      $("buildStatus").textContent = "Ready for your first build";
    }
    persist(false);
  }
  function withPreviewPolicy(source) {
    const policy = "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'";
    const meta = '<meta http-equiv="Content-Security-Policy" content="' + policy + '">';
    if (/<head[^>]*>/i.test(source)) return source.replace(/<head([^>]*)>/i, "<head$1>" + meta);
    return "<!doctype html><html><head>" + meta + "</head><body>" + source + "</body></html>";
  }
  async function generate(isRefine) {
    if (busy) return;
    const text = (isRefine ? changeRequest.value : prompt.value).trim();
    if (text.length < 8) { setStatus("Add a little more detail to the request."); return; }
    active.name = projectName.value.trim().slice(0, 80) || "My App";
    active.prompt = isRefine ? active.prompt : text;
    busy = true;
    $("generate").disabled = $("refine").disabled = true;
    $("statusText").textContent = isRefine ? "Refining application…" : "Generating application…";
    $("buildStatus").textContent = "Preparing a new version…";
    try {
      const response = await fetch("/api/appforge/generate", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({prompt: active.prompt || text, project_name: active.name, current_html: isRefine ? active.html || null : null, change_request: isRefine ? text : null})
      });
      if (!response.ok) throw new Error("Cloud generation unavailable (" + response.status + ")");
      const result = await response.json();
      if (!result || !result.ok || typeof result.html !== "string") throw new Error("The generator returned an invalid response.");
      checkpoint();
      active.html = result.html;
      active.provider = result.mode === "ai-generated" ? "Generated by SAARTHI" : "Starter preview";
      active.updatedAt = new Date().toISOString();
      if (isRefine) changeRequest.value = "";
      setStatus(result.note || "Version generated.");
      view = "preview";
      persist();
      render();
      saveProjectToCloud(active);
    } catch (error) {
      setStatus(error.message + ". Use Export HTML to keep local work; check the SAARTHI API connection.");
      $("buildStatus").textContent = "Generation could not be completed";
    } finally {
      busy = false;
      $("generate").disabled = $("refine").disabled = false;
      if ($("statusText").textContent.includes("…")) $("statusText").textContent = "Local workspace ready";
    }
  }
  function setStatus(message) {
    $("statusText").textContent = message.length > 76 ? message.slice(0, 73) + "…" : message;
  }
  async function runCloudBuild() {
    if (busy) return;
    if (!active.html) { setStatus("Generate an application before running a cloud build."); return; }
    const key = $("buildKey").value.trim();
    if (!key) { setStatus("Enter the private build key to authorize an isolated build."); $("buildKey").focus(); return; }
    busy = true;
    $("cloudBuild").disabled = true;
    $("statusText").textContent = "Starting isolated cloud build…";
    $("buildStatus").textContent = "Building inside a restricted microVM…";
    try {
      const response = await fetch("/api/appforge/build", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-AppForge-Build-Key": key},
        body: JSON.stringify({files: {"index.html": active.html}})
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Cloud build unavailable (" + response.status + ")");
      if (!result.ok) throw new Error(result.logs || result.status || "Build failed");
      const output = typeof result.preview_html === "string" ? result.preview_html : active.html;
      preview.srcdoc = withPreviewPolicy(output);
      $("providerLabel").textContent = "Isolated cloud build · network restricted";
      $("buildStatus").textContent = "Build passed · " + result.files + " file(s) checked in isolated microVM";
      setStatus("Isolated build passed. No code ran in the SAARTHI API process.");
    } catch (error) {
      $("buildStatus").textContent = "Cloud build did not complete";
      setStatus(error.message);
    } finally {
      busy = false;
      $("cloudBuild").disabled = false;
      if ($("statusText").textContent.includes("…")) $("statusText").textContent = "Local workspace ready";
    }
  }
  $("cloudBuild").addEventListener("click", runCloudBuild);
  $("generate").addEventListener("click", () => generate(false));
  $("refine").addEventListener("click", () => generate(true));
  $("newProject").addEventListener("click", () => {
    const p = makeProject("Untitled project");
    projects.unshift(p); active = p; view = "preview"; persist(); render();
    saveProjectToCloud(active);
    prompt.focus();
  });
  $("projectPicker").addEventListener("change", () => {
    const selected = projects.find(project => project.id === $("projectPicker").value);
    if (selected) { active = selected; view = "preview"; render(); setStatus("Project opened from this browser."); }
  });
  $("projectName").addEventListener("change", () => {
    active.name = projectName.value.trim().slice(0, 80) || "My App";
    active.updatedAt = new Date().toISOString(); persist(); render(); saveProjectToCloud(active);
  });
  document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => { prompt.value = button.dataset.prompt; prompt.focus(); }));
  document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => { view = button.dataset.view; render(); }));
  $("applyCode").addEventListener("click", () => {
    const source = $("codeEditor").value;
    if (!/<html[\s>]/i.test(source) || !/<\/html\s*>/i.test(source)) { setStatus("The source must contain a complete HTML document."); return; }
    checkpoint(); active.html = source.slice(0, 120000); active.provider = "Manual edit"; active.updatedAt = new Date().toISOString(); view = "preview"; persist(); render(); saveProjectToCloud(active); setStatus("Edited HTML applied to the sandboxed preview.");
  });
  $("restoreVersion").addEventListener("click", () => {
    if (!active.versions || !active.versions.length) { setStatus("No previous version is available yet."); return; }
    const previous = active.versions.pop();
    active.html = previous.html; active.name = previous.name || active.name; active.prompt = previous.prompt || active.prompt; active.provider = "Restored checkpoint"; active.updatedAt = new Date().toISOString(); persist(); render(); saveProjectToCloud(active); setStatus("Previous checkpoint restored.");
  });
  $("downloadProject").addEventListener("click", () => {
    if (!active.html) { setStatus("Generate an application before exporting."); return; }
    const blob = new Blob([active.html], {type: "text/html;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = (active.name || "appforge-project").replace(/[^a-z0-9-_]+/gi, "-").slice(0, 60) + ".html"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener("beforeunload", () => persist(false));
})();