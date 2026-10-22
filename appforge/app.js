(() => {
  "use strict";
  const applyTheme=()=>{
    let prefs={};try{prefs=JSON.parse(localStorage.getItem('saarthi.preferences.v1')||'{}');}catch{}
    document.documentElement.classList.toggle('dark-theme',prefs.theme==='dark'||(prefs.theme==='system'&&matchMedia('(prefers-color-scheme: dark)').matches));
    document.documentElement.classList.toggle('reduce-motion',prefs.reducedMotion===true);
  };
  applyTheme();addEventListener('storage',event=>{if(event.key==='saarthi.preferences.v1')applyTheme();});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',applyTheme);
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
  let cloudBuildConfigured = false;
  let selectedFile = "index.html";
  persist(false);
  render();
  loadCloudProjects();
  refreshBuildCapability();

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
    try { const parsed = JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); return Array.isArray(parsed) ? parsed.filter(p => p && typeof p.id === "string").map(p => ({...p, versions: Array.isArray(p.versions) ? p.versions : [], files: p.files && typeof p.files === "object" ? p.files : (p.html ? {"index.html": p.html} : {})})) : []; }
    catch { return []; }
  }
  function makeProject(name) {
    return {id: crypto.randomUUID ? crypto.randomUUID() : fallbackUuid(), name, prompt: "", html: "", files: {}, buildHtml: null, versions: [], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), provider: "not-generated"};
  }
  function persist(updateStatus = true) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(projects));
      localStorage.setItem(ACTIVE_KEY, active.id);
      if (updateStatus) $("saveStatus").textContent = "Saved locally";
      $("projectCount").textContent = projects.length + (projects.length === 1 ? " project" : " projects");
    } catch {
      $("saveStatus").textContent = "Storage full · export your HTML";
    }
  }
  async function refreshBuildCapability() {
    const button = $("cloudBuild");
    if (!button) return;
    try {
      const response = await fetch("/api/appforge/health", {headers: window.parent.SaarthiWorkspace?.headers()});
      const status = response.ok ? await response.json() : {};
      cloudBuildConfigured = status.isolated_builds_configured === true;
      button.disabled = !cloudBuildConfigured;
      $("buildAccess").classList.toggle("hidden", !cloudBuildConfigured);
      button.title = cloudBuildConfigured ? "Run an isolated cloud build" : "Private preview build key is not configured yet";
      if (!cloudBuildConfigured) {
        $("buildStatus").textContent = "Cloud build awaits private preview configuration";
        $("providerLabel").textContent = "Isolated build · not configured";
      }
    } catch {
      cloudBuildConfigured = false;
      button.disabled = true;
      $("buildAccess").classList.add("hidden");
      $("buildStatus").textContent = "Cloud build capability could not be verified";
    }
  }
  async function loadCloudProjects() {
    try {
      const response = await fetch("/api/appforge/projects?session_id=" + encodeURIComponent(sessionId), {headers: window.parent.SaarthiWorkspace?.headers()});
      if (!response.ok) { $("saveStatus").textContent = "Cloud backup unavailable · local copy safe"; return; }
      const result = await response.json();
      if (!result || !result.ok || !Array.isArray(result.projects)) return;
      const byId = new Map(projects.map(project => [project.id, project]));
      const remoteIds = new Set(result.projects.filter(project => project && typeof project.id === "string").map(project => project.id));
      const newerLocal = projects.filter(project => !remoteIds.has(project.id));
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
          files: remote.files && typeof remote.files === "object" ? remote.files : (remote.html ? {"index.html": remote.html} : {}),
          buildHtml: null,
          versions: Array.isArray(remote.versions) ? remote.versions.slice(-5) : [],
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
      files: project.files && typeof project.files === "object" ? project.files : {"index.html": String(project.html || "")},
      versions: (Array.isArray(project.versions) ? project.versions : []).slice(-1).map(version => ({
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
        headers: {"Content-Type": "application/json",...window.parent.SaarthiWorkspace?.headers()},
        body: JSON.stringify({session_id: sessionId, project: payload})
      });
      const result = await response.json().catch(() => ({}));
      if (response.ok && result.ok) $("saveStatus").textContent = "Saved to cloud + browser";
      else if (response.status >= 500) $("saveStatus").textContent = "Saved locally · cloud backup unavailable";
    } catch {
      // Keep the browser copy as the source of truth when cloud storage is unavailable.
    }
  }
  function checkpoint() {
    if (!active.html && !Object.keys(active.files || {}).length) return;
    active.versions = Array.isArray(active.versions) ? active.versions : [];
    active.versions.push({
      html: active.html,
      files: {...(active.files || {})},
      name: active.name,
      at: new Date().toISOString(),
      prompt: active.prompt,
      provider: active.provider
    });
    active.versions = active.versions.slice(-5);
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
    active.files = active.files && typeof active.files === "object" ? active.files : {};
    if (active.html && typeof active.files["index.html"] !== "string") active.files["index.html"] = active.html;
    const fileNames = Object.keys(active.files).sort();
    if (!fileNames.length) {
      active.files["index.html"] = active.html || "";
      fileNames.push("index.html");
    }
    if (!fileNames.includes(selectedFile)) selectedFile = fileNames.includes("index.html") ? "index.html" : fileNames[0];
    const filePicker = $("filePicker");
    if (filePicker) {
      filePicker.innerHTML = "";
      fileNames.forEach(path => {
        const option = document.createElement("option");
        option.value = path;
        option.textContent = path;
        filePicker.appendChild(option);
      });
      filePicker.value = selectedFile;
    }
    const source = String(active.files[selectedFile] ?? "");
    const previewSource = String(active.buildHtml || bundleStaticFiles(active.files, active.html) || "");
    const hasPreview = previewSource.trim().length > 0;
    const completeHtml = /<(?:!doctype\s+html|html)(?:\s|>)/i.test(previewSource) && /<\/html\s*>/i.test(previewSource);
    $("versionLabel").textContent = (hasPreview || fileNames.length > 1) ? "Draft · v" + (active.versions.length + 1) : "New draft";
    $("emptyState").classList.toggle("hidden", hasPreview);
    $("previewWrap").classList.toggle("hidden", view !== "preview");
    $("codeWrap").classList.toggle("hidden", view !== "code");
    $("previewLabel").textContent = view === "preview" ? "LIVE PREVIEW" : "SOURCE EDITOR";
    document.querySelectorAll("[data-view]").forEach(btn => btn.classList.toggle("active", btn.dataset.view === view));
    if (hasPreview && completeHtml) {
      preview.srcdoc = withPreviewPolicy(previewSource);
      $("providerLabel").textContent = active.buildHtml ? "Isolated cloud build · preview artifact" : "SAARTHI workspace · isolated preview";
      $("buildStatus").textContent = active.buildHtml ? "Cloud build output ready" : "HTML document loaded · cloud build optional";
    } else if (hasPreview) {
      const safeText = previewSource.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      preview.srcdoc = "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><style>body{font:15px/1.6 system-ui,sans-serif;color:#263238;margin:0;padding:24px;background:#f7faf9}h2{font-size:20px}p{color:#64716f}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;border:1px solid #dfe8e5;border-radius:12px;padding:16px}</style></head><body><h2>Preview could not render</h2><p>The saved source is not a complete HTML document. Open the Code tab, check the source, or regenerate this project.</p><pre>" + safeText + "</pre></body></html>";
      $("providerLabel").textContent = "Preview validation";
      $("buildStatus").textContent = "Preview unavailable · incomplete HTML source";
    } else {
      $("providerLabel").textContent = "Ready for first generation";
      $("buildStatus").textContent = "Add a file or generate your first application";
    }
    $("codeEditor").value = source;
    $("codeSize").textContent = source.length.toLocaleString() + " characters";
    persist(false);
  }
  function bundleStaticFiles(files, html) {
    if(files?.['package.json'] && !active.buildHtml){
      return '<!doctype html><html><body><h2>Managed build required</h2><p>This project has package dependencies. Configure the isolated build service to create a preview. Source editing and export remain available.</p></body></html>';
    }
    let source=String(html || files?.['index.html'] || '');
    const doc=new DOMParser().parseFromString(source,'text/html');
    for(const link of doc.querySelectorAll('link[rel="stylesheet"][href]')){
      const path=link.getAttribute('href').replace(/^\.\//,'');
      if(typeof files?.[path]==='string'){const style=doc.createElement('style');style.textContent=files[path];link.replaceWith(style);}
    }
    for(const script of doc.querySelectorAll('script[src]')){
      const path=script.getAttribute('src').replace(/^\.\//,'');
      if(typeof files?.[path]==='string'){script.removeAttribute('src');script.textContent=files[path];}
    }
    return source.trim()?'<!doctype html>'+doc.documentElement.outerHTML:'';
  }
  window.addEventListener('message',event=>{
    if(event.source!==preview.contentWindow||event.data?.type!=='appforge-preview-error')return;
    $('buildStatus').textContent='Preview runtime error: '+String(event.data.message||'Unknown error').slice(0,240);
  });
  function withPreviewPolicy(source) {
    const policy = "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'";
    const monitor='<script>addEventListener("error",function(e){parent.postMessage({type:"appforge-preview-error",message:String(e.message).slice(0,240)},"*")});addEventListener("unhandledrejection",function(){parent.postMessage({type:"appforge-preview-error",message:"Unhandled promise rejection in preview"},"*")});<'+ '/script>';
    // Parse inertly, then put the policy before every untrusted node, including malformed HTML.
    const doc=new DOMParser().parseFromString(source,'text/html');
    doc.querySelectorAll('base').forEach(node=>node.remove());
    const meta=doc.createElement('meta');meta.httpEquiv='Content-Security-Policy';meta.content=policy;
    doc.head.prepend(meta);
    const script=doc.createElement('script');script.textContent=monitor.slice(8,-9);meta.after(script);
    return '<!doctype html>'+doc.documentElement.outerHTML;
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
        method: "POST", headers: {"Content-Type": "application/json",...window.parent.SaarthiWorkspace?.headers()},
        body: JSON.stringify({prompt: active.prompt || text, project_name: active.name, provider_settings:window.parent.SaarthiWorkspace?.providerSelection(),current_files:isRefine?active.files:{},current_html: isRefine ? active.html || null : null, change_request: isRefine ? text : null})
      });
      if (!response.ok) throw new Error("Cloud generation unavailable (" + response.status + ")");
      const result = await response.json();
      if (!result || !result.ok || typeof result.html !== "string") throw new Error("The generator returned an invalid response.");
      checkpoint();
      active.html = result.html;
      active.files = result.files || {...(active.files || {}), "index.html": result.html};
      active.buildHtml = null;
      selectedFile = "index.html";
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
    const files = {...(active.files || {})};
    if (active.html) files["index.html"] = active.html;
    if (!Object.keys(files).length) { setStatus("Add project files or generate an application before building."); return; }
    const key = $("buildKey").value.trim();
    if (!key) { setStatus("Enter the private build key to authorize an isolated build."); $("buildKey").focus(); return; }
    busy = true;
    $("cloudBuild").disabled = true;
    $("statusText").textContent = "Starting isolated cloud build…";
    $("buildStatus").textContent = "Building inside a restricted microVM…";
    try {
      const response = await fetch("/api/appforge/build", {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-AppForge-Build-Key": key,...window.parent.SaarthiWorkspace?.headers()},
        body: JSON.stringify({files})
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Cloud build unavailable (" + response.status + ")");
      if (!result.ok) throw new Error(result.logs || result.status || "Build failed");
      if (typeof result.preview_html === "string") {
        active.buildHtml = result.preview_html;
        preview.srcdoc = withPreviewPolicy(result.preview_html);
      } else if (active.html) {
        active.buildHtml = null;
        preview.srcdoc = withPreviewPolicy(active.html);
      }
      $("providerLabel").textContent = "Isolated cloud build · network restricted";
      $("buildStatus").textContent = "Build passed · " + result.files + " file(s) checked in isolated microVM";
      setStatus("Isolated build passed. No code ran in the SAARTHI API process.");
      persist();
      saveProjectToCloud(active);
    } catch (error) {
      $("buildStatus").textContent = "Cloud build did not complete";
      setStatus(error.message);
    } finally {
      busy = false;
      $("cloudBuild").disabled = !cloudBuildConfigured;
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
  $("filePicker").addEventListener("change", () => {
    selectedFile = $("filePicker").value || "index.html";
    render();
  });
  $("addFile").addEventListener("click", () => {
    const path = $("newFilePath").value.trim().replace(/\\\\/g, "/");
    const parts = path.split("/");
    const suffix = path.includes(".") ? "." + path.split(".").pop().toLowerCase() : "";
    const allowed = [".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".svg", ".txt", ".md", ".ts", ".tsx", ".jsx"];
    if (!path || path.startsWith("/") || path.length > 180 || parts.some(part => !part || part === "." || part === ".." || part.startsWith(".")) || !allowed.includes(suffix)) {
      setStatus("Use a safe project-relative path with a supported file extension.");
      return;
    }
    active.files = active.files && typeof active.files === "object" ? active.files : {};
    if (Object.keys(active.files).length >= 30) { setStatus("A project can contain at most 30 files."); return; }
    if (Object.prototype.hasOwnProperty.call(active.files, path)) { selectedFile = path; view = "code"; render(); setStatus("Opened existing file."); return; }
    checkpoint();
    active.files[path] = "";
    selectedFile = path;
    active.updatedAt = new Date().toISOString();
    view = "code";
    $("newFilePath").value = "";
    persist();
    render();
    saveProjectToCloud(active);
    $("codeEditor").focus();
    setStatus("File added to the project.");
  });
  $("applyCode").addEventListener("click", () => {
    const source = $("codeEditor").value;
    const limit = selectedFile === "index.html" ? 120000 : 80000;
    if (source.length > limit) { setStatus("This file exceeds the size limit."); return; }
    if (selectedFile === "index.html" && (!/<html[\s>]/i.test(source) || !/<\/html\s*>/i.test(source))) {
      setStatus("index.html must contain a complete HTML document.");
      return;
    }
    checkpoint();
    active.files = active.files && typeof active.files === "object" ? active.files : {};
    active.files[selectedFile] = source;
    active.buildHtml = null;
    if (selectedFile === "index.html") {
      active.html = source;
      active.buildHtml = null;
      view = "preview";
    } else {
      view = "code";
    }
    active.provider = "Manual edit";
    active.updatedAt = new Date().toISOString();
    persist();
    render();
    saveProjectToCloud(active);
    setStatus("Saved " + selectedFile + " to the project.");
  });
  $("restoreVersion").addEventListener("click", () => {
    if (!active.versions || !active.versions.length) { setStatus("No previous version is available yet."); return; }
    const previous = active.versions.pop();
    active.html = previous.html || ""; active.files = previous.files && typeof previous.files === "object" ? previous.files : (active.html ? {"index.html": active.html} : {}); active.buildHtml = null; selectedFile = "index.html"; active.name = previous.name || active.name; active.prompt = previous.prompt || active.prompt; active.provider = "Restored checkpoint"; active.updatedAt = new Date().toISOString(); persist(); render(); saveProjectToCloud(active); setStatus("Previous checkpoint restored.");
  });
  $("downloadProject").addEventListener("click", async () => {
    const files = {...(active.files || {})};
    if (active.html) files["index.html"] = active.html;
    const paths = Object.keys(files);
    if (!paths.length || (!active.html && paths.every(path => !files[path]))) {
      setStatus("Generate an application or add project files before exporting.");
      return;
    }
    const baseName = (active.name || "appforge-project").replace(/[^a-z0-9-_]+/gi, "-").slice(0, 60) || "appforge-project";
    try {
      let blob;
      let extension;
      if (paths.length > 1 || Object.prototype.hasOwnProperty.call(files, "package.json") || !Object.prototype.hasOwnProperty.call(files, "index.html")) {
        const response = await fetch("/api/appforge/export", {
          method: "POST",
          headers: {"Content-Type": "application/json",...window.parent.SaarthiWorkspace?.headers()},
          body: JSON.stringify({project_name: active.name, files})
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || "Project export failed.");
        }
        blob = await response.blob();
        extension = ".zip";
      } else {
        blob = new Blob([files["index.html"] || active.html], {type: "text/html;charset=utf-8"});
        extension = ".html";
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = baseName + extension;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus(extension === ".zip" ? "Project source exported as ZIP." : "HTML exported.");
    } catch (error) {
      setStatus(error.message);
    }
  });
  window.addEventListener("beforeunload", () => persist(false));
})();