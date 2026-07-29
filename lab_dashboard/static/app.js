const state = {
  meta: null,
  history: [],
  answerBuffer: "",
};

const $ = (id) => document.getElementById(id);

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return `${Math.round(Number(value) * 100)}%`;
}

function money(value) {
  return `$${Number(value || 0).toFixed(6)}`;
}

function shortHash(value) {
  if (!value) return "";
  return `${value.slice(0, 12)}...`;
}

async function loadMeta() {
  const response = await fetch("/api/meta");
  state.meta = await response.json();
  renderMeta();
}

function renderMeta() {
  const { artifact, best_run, runs, version_log, tools, group_cases } = state.meta;
  $("artifactVersion").textContent = artifact.artifact_version;
  $("artifactHash").textContent = `prompt ${shortHash(artifact.prompt_hash)} · tools ${shortHash(artifact.tools_hash)}`;
  $("bestAccuracy").textContent = pct(best_run?.case_accuracy);
  $("passedCases").textContent = best_run ? `${best_run.passed_cases}/${best_run.total_cases}` : "--";
  $("providerErrors").textContent = best_run?.provider_error_cases ?? "--";
  $("toolCount").textContent = tools.length;
  $("runCount").textContent = `${runs.length} runs`;
  $("groupCount").textContent = `${group_cases.length} cases`;
  renderVersions(version_log, runs);
  renderRuns(runs);
  renderTools(tools);
  renderGroupCases(group_cases);
}

function renderVersions(rows, runs) {
  const byVersion = new Map();
  for (const run of runs) {
    if (!run.version) continue;
    const current = byVersion.get(run.version);
    if (!current || (run.case_accuracy ?? -1) > (current.case_accuracy ?? -1)) {
      byVersion.set(run.version, run);
    }
  }
  $("versionTimeline").innerHTML = rows.map((row) => {
    const run = byVersion.get(row.version);
    return `
      <div class="version-item">
        <div class="version-id">${escapeHtml(row.version || "")}</div>
        <div>
          <div class="version-reason">${escapeHtml(row.hypothesis || row.reason || "")}</div>
          <div class="subtle">${escapeHtml(row.run_file || "")}</div>
        </div>
        <div class="version-score">${pct(run?.case_accuracy ?? row.metric_after)}</div>
      </div>
    `;
  }).join("");
}

function renderRuns(runs) {
  $("runsTable").innerHTML = runs.slice().reverse().map((run) => `
    <tr>
      <td><strong>${escapeHtml(run.version || "")}</strong></td>
      <td>${escapeHtml(run.suite || "")}</td>
      <td>${escapeHtml(run.model || run.provider || "")}</td>
      <td>${pct(run.case_accuracy)}</td>
      <td>${run.passed_cases ?? "--"}/${run.total_cases ?? "--"}</td>
      <td><code>${escapeHtml(run.file || "")}</code></td>
    </tr>
  `).join("");
}

function renderTools(tools) {
  $("toolsList").innerHTML = tools.map((tool) => `
    <article class="tool-card">
      <div class="tool-title">
        <span>${escapeHtml(tool.name)}</span>
        <span class="badge ${tool.implemented ? "green" : ""}">${tool.implemented ? "ready" : "missing"}</span>
      </div>
      <div class="description">${escapeHtml(tool.description)}</div>
    </article>
  `).join("");
}

function renderGroupCases(cases) {
  $("groupCases").innerHTML = cases.map((item) => `
    <article class="case-card">
      <div class="case-title">
        <span>${escapeHtml(item.id)}</span>
        <span class="badge">${escapeHtml(item.type)}</span>
      </div>
      <div class="description">${escapeHtml(item.what_it_tests)}</div>
    </article>
  `).join("");
}

function addMessage(role, text) {
  const node = document.createElement("div");
  node.className = `msg ${role}`;
  node.textContent = text;
  $("chatLog").appendChild(node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
  return node;
}

function addEvent(event, data) {
  const node = document.createElement("div");
  node.className = "event-line";
  node.innerHTML = `<code>${escapeHtml(event)}</code> ${escapeHtml(compactJson(data))}`;
  $("eventStream").prepend(node);
}

function setStatus(text, mode = "") {
  const node = $("chatStatus");
  node.textContent = text;
  node.className = `status ${mode}`;
}

async function submitChat(event) {
  event.preventDefault();
  const message = $("message").value.trim();
  if (!message) return;
  $("message").value = "";
  state.answerBuffer = "";
  $("eventStream").innerHTML = "";
  $("latency").textContent = "0 ms";
  $("tokens").textContent = "0";
  $("cost").textContent = "$0.000000";
  $("activeProvider").textContent = "--";
  $("transcriptPath").textContent = "";

  addMessage("user", message);
  const assistantNode = addMessage("assistant", "");
  setStatus("running", "running");

  const payload = {
    message,
    provider: $("provider").value,
    fallback_provider: $("fallbackProvider").value,
    version: $("version").value || "demo",
    model: $("model").value || null,
    history: state.history.slice(-10),
  };

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await readEventStream(response.body, (eventName, data) => {
      addEvent(eventName, data);
      if (eventName === "answer_chunk") {
        state.answerBuffer += data.text || "";
        assistantNode.textContent = state.answerBuffer;
        $("chatLog").scrollTop = $("chatLog").scrollHeight;
      }
      if (eventName === "provider_success") {
        $("activeProvider").textContent = `${data.provider}/${data.model || "default"}`;
      }
      if (eventName === "done") {
        $("latency").textContent = `${Math.round(data.totals.latency_ms || 0)} ms`;
        $("tokens").textContent = String(data.totals.total_tokens || 0);
        $("cost").textContent = money(data.totals.cost_usd);
        $("transcriptPath").textContent = data.transcript_path || "";
        setStatus(data.status || "done", "done");
      }
      if (eventName === "fatal_error") {
        setStatus("error", "error");
        assistantNode.textContent = data.error || "Error";
      }
    });
    state.history.push({ role: "user", content: message });
    state.history.push({ role: "assistant", content: state.answerBuffer });
  } catch (error) {
    setStatus("error", "error");
    assistantNode.textContent = String(error);
  }
}

async function readEventStream(stream, onEvent) {
  const reader = stream.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event: "));
      const dataLine = lines.find((line) => line.startsWith("data: "));
      if (!eventLine || !dataLine) continue;
      const eventName = eventLine.slice(7).trim();
      const data = JSON.parse(dataLine.slice(6));
      onEvent(eventName, data);
    }
  }
}

function compactJson(value) {
  const text = JSON.stringify(value);
  return text.length > 360 ? `${text.slice(0, 360)}...` : text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

$("refreshBtn").addEventListener("click", loadMeta);
$("chatForm").addEventListener("submit", submitChat);
loadMeta().catch((error) => {
  setStatus("meta error", "error");
  addEvent("meta_error", { error: String(error) });
});

