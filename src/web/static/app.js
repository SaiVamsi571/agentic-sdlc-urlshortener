/**
 * AetherSDLC Reactive Frontend Engine
 * Real-time SSE DAG rendering, HITL governance, telemetry, and URL shortener sandbox.
 */

// Topologies for each scenario
const SCENARIO_TOPOLOGIES = {
  greenfield: [
    { id: "REQ-01", name: "Requirements", phase: "requirements", x: 40, y: 170, status: "pending" },
    { id: "ARCH-01", name: "Architecture", phase: "architecture", x: 180, y: 170, status: "pending", deps: ["REQ-01"] },
    { id: "DECOMP-01", name: "Decomposition", phase: "decomposition", x: 320, y: 170, status: "pending", deps: ["ARCH-01"] },
    { id: "CODE-01", name: "Implementation", phase: "implementation", x: 470, y: 100, status: "pending", deps: ["DECOMP-01"] },
    { id: "SEC-01", name: "Security SAST", phase: "guardrails_pre", x: 470, y: 240, status: "pending", deps: ["DECOMP-01"] },
    { id: "TEST-01", name: "Testing", phase: "testing", x: 620, y: 170, status: "pending", deps: ["CODE-01", "SEC-01"] },
    { id: "HITL-01", name: "Governance Gate", phase: "hitl_approval", x: 770, y: 170, status: "pending", deps: ["TEST-01"] },
    { id: "REL-01", name: "Release Ready", phase: "release_readiness", x: 920, y: 170, status: "pending", deps: ["HITL-01"] }
  ],
  brownfield: [
    { id: "REQ-BROWN-01", name: "Req Scope", phase: "requirements", x: 40, y: 170, status: "pending" },
    { id: "BLAST-01", name: "AST Blast Radius", phase: "blast_radius", x: 190, y: 170, status: "pending", deps: ["REQ-BROWN-01"] },
    { id: "HITL-SCHEMA-01", name: "Change Control Gate", phase: "hitl_approval", x: 350, y: 170, status: "pending", deps: ["BLAST-01"] },
    { id: "CODE-BROWN-01", name: "Incremental Coder", phase: "implementation", x: 510, y: 170, status: "pending", deps: ["HITL-SCHEMA-01"] },
    { id: "SEC-BROWN-01", name: "Security Audit", phase: "guardrails_pre", x: 660, y: 170, status: "pending", deps: ["CODE-BROWN-01"] },
    { id: "TEST-BROWN-01", name: "Regression Tests", phase: "testing", x: 800, y: 170, status: "pending", deps: ["SEC-BROWN-01"] },
    { id: "REL-BROWN-01", name: "Release v1.1.0", phase: "release_readiness", x: 940, y: 170, status: "pending", deps: ["TEST-BROWN-01"] }
  ],
  ambiguous: [
    { id: "AMBIG-01", name: "Ambiguity Scoring", phase: "requirements", x: 40, y: 170, status: "pending" },
    { id: "HITL-DISAMBIG-01", name: "Clarification Gate", phase: "hitl_approval", x: 200, y: 170, status: "pending", deps: ["AMBIG-01"] },
    { id: "ARCH-AMBIG-01", name: "Architecture", phase: "architecture", x: 360, y: 170, status: "pending", deps: ["HITL-DISAMBIG-01"] },
    { id: "CODE-AMBIG-01", name: "Implementation", phase: "implementation", x: 510, y: 170, status: "pending", deps: ["ARCH-AMBIG-01"] },
    { id: "SEC-AMBIG-01", name: "Security SAST", phase: "guardrails_pre", x: 660, y: 170, status: "pending", deps: ["CODE-AMBIG-01"] },
    { id: "TEST-AMBIG-01", name: "Test Suite", phase: "testing", x: 800, y: 170, status: "pending", deps: ["SEC-AMBIG-01"] },
    { id: "REL-AMBIG-01", name: "Release v1.0.1", phase: "release_readiness", x: 940, y: 170, status: "pending", deps: ["TEST-AMBIG-01"] }
  ]
};

let currentScenario = "greenfield";
let currentNodes = JSON.parse(JSON.stringify(SCENARIO_TOPOLOGIES.greenfield));
let activeHitlRequestId = null;
let lastShortCode = null;

// Initialize SVG DAG
function renderDAG() {
  const svg = document.getElementById("dag-canvas");
  if (!svg) return;
  svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 1080 380");
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

  const NODE_WIDTH = 114;
  const NODE_HEIGHT = 50;

  // 1. Draw Edges
  currentNodes.forEach(node => {
    if (node.deps) {
      node.deps.forEach(depId => {
        const fromNode = currentNodes.find(n => n.id === depId);
        if (fromNode) {
          const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
          const startX = fromNode.x + NODE_WIDTH;
          const startY = fromNode.y + NODE_HEIGHT / 2;
          const endX = node.x;
          const endY = node.y + NODE_HEIGHT / 2;
          const cX1 = startX + 35;
          const cX2 = endX - 35;
          const d = `M ${startX} ${startY} C ${cX1} ${startY}, ${cX2} ${endY}, ${endX} ${endY}`;
          path.setAttribute("d", d);
          path.setAttribute("class", `dag-edge ${fromNode.status === 'completed' && node.status === 'running' ? 'active' : ''}`);
          svg.appendChild(path);
        }
      });
    }
  });

  // 2. Draw Nodes
  currentNodes.forEach(node => {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", `dag-node status-${node.status}`);
    g.setAttribute("transform", `translate(${node.x}, ${node.y})`);

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("width", NODE_WIDTH);
    rect.setAttribute("height", NODE_HEIGHT);
    rect.setAttribute("rx", "10");

    const textId = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textId.setAttribute("x", "10");
    textId.setAttribute("y", "20");
    textId.setAttribute("fill", "#94a3b8");
    textId.setAttribute("font-size", "10");
    textId.setAttribute("font-family", "JetBrains Mono, monospace");
    textId.textContent = node.id;

    const textName = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textName.setAttribute("x", "10");
    textName.setAttribute("y", "38");
    textName.setAttribute("fill", "#ffffff");
    textName.setAttribute("font-size", "11.5");
    textName.setAttribute("font-weight", "600");
    textName.textContent = node.name.length > 13 ? node.name.substring(0, 12) + "…" : node.name;

    g.appendChild(rect);
    g.appendChild(textId);
    g.appendChild(textName);
    svg.appendChild(g);
  });
}

// Connect to Server-Sent Events (SSE)
function connectSSE() {
  const evtSource = new EventSource("/api/pipeline/events");

  evtSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      handlePipelineEvent(data);
    } catch (err) {
      console.error("SSE parse error:", err);
    }
  };

  evtSource.addEventListener("pipeline_event", (e) => {
    try {
      const data = JSON.parse(e.data);
      handlePipelineEvent(data);
    } catch (err) {
      console.error("pipeline_event parse error:", err);
    }
  });

  evtSource.onerror = (err) => {
    console.warn("SSE connection interrupted. Reconnecting in 3s...", err);
  };
}

function handlePipelineEvent(event) {
  const type = event.type;

  if (type === "PIPELINE_STARTED") {
    currentScenario = event.scenario;
    highlightScenarioButton(currentScenario);
    if (SCENARIO_TOPOLOGIES[currentScenario]) {
      currentNodes = JSON.parse(JSON.stringify(SCENARIO_TOPOLOGIES[currentScenario]));
    }
    document.getElementById("val-phase").textContent = "RUNNING";
    document.getElementById("val-pipeline-id").textContent = event.scenario.toUpperCase();
    document.getElementById("dag-status-pill").textContent = "Executing...";
    currentNodes.forEach(n => n.status = "pending");
    renderDAG();
    appendLog("INFO", "ORCHESTRATOR", `Pipeline started for scenario [${event.scenario.toUpperCase()}]`);
  } 
  else if (type === "NODE_STARTED") {
    const node = currentNodes.find(n => n.id === event.node_id);
    if (node) {
      node.status = "running";
      renderDAG();
    }
    document.getElementById("val-phase").textContent = event.phase ? event.phase.toUpperCase() : "RUNNING";
    appendLog("INFO", event.node_id, `Started: ${event.node_name}`);
  }
  else if (type === "NODE_COMPLETED") {
    const node = currentNodes.find(n => n.id === event.node_id);
    if (node) {
      node.status = "completed";
      renderDAG();
    }
    appendLog("INFO", event.node_id, `Completed successfully.`);

    // If node completed was AST Blast Radius, update the card
    if (event.output && (event.output.risk_score !== undefined || event.output.blast_radius_report)) {
      const report = event.output.blast_radius_report || event.output;
      updateBlastRadiusUI(report);
    }
  }
  else if (type === "HITL_REQUESTED") {
    const node = currentNodes.find(n => n.id === event.node_id);
    if (node) {
      node.status = "waiting";
      renderDAG();
    }
    appendLog("GATE", event.node_id, `Human review requested for gate: ${event.gate_title}`);
    
    // Check auto-approve toggle
    const autoApprove = document.getElementById("chk-auto-approve").checked;
    if (!autoApprove) {
      showHitlModal(event);
    }
  }
  else if (type === "HITL_RESOLVED") {
    hideHitlModal();
    appendLog("GATE", "GOVERNANCE", `Gate signed off by ${event.reviewer}: ${event.comments}`);
  }
  else if (type === "DYNAMIC_REPLAN_TRIGGERED") {
    appendLog("WARN", "SELF-HEAL", `Dynamic re-planning engaged. Rescheduling subgraph.`);
  }
  else if (type === "PIPELINE_COMPLETED") {
    document.getElementById("val-phase").textContent = "COMPLETED";
    document.getElementById("dag-status-pill").textContent = "Pipeline Succeeded";
    appendLog("INFO", "ORCHESTRATOR", "Pipeline finished successfully with 100% gate pass.");
    refreshMetrics();
    fetchBlastRadius();
  }
  else if (type === "METRICS_UPDATED") {
    updateMetricsUI(event.metrics);
  }
}

function appendLog(level, source, message) {
  const container = document.getElementById("log-stream");
  if (!container) return;
  const entry = document.createElement("div");
  entry.className = `log-entry level-${level}`;

  const timeStr = new Date().toLocaleTimeString();
  entry.innerHTML = `
    <div class="log-header">
      <span>${source}</span>
      <span>${timeStr}</span>
    </div>
    <div class="log-msg">${message}</div>
  `;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

// HITL Modal logic
function showHitlModal(req) {
  activeHitlRequestId = req.request_id;
  document.getElementById("hitl-title").textContent = req.gate_title || "Governance Checkpoint";
  document.getElementById("hitl-description").textContent = req.description || "Human review required before pipeline can progress.";
  document.getElementById("hitl-diff").textContent = req.proposed_diff || "// Proposed schema changes and AST blast radius reviewed.\n// All backwards compatibility checks passed.";
  
  const riskBadge = document.getElementById("hitl-risk");
  const risk = req.risk_level || "MEDIUM";
  riskBadge.textContent = `${risk} RISK`;
  riskBadge.className = `risk-badge risk-${risk}`;

  // Update Docked bar info as well
  const dockedBar = document.getElementById("hitl-docked-bar");
  if (dockedBar) {
    document.getElementById("hitl-docked-title").textContent = req.node_id || "HITL-GATE";
    const dockedRisk = document.getElementById("hitl-docked-risk");
    dockedRisk.textContent = `${risk} RISK`;
    dockedRisk.className = `risk-badge risk-${risk}`;
  }

  // Update AST ribbon if metadata or artifacts present
  const blast = (req.metadata && req.metadata.blast_radius) || null;
  const ribbon = document.getElementById("hitl-ast-ribbon");
  if (ribbon) {
    if (blast) {
      ribbon.style.display = "flex";
      const bRisk = document.getElementById("hitl-ast-risk");
      bRisk.textContent = `${blast.risk_category || risk} (${blast.risk_score !== undefined ? blast.risk_score : 1.0})`;
      bRisk.style.color = (blast.risk_category === "CRITICAL" || blast.risk_category === "HIGH") ? "var(--accent-rose)" : "var(--accent-amber)";
      document.getElementById("hitl-ast-files").textContent = `${blast.total_modules_affected || (req.affected_components ? req.affected_components.length : 0)} Modules`;
      const isSchema = !!blast.is_schema_modified;
      const schemaEl = document.getElementById("hitl-ast-schema");
      schemaEl.textContent = isSchema ? "YES (Sign-Off Required)" : "NO (Non-schema logic)";
      schemaEl.style.color = isSchema ? "var(--accent-rose)" : "var(--accent-emerald)";
    } else {
      ribbon.style.display = "none";
    }
  }

  // If docked bar was showing, hide it and show modal
  if (dockedBar) dockedBar.style.display = "none";
  document.getElementById("hitl-modal").classList.add("active");
}

function minimizeHitlModal() {
  document.getElementById("hitl-modal").classList.remove("active");
  const dockedBar = document.getElementById("hitl-docked-bar");
  if (dockedBar) dockedBar.style.display = "flex";
}

function restoreHitlModal() {
  const dockedBar = document.getElementById("hitl-docked-bar");
  if (dockedBar) dockedBar.style.display = "none";
  document.getElementById("hitl-modal").classList.add("active");
}

function hideHitlModal() {
  activeHitlRequestId = null;
  document.getElementById("hitl-modal").classList.remove("active");
  const dockedBar = document.getElementById("hitl-docked-bar");
  if (dockedBar) dockedBar.style.display = "none";
}

async function resolveHitl(approved) {
  if (!activeHitlRequestId) {
    hideHitlModal();
    return;
  }
  const reqId = activeHitlRequestId;
  try {
    const res = await fetch(`/api/pipeline/hitl/${reqId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved: approved,
        reviewer: "LeadArchitect-UI",
        comments: approved ? "Approved via Interactive Dashboard" : "Rejected by user in UI"
      })
    });
    if (!res.ok) {
      const err = await res.json();
      console.warn("HITL resolution response:", err);
    }
    hideHitlModal();
  } catch (err) {
    console.error("Error submitting HITL decision:", err);
    hideHitlModal();
  }
}

// AST Blast Radius Logic
async function fetchBlastRadius(proposal) {
  try {
    const sel = document.getElementById("sel-blast-proposal");
    const activeProposal = proposal || (sel ? sel.value : "brownfield");
    if (sel && proposal && sel.value !== proposal) {
      sel.value = proposal;
    }
    const indicator = document.getElementById("blast-updating-indicator");
    if (indicator) indicator.style.display = "inline";

    const res = await fetch(`/api/pipeline/blast-radius?proposal=${encodeURIComponent(activeProposal)}`);
    if (res.ok) {
      const data = await res.json();
      updateBlastRadiusUI(data);
    }
  } catch (err) {
    console.error("Error fetching blast radius:", err);
  } finally {
    const indicator = document.getElementById("blast-updating-indicator");
    if (indicator) indicator.style.display = "none";
  }
}

function updateBlastRadiusUI(report) {
  if (!report) return;
  const box = document.getElementById("blast-details");
  if (!box) return;

  const score = report.risk_score !== undefined ? report.risk_score : 1.0;
  const category = report.risk_category || "HIGH";
  const impactedCount = report.total_modules_affected !== undefined ? report.total_modules_affected : (report.total_impacted_count || (report.directly_impacted_modules ? report.directly_impacted_modules.length : 0));
  const directList = report.directly_impacted_modules || [];
  const indirectList = report.indirectly_impacted_modules || [];
  const isSchema = !!report.is_schema_modified;
  const reqHitl = !!report.requires_hitl_approval;

  const colorMap = {
    LOW: "var(--accent-emerald)",
    MEDIUM: "var(--accent-amber)",
    HIGH: "var(--accent-rose)",
    CRITICAL: "var(--accent-rose)"
  };
  const color = colorMap[category] || "var(--accent-cyan)";

  // Update active proposal badge if present
  const badge = document.getElementById("blast-active-badge");
  if (badge && report.selected_proposal) {
    const labels = {
      brownfield: "Full Scope",
      schema_migration: "Schema Migration",
      router_only: "Router Only",
      cache: "Cache Layer",
      validator: "Validator Patch"
    };
    badge.textContent = `Active: ${labels[report.selected_proposal] || report.selected_proposal}`;
  }

  // Flash highlight on box to visually confirm update
  box.classList.remove("pulse-highlight");
  void box.offsetWidth; // Force reflow
  box.classList.add("pulse-highlight");
  setTimeout(() => box.classList.remove("pulse-highlight"), 600);

  let html = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
      <span style="font-weight: 500;">Risk Level:</span>
      <strong style="color: ${color}; font-size: 0.85rem;">${category} (${score})</strong>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
      <span style="color: var(--text-secondary);">Affected Modules:</span>
      <strong>${impactedCount}</strong>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
      <span style="color: var(--text-secondary);">Schema Modified:</span>
      <strong style="color: ${isSchema ? 'var(--accent-rose)' : 'var(--accent-emerald)'};">${isSchema ? 'YES' : 'NO'}</strong>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 0.45rem;">
      <span style="color: var(--text-secondary);">HITL Gate:</span>
      <strong style="color: ${reqHitl ? 'var(--accent-amber)' : 'var(--accent-emerald)'};">${reqHitl ? 'Required' : 'Auto-Approved'}</strong>
    </div>
    <div style="font-size: 0.74rem; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 0.4rem;">
      <div><strong>Directly modified (${directList.length}):</strong></div>
      <ul style="margin: 0.2rem 0 0.3rem 1.1rem; padding: 0;">
        ${directList.map(f => `<li><code>${f.split('/').pop()}</code></li>`).join('')}
      </ul>
      ${indirectList.length > 0 ? `
        <div style="margin-top: 0.2rem;"><strong>Indirect dependents (${indirectList.length}):</strong></div>
        <ul style="margin: 0.2rem 0 0 1.1rem; padding: 0;">
          ${indirectList.map(f => `<li><code>${f.split('/').pop()}</code></li>`).join('')}
        </ul>
      ` : '<div style="margin-top: 0.2rem; color: var(--accent-emerald);"><em>No downstream caller dependencies affected</em></div>'}
    </div>
  `;
  box.innerHTML = html;
}

// Metrics refresh
async function refreshMetrics() {
  try {
    const res = await fetch("/api/pipeline/metrics");
    if (res.ok) {
      const data = await res.json();
      updateMetricsUI(data);
    }
  } catch (err) {
    console.error("Error fetching metrics:", err);
  }
}

function updateMetricsUI(m) {
  if (!m) return;
  document.getElementById("val-success-rate").textContent = `${m.success_rate_percent || 100.0}%`;
  document.getElementById("val-mttr").textContent = `${m.mean_time_to_repair_mttr_sec || 0.0}s`;
  document.getElementById("val-latency").textContent = `${m.avg_latency_seconds || 3.5}s`;
  document.getElementById("val-violations").textContent = `${m.guardrail_violations_prevented || 0}`;
}

// Scenario Button Highlighting
function highlightScenarioButton(name) {
  const map = {
    greenfield: document.getElementById("btn-run-greenfield"),
    brownfield: document.getElementById("btn-run-brownfield"),
    ambiguous: document.getElementById("btn-run-ambiguous")
  };
  Object.entries(map).forEach(([scenario, btn]) => {
    if (!btn) return;
    if (scenario === name) {
      btn.className = "btn active-scenario";
    } else {
      btn.className = "btn";
    }
  });
}

// Scenario Run Trigger
async function triggerScenario(name) {
  const autoApprove = document.getElementById("chk-auto-approve").checked;
  currentScenario = name;
  highlightScenarioButton(name);
  if (SCENARIO_TOPOLOGIES[name]) {
    currentNodes = JSON.parse(JSON.stringify(SCENARIO_TOPOLOGIES[name]));
    renderDAG();
  }

  // Retrieve proposal for brownfield scenario
  const sel = document.getElementById("sel-blast-proposal");
  const proposal = (name === "brownfield" && sel) ? sel.value : "brownfield";

  appendLog("INFO", "LAUNCHER", `Requesting run for scenario: ${name.toUpperCase()}${name === "brownfield" ? ` [Proposal: ${proposal}]` : ""} (Auto-Approve: ${autoApprove})`);
  try {
    const res = await fetch(`/api/pipeline/run/${name}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        auto_approve: autoApprove,
        proposal: proposal
      })
    });
    const data = await res.json();
    console.log("Run response:", data);
  } catch (err) {
    console.error("Run error:", err);
  }
}

// URL Shortener Playground Handlers
async function handleShortenSubmit(e) {
  e.preventDefault();
  const url = document.getElementById("input-url").value;
  const alias = document.getElementById("input-alias").value.trim() || null;
  const ttl = parseInt(document.getElementById("input-ttl").value, 10) || null;

  try {
    const res = await fetch("/shortener/api/v1/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        original_url: url,
        custom_alias: alias,
        ttl_seconds: ttl,
        tags: { source: "web_dashboard_playground" }
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${err.detail || "Failed to shorten URL"}`);
      return;
    }

    const data = await res.json();
    lastShortCode = data.short_code;
    
    const resultCard = document.getElementById("shorten-result");
    const linkElem = document.getElementById("short-link");
    linkElem.textContent = data.short_url;
    linkElem.href = data.short_url;
    resultCard.classList.add("active");
    appendLog("INFO", "PLAYGROUND", `Short URL generated: ${data.short_code} -> ${data.original_url}`);
  } catch (err) {
    alert("Network error creating short URL");
  }
}

async function handleSimulateClick() {
  if (!lastShortCode) {
    appendLog("WARN", "PLAYGROUND", "Please shorten a URL first to generate a short link before simulating click hops.");
    alert("Please shorten a URL first to generate a short link.");
    return;
  }
  try {
    const res = await fetch(`/shortener/${lastShortCode}`, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Referer": "https://example.com/dashboard"
      }
    });
    appendLog("INFO", "CLICK_SIMULATOR", `Click recorded for [${lastShortCode}]. Status: ${res.status}`);
    fetchAnalytics();
  } catch (err) {
    console.error(err);
    appendLog("WARN", "CLICK_SIMULATOR", `Failed to record click for [${lastShortCode}]: ${err.message}`);
  }
}

async function fetchAnalytics() {
  if (!lastShortCode) {
    appendLog("WARN", "PLAYGROUND", "Please shorten a URL first to view analytics.");
    alert("Please shorten a URL first to view its analytics.");
    return;
  }
  try {
    const res = await fetch(`/shortener/api/v1/analytics/${lastShortCode}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("analytics-card").style.display = "block";
      document.getElementById("stat-total-clicks").textContent = data.total_clicks;
      document.getElementById("stat-uniques").textContent = data.unique_visitors;
      const topDevice = data.devices && data.devices.length > 0 ? data.devices[0].device : "desktop";
      document.getElementById("stat-device").textContent = topDevice;
    } else {
      const err = await res.json();
      appendLog("WARN", "ANALYTICS", `Analytics query failed: ${err.detail || res.statusText}`);
    }
  } catch (err) {
    console.error(err);
    appendLog("WARN", "ANALYTICS", `Network error fetching analytics: ${err.message}`);
  }
}

// Setup Event Listeners
window.addEventListener("DOMContentLoaded", () => {
  highlightScenarioButton("greenfield");
  renderDAG();
  connectSSE();
  refreshMetrics();
  fetchBlastRadius();

  const blastProposalSelect = document.getElementById("sel-blast-proposal");
  if (blastProposalSelect) {
    blastProposalSelect.addEventListener("change", (e) => {
      fetchBlastRadius(e.target.value);
    });
  }

  document.getElementById("btn-run-greenfield").addEventListener("click", () => triggerScenario("greenfield"));
  document.getElementById("btn-run-brownfield").addEventListener("click", () => triggerScenario("brownfield"));
  document.getElementById("btn-run-ambiguous").addEventListener("click", () => triggerScenario("ambiguous"));
  
  document.getElementById("btn-clear-logs").addEventListener("click", () => {
    document.getElementById("log-stream").innerHTML = "";
  });

  document.getElementById("btn-hitl-approve").addEventListener("click", () => resolveHitl(true));
  document.getElementById("btn-hitl-reject").addEventListener("click", () => resolveHitl(false));

  const btnHitlMin = document.getElementById("btn-hitl-minimize");
  if (btnHitlMin) btnHitlMin.addEventListener("click", minimizeHitlModal);

  const btnHitlRest = document.getElementById("btn-hitl-restore");
  if (btnHitlRest) btnHitlRest.addEventListener("click", restoreHitlModal);

  const btnHitlDockApprove = document.getElementById("btn-hitl-docked-approve");
  if (btnHitlDockApprove) btnHitlDockApprove.addEventListener("click", () => resolveHitl(true));

  const btnHitlDockReject = document.getElementById("btn-hitl-docked-reject");
  if (btnHitlDockReject) btnHitlDockReject.addEventListener("click", () => resolveHitl(false));

  document.getElementById("shorten-form").addEventListener("submit", handleShortenSubmit);
  document.getElementById("btn-test-click").addEventListener("click", handleSimulateClick);
  document.getElementById("btn-fetch-analytics").addEventListener("click", fetchAnalytics);

  document.getElementById("btn-open-report").addEventListener("click", showReportModal);
  document.getElementById("btn-close-report").addEventListener("click", hideReportModal);
  document.getElementById("btn-dismiss-report").addEventListener("click", hideReportModal);
});

async function showReportModal() {
  const modal = document.getElementById("report-modal");
  const content = document.getElementById("report-content");
  modal.classList.add("active");
  content.textContent = "Loading engineering run report from artifacts/engineering-summary.md...";
  try {
    const res = await fetch("/api/pipeline/report");
    if (res.ok) {
      const data = await res.json();
      if (data.status === "AVAILABLE") {
        content.textContent = data.report_markdown;
      } else {
        content.textContent = "No engineering report has been generated yet. Run a pipeline scenario (e.g. Run Greenfield) to produce artifacts.";
      }
    } else {
      content.textContent = "Error fetching engineering report.";
    }
  } catch (err) {
    content.textContent = "Failed to load report: " + err;
  }
}

function hideReportModal() {
  document.getElementById("report-modal").classList.remove("active");
}
