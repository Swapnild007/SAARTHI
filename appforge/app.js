(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const STORE_KEY = "saarthi.appforge.projects.v1";
  const ACTIVE_KEY = "saarthi.appforge.active.v1";
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
  function checkpoint() {
    if (!active.html) return;
    active.versions = Array.isArray(active.versions) ? active.versions : [];
    active.versions.push({html: active.html, name: active.name, at: new Date().toISOString(), prompt: active.prompt, provider: active.provider});
    active.versions = active.versions.slice(-12);
  }
  function render() {
    projectName.value = active.name;
    $("workspaceTitle").textContent = active.name;
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
      $("providerLabel").textContent = (active.provider || "local") + " · isolated iframe";
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
      active.provider = result.mode === "ai-generated" ? "AI · " + result.provider : "Safe starter · " + result.provider;
      active.updatedAt = new Date().toISOString();
      if (isRefine) changeRequest.value = "";
      setStatus(result.note || "Version generated.");
      view = "preview";
      persist();
      render();
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
  $("generate").addEventListener("click", () => generate(false));
  $("refine").addEventListener("click", () => generate(true));
  $("newProject").addEventListener("click", () => {
    const p = makeProject("Untitled project");
    projects.unshift(p); active = p; view = "preview"; persist(); render();
    prompt.focus();
  });
  $("projectName").addEventListener("change", () => {
    active.name = projectName.value.trim().slice(0, 80) || "My App";
    active.updatedAt = new Date().toISOString(); persist(); render();
  });
  document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => { prompt.value = button.dataset.prompt; prompt.focus(); }));
  document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => { view = button.dataset.view; render(); }));
  $("applyCode").addEventListener("click", () => {
    const source = $("codeEditor").value;
    if (!/<html[\s>]/i.test(source) || !/<\/html\s*>/i.test(source)) { setStatus("The source must contain a complete HTML document."); return; }
    checkpoint(); active.html = source.slice(0, 120000); active.provider = "Manual edit"; active.updatedAt = new Date().toISOString(); view = "preview"; persist(); render(); setStatus("Edited HTML applied to the sandboxed preview.");
  });
  $("restoreVersion").addEventListener("click", () => {
    if (!active.versions || !active.versions.length) { setStatus("No previous version is available yet."); return; }
    const previous = active.versions.pop();
    active.html = previous.html; active.name = previous.name || active.name; active.prompt = previous.prompt || active.prompt; active.provider = "Restored checkpoint"; active.updatedAt = new Date().toISOString(); persist(); render(); setStatus("Previous checkpoint restored.");
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