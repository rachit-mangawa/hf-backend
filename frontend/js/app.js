/**
 * HF Backend — Swagger / FastAPI Style Interactive API Explorer
 * Built with Emil Kowalski design engineering principles:
 * - Direct, tactile feedback (< 140ms response states)
 * - Clean method-coded operation bars (GET in blue, POST in green)
 * - Pre-filled sample payloads (zero manual form configuration required)
 * - Live request execution with direct timing & status feedback
 */

const BASE_URL = "https://idkhowtocodefr-hf-backend.hf.space";

const GATEWAYS = {
  "hf-backend": {
    name: "HF Backend Core Gateway",
    description: "Central routing, status table, and health telemetry endpoints.",
    endpoints: [
      {
        id: "hf-health",
        method: "GET",
        path: "/health",
        summary: "Gateway Health & Subproject Readiness",
        description: "Returns aggregate health status, container uptime, and model warmup readiness across all mounted subprojects.",
        samplePayload: null,
        sampleResponse: {
          "status": "healthy",
          "timestamp": "2026-11-07T12:00:00Z",
          "uptime_seconds": 108420.5,
          "subprojects": {
            "/heartflow": {
              "status": "healthy",
              "warmed": true
            },
            "/semantic": {
              "status": "healthy",
              "warmed": true
            }
          }
        }
      },
      {
        id: "hf-status",
        method: "GET",
        path: "/status",
        summary: "Subproject Routing Table & Metadata",
        description: "Introspects registered route paths, mounted upstream packages, and gateway middleware boundaries.",
        samplePayload: null,
        sampleResponse: {
          "gateway": "HF Backend Hub",
          "version": "1.0.0",
          "active_subprojects": [
            {
              "prefix": "/heartflow",
              "package": "heartflow-backend",
              "status": "mounted"
            },
            {
              "prefix": "/semantic",
              "package": "semantic-backend",
              "status": "mounted"
            }
          ]
        }
      },
      {
        id: "hf-root",
        method: "GET",
        path: "/",
        summary: "Gateway Root & OpenAPI Redirect",
        description: "Root gateway endpoint; serves Swagger UI HTML to browser requests and JSON health payload to automated probes.",
        samplePayload: null,
        sampleResponse: {
          "message": "HF Backend Gateway Operational",
          "docs": "/project",
          "openapi": "/openapi.json"
        }
      }
    ]
  },
  "heartflow": {
    name: "HeartFlow OS Machine Learning Gateway",
    description: "Real-time cardiac arrhythmia prediction, clinical SHAP attribution, TinyML C++ export, and model metrics.",
    endpoints: [
      {
        id: "heartflow-predict",
        method: "POST",
        path: "/heartflow/predict",
        summary: "Real-Time Arrhythmia Risk Prediction",
        description: "Evaluates patient telemetry vitals to classify cardiac rhythm risk and compute diagnostic confidence.",
        samplePayload: {
          "Heart_Rate": 84,
          "SpO2_Level": 98.2,
          "Systolic_BP": 122,
          "Diastolic_BP": 79,
          "Body_Temp": 36.8
        },
        sampleResponse: {
          "prediction": "Normal Sinus Rhythm",
          "risk_score": 0.082,
          "confidence": 0.941,
          "telemetry_evaluated": {
            "Heart_Rate": 84,
            "SpO2_Level": 98.2,
            "Systolic_BP": 122,
            "Diastolic_BP": 79,
            "Body_Temp": 36.8
          }
        }
      },
      {
        id: "heartflow-explain",
        method: "POST",
        path: "/heartflow/explain",
        summary: "Clinical Feature Attribution & SHAP Weights",
        description: "Computes physiological feature importances and diagnostic explanations for patient telemetry.",
        samplePayload: {
          "Heart_Rate": 115,
          "SpO2_Level": 93.5,
          "Systolic_BP": 148,
          "Diastolic_BP": 95,
          "Body_Temp": 38.2
        },
        sampleResponse: {
          "prediction": "Tachycardia / Elevated Risk",
          "risk_score": 0.74,
          "attributions": {
            "Heart_Rate": 0.42,
            "Systolic_BP": 0.28,
            "SpO2_Level": -0.18,
            "Body_Temp": 0.12
          }
        }
      },
      {
        id: "heartflow-metrics",
        method: "GET",
        path: "/heartflow/metrics",
        summary: "Model Validation & Confusion Matrix Metrics",
        description: "Returns offline validation metrics, classification accuracy, AUC-ROC, and inference latencies.",
        samplePayload: null,
        sampleResponse: {
          "model": "RandomForest-Classifier",
          "accuracy": 0.923,
          "f1_score": 0.918,
          "auc_roc": 0.964,
          "evaluation_samples": 450
        }
      },
      {
        id: "heartflow-tinyml",
        method: "GET",
        path: "/heartflow/export_tinyml",
        summary: "TinyML C++ Header Export",
        description: "Compiles trained decision tree arrays into a standalone C++ header for ESP32 and Arduino microcontrollers.",
        samplePayload: null,
        sampleResponse: {
          "format": "cpp_header",
          "filename": "heartflow_tinyml.h",
          "byte_size": 14280,
          "preview": "// Auto-generated HeartFlow TinyML model\nconst float weights[5] = {0.21, 0.34, 0.15, 0.18, 0.12};"
        }
      },
      {
        id: "heartflow-health",
        method: "GET",
        path: "/heartflow/health",
        summary: "HeartFlow Runtime Readiness",
        description: "Checks model weight warmups and memory residency.",
        samplePayload: null,
        sampleResponse: {
          "status": "healthy",
          "model_loaded": true,
          "package": "heartflow-backend"
        }
      }
    ]
  },
  "semantic": {
    name: "Semantic Analyzer NLP Gateway",
    description: "Transformer-based sentence embeddings, multi-label toxicity classification, and sentiment extraction.",
    endpoints: [
      {
        id: "semantic-analyze",
        method: "POST",
        path: "/semantic/analyze",
        summary: "Multi-Label NLP Toxicity & Sentiment Analysis",
        description: "Runs transformer inference to detect toxicity, polarity, and intent from text feedback.",
        samplePayload: {
          "text": "Great API integration, lightweight and response times are extremely fast.",
          "threshold": 0.5,
          "include_explanation": true
        },
        sampleResponse: {
          "sentiment": "positive",
          "polarity_score": 0.89,
          "toxicity": {
            "toxic": false,
            "severe_toxic": false,
            "insult": false,
            "confidence": 0.012
          },
          "inference_latency_ms": 14.8
        }
      },
      {
        id: "semantic-batch",
        method: "POST",
        path: "/semantic/batch",
        summary: "Batch Text NLP Inference",
        description: "Evaluates multiple comments in a vectorized batch operation.",
        samplePayload: {
          "texts": [
            "Outstanding gateway performance and zero downtime.",
            "Needs more documentation on endpoint rate limits."
          ],
          "threshold": 0.5
        },
        sampleResponse: {
          "processed_count": 2,
          "results": [
            { "sentiment": "positive", "score": 0.94 },
            { "sentiment": "neutral", "score": 0.48 }
          ]
        }
      },
      {
        id: "semantic-health",
        method: "GET",
        path: "/semantic/health",
        summary: "Semantic Analyzer Service Readiness",
        description: "Confirms SentenceTransformer weights and tokenizers are ready in RAM.",
        samplePayload: null,
        sampleResponse: {
          "status": "healthy",
          "service": "semantic-analyzer",
          "device": "cpu"
        }
      }
    ]
  }
};

let currentGateway = "hf-backend";
let openedOperations = new Set(["hf-health"]);

/**
 * Switch the active gateway (/hf-backend, /heartflow, /semantic)
 */
function selectGateway(gwKey) {
  if (!GATEWAYS[gwKey]) return;
  currentGateway = gwKey;

  // Update Gateway Tabs
  const tabHf = document.getElementById("tab-gw-hf");
  const tabHeartflow = document.getElementById("tab-gw-heartflow");
  const tabSemantic = document.getElementById("tab-gw-semantic");

  if (tabHf) tabHf.classList.toggle("active", gwKey === "hf-backend");
  if (tabHeartflow) tabHeartflow.classList.toggle("active", gwKey === "heartflow");
  if (tabSemantic) tabSemantic.classList.toggle("active", gwKey === "semantic");

  // Update Gateway Info Header
  const titleEl = document.getElementById("gw-current-title");
  const descEl = document.getElementById("gw-current-desc");
  if (titleEl) titleEl.textContent = GATEWAYS[gwKey].name;
  if (descEl) descEl.textContent = GATEWAYS[gwKey].description;

  // Default open the first operation of this gateway
  const firstEp = GATEWAYS[gwKey].endpoints[0];
  if (firstEp) {
    openedOperations.add(firstEp.id);
  }

  renderOperations();
}

/**
 * Toggle an operation accordion open/closed
 */
function toggleOperation(opId, forceOpen = null) {
  const isOpen = openedOperations.has(opId);
  const nextState = forceOpen !== null ? forceOpen : !isOpen;

  if (nextState) {
    openedOperations.add(opId);
  } else {
    openedOperations.delete(opId);
  }

  const opCard = document.getElementById(`op-${opId}`);
  if (opCard) {
    opCard.classList.toggle("is-open", nextState);
    const headerBtn = opCard.querySelector(".op-header");
    if (headerBtn) {
      headerBtn.setAttribute("aria-expanded", String(nextState));
    }
  }
}

/**
 * Render the Swagger-style operation rows
 */
function renderOperations() {
  const container = document.getElementById("swagger-operations-list");
  if (!container) return;

  const gw = GATEWAYS[currentGateway];
  if (!gw) return;

  container.innerHTML = gw.endpoints.map(ep => {
    const isPost = ep.method === "POST";
    const methodLower = ep.method.toLowerCase();
    const isOpen = openedOperations.has(ep.id);
    const samplePayloadStr = ep.samplePayload ? JSON.stringify(ep.samplePayload, null, 2) : "";
    const sampleResponseStr = JSON.stringify(ep.sampleResponse, null, 2);

    return `
      <div class="op-card op-method-${methodLower} ${isOpen ? 'is-open' : ''}" id="op-${ep.id}">
        <!-- Operation Row Header -->
        <button type="button" class="op-header" aria-expanded="${isOpen}" onclick="toggleOperation('${ep.id}')">
          <div class="op-header-left">
            <span class="op-method-pill op-pill-${methodLower}">${ep.method}</span>
            <span class="op-path">${ep.path}</span>
            <span class="op-summary">${escapeHtml(ep.summary)}</span>
          </div>
          <div class="op-header-right">
            <svg class="op-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
        </button>

        <!-- Operation Collapsible Body -->
        <div class="op-body">
          <div class="op-desc-row">
            <p class="op-description">${escapeHtml(ep.description)}</p>
            <div class="op-url-badge">
              <code>${BASE_URL}${ep.path}</code>
            </div>
          </div>

          <div class="op-grid">
            <!-- Request Parameters / Body Column -->
            <div class="op-col op-req-col">
              <div class="op-col-header">
                <span class="op-col-title">Parameters & Request Body</span>
                ${isPost ? '<span class="op-content-type">application/json</span>' : '<span class="op-content-type">No Body</span>'}
              </div>

              ${isPost ? `
                <div class="op-editor-box">
                  <label for="payload-${ep.id}" class="sr-only">Request Payload JSON</label>
                  <textarea id="payload-${ep.id}" class="op-payload-textarea" spellcheck="false">${samplePayloadStr}</textarea>
                </div>
              ` : `
                <div class="op-no-params-box">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                  </svg>
                  <span>No parameters required. Directly query this endpoint via GET.</span>
                </div>
              `}

              <!-- Action Buttons -->
              <div class="op-actions-bar">
                <button type="button" class="btn btn-primary btn-sm" id="btn-exec-${ep.id}" onclick="executeEndpoint('${ep.id}')">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                  </svg>
                  <span>Execute</span>
                </button>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-curl-${ep.id}" onclick="copyEndpointCurl('${ep.id}')">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  <span>Copy cURL</span>
                </button>
                ${isPost ? `
                  <button type="button" class="btn btn-ghost btn-xs" onclick="resetEndpointPayload('${ep.id}')">
                    <span>Reset</span>
                  </button>
                ` : ''}
              </div>
            </div>

            <!-- Response Column -->
            <div class="op-col op-resp-col">
              <div class="op-col-header">
                <span class="op-col-title">Responses</span>
                <span class="op-status-sample">Expected 200 OK</span>
              </div>

              <!-- Live Server Response (Appears once executed) -->
              <div class="op-live-box" id="live-box-${ep.id}" style="display: none;">
                <div class="op-live-bar">
                  <div class="op-live-status-pill" id="live-pill-${ep.id}">
                    <span class="live-dot"></span>
                    <span id="live-code-${ep.id}">200 OK</span>
                  </div>
                  <span class="op-live-time" id="live-time-${ep.id}">~18ms</span>
                  <button type="button" class="op-mini-copy" onclick="copyLiveResponse('${ep.id}')" title="Copy response JSON">
                    Copy
                  </button>
                </div>
                <pre class="op-code-pre"><code id="live-output-${ep.id}"></code></pre>
              </div>

              <!-- Sample Response Documentation -->
              <div class="op-sample-box" id="sample-box-${ep.id}">
                <div class="op-sample-bar">
                  <span class="op-sample-label">Sample Response (application/json):</span>
                  <button type="button" class="op-mini-copy" onclick="copySampleResponse('${ep.id}')" title="Copy sample JSON">
                    Copy
                  </button>
                </div>
                <pre class="op-code-pre"><code>${sampleResponseStr}</code></pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Execute real HTTP request against the gateway
 */
async function executeEndpoint(epId) {
  const ep = findEndpoint(epId);
  if (!ep) return;

  const execBtn = document.getElementById(`btn-exec-${epId}`);
  const liveBox = document.getElementById(`live-box-${epId}`);
  const livePill = document.getElementById(`live-pill-${epId}`);
  const liveCode = document.getElementById(`live-code-${epId}`);
  const liveTime = document.getElementById(`live-time-${epId}`);
  const liveOutput = document.getElementById(`live-output-${epId}`);

  if (execBtn) {
    execBtn.disabled = true;
    execBtn.classList.add("loading");
    execBtn.innerHTML = `
      <svg class="spin-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
      </svg>
      <span>Executing...</span>
    `;
  }

  const url = `${BASE_URL}${ep.path}`;
  let options = {
    method: ep.method,
    headers: { "Accept": "application/json" }
  };

  if (ep.method === "POST") {
    const textarea = document.getElementById(`payload-${epId}`);
    const rawVal = textarea ? textarea.value.trim() : "";
    try {
      const parsed = JSON.parse(rawVal);
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(parsed);
    } catch (err) {
      alert("Invalid JSON format in request body. Please check commas and quotes.");
      resetExecBtn(execBtn);
      return;
    }
  }

  const startTime = performance.now();

  try {
    const res = await fetch(url, options);
    const latency = Math.round(performance.now() - startTime);

    let data;
    const text = await res.text();
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }

    if (liveBox) liveBox.style.display = "block";
    if (liveTime) liveTime.textContent = `~${latency}ms`;

    if (liveCode && livePill) {
      liveCode.textContent = `${res.status} ${res.statusText || 'OK'}`;
      livePill.className = "op-live-status-pill " + (res.ok ? "status-success" : (res.status >= 500 ? "status-error" : "status-warn"));
    }

    if (liveOutput) {
      liveOutput.textContent = typeof data === "object" ? JSON.stringify(data, null, 2) : data;
    }
  } catch (err) {
    const latency = Math.round(performance.now() - startTime);
    if (liveBox) liveBox.style.display = "block";
    if (liveTime) liveTime.textContent = `~${latency}ms`;
    if (liveCode && livePill) {
      liveCode.textContent = "Network Error";
      livePill.className = "op-live-status-pill status-error";
    }
    if (liveOutput) {
      liveOutput.textContent = `// Failed to fetch live gateway route.\n// Ensure https://idkhowtocodefr-hf-backend.hf.space is running and CORS is permitted.\n// Error: ${err.message}`;
    }
  } finally {
    resetExecBtn(execBtn);
  }
}

function resetExecBtn(btn) {
  if (!btn) return;
  btn.disabled = false;
  btn.classList.remove("loading");
  btn.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
    <span>Execute</span>
  `;
}

/**
 * Generate and copy cURL command
 */
function copyEndpointCurl(epId) {
  const ep = findEndpoint(epId);
  if (!ep) return;

  const url = `${BASE_URL}${ep.path}`;
  let cmd = "";

  if (ep.method === "GET") {
    cmd = `curl -X GET "${url}"`;
  } else {
    const textarea = document.getElementById(`payload-${epId}`);
    const rawVal = textarea ? textarea.value.trim() : JSON.stringify(ep.samplePayload);
    // Compact JSON for cURL command
    let compact = rawVal;
    try {
      compact = JSON.stringify(JSON.parse(rawVal));
    } catch {}
    cmd = `curl -X POST "${url}" \\\n  -H "Content-Type: application/json" \\\n  -d '${compact}'`;
  }

  copyToClipboard(cmd, `btn-curl-${epId}`, "Copy cURL");
}

/**
 * Reset payload textarea to original sample
 */
function resetEndpointPayload(epId) {
  const ep = findEndpoint(epId);
  if (!ep || !ep.samplePayload) return;
  const textarea = document.getElementById(`payload-${epId}`);
  if (textarea) {
    textarea.value = JSON.stringify(ep.samplePayload, null, 2);
  }
}

/**
 * Copy Live Response to clipboard
 */
function copyLiveResponse(epId) {
  const codeEl = document.getElementById(`live-output-${epId}`);
  if (codeEl) {
    navigator.clipboard.writeText(codeEl.textContent);
  }
}

/**
 * Copy Sample Response to clipboard
 */
function copySampleResponse(epId) {
  const ep = findEndpoint(epId);
  if (ep && ep.sampleResponse) {
    navigator.clipboard.writeText(JSON.stringify(ep.sampleResponse, null, 2));
  }
}

/**
 * Find endpoint data across all gateways
 */
function findEndpoint(epId) {
  for (const gwKey in GATEWAYS) {
    const found = GATEWAYS[gwKey].endpoints.find(e => e.id === epId);
    if (found) return found;
  }
  return null;
}

/**
 * Activate and expand an endpoint from external links (e.g., service cards)
 */
function activatePlayground(endpointId) {
  let targetGw = "hf-backend";
  if (endpointId.startsWith("heartflow")) targetGw = "heartflow";
  if (endpointId.startsWith("semantic")) targetGw = "semantic";

  selectGateway(targetGw);
  toggleOperation(endpointId, true);

  const targetCard = document.getElementById(`op-${endpointId}`);
  if (targetCard) {
    targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

/**
 * Helper: Copy text with tactile feedback
 */
function copyToClipboard(text, btnId, originalLabel) {
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    const prevHtml = btn.innerHTML;
    btn.innerHTML = `
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2.5">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span style="color: #34d399;">Copied!</span>
    `;
    setTimeout(() => {
      btn.innerHTML = prevHtml;
    }, 1500);
  });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  // Setup copy base URL widget in hero
  const copyBaseBtn = document.getElementById("copy-base-btn");
  if (copyBaseBtn) {
    copyBaseBtn.addEventListener("click", () => {
      copyToClipboard(BASE_URL, "copy-base-btn", "Copy");
    });
  }

  // Render operations
  selectGateway("hf-backend");
});
