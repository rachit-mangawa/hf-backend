/**
 * HF Backend — Swagger / FastAPI Style Interactive API Explorer
 * Built with Emil Kowalski design engineering principles:
 * - Direct, tactile feedback (< 140ms response states)
 * - Clean method-coded operation bars (GET in blue, POST in green)
 * - True-to-life production payloads matching live Hugging Face Space contracts
 * - Live request execution with direct timing & status feedback
 */

const DEFAULT_BASE_URL = "https://idkhowtocodefr-hf-backend.hf.space";
const BASE_URL = (typeof window !== "undefined" && window.location.hostname.endsWith(".hf.space"))
  ? window.location.origin
  : DEFAULT_BASE_URL;

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
          "loaded": {
            "/semantic": "semantic_backend.router:router",
            "/heartflow": "heartflow_backend.router:router"
          },
          "failed": {},
          "warm_status": {
            "/semantic": "warmed",
            "/heartflow": "warmed"
          },
          "total_warmup_seconds": 5.328
        }
      },
      {
        id: "hf-root",
        method: "GET",
        path: "/?format=json",
        summary: "Gateway Root & Status Telemetry",
        description: "Root gateway entrypoint. When queried with format=json (or Accept: application/json), returns core health and loaded route prefixes.",
        samplePayload: null,
        sampleResponse: {
          "status": "healthy",
          "loaded": {
            "/semantic": "semantic_backend.router:router",
            "/heartflow": "heartflow_backend.router:router"
          },
          "failed": {},
          "warm_status": {
            "/semantic": "warmed",
            "/heartflow": "warmed"
          },
          "total_warmup_seconds": 5.328
        }
      },
      {
        id: "hf-openapi",
        method: "GET",
        path: "/openapi.json",
        summary: "OpenAPI 3.1 Specification",
        description: "Dynamically generated OpenAPI schema documenting all mounted subproject routes, parameters, and schemas.",
        samplePayload: null,
        sampleResponse: {
          "openapi": "3.1.0",
          "info": {
            "title": "HF Backend Gateway",
            "description": "Pluggable aggregation gateway for independent Python microservices.",
            "version": "1.0.0"
          },
          "paths": {
            "/health": { "get": { "tags": ["Host Gateway"], "summary": "Health" } },
            "/status": { "get": { "tags": ["Host Gateway"], "summary": "Status Page" } },
            "/heartflow/predict": { "post": { "tags": ["HeartFlow OS"], "summary": "Predict" } },
            "/semantic/analyze": { "post": { "tags": ["Semantic Comment Analyzer"], "summary": "Analyze Text" } }
          }
        }
      },
      {
        id: "hf-status",
        method: "GET",
        path: "/status",
        responseType: "html",
        summary: "Developer Console (HTML Dashboard)",
        description: "Renders the interactive web status console with live latency, active middleware caps, and route explorer.",
        samplePayload: null,
        sampleResponse: "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <title>HF Backend Gateway Status</title>\n  <!-- Interactive Status Dashboard -->\n</head>\n<body>\n  <header>HF Backend Gateway &bull; Live Telemetry</header>\n</body>\n</html>"
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
        summary: "Arrhythmia & Disease Risk Ensemble",
        description: "Evaluates patient telemetry vitals through a weighted 5-model ensemble (Random Forest, Small NN, Logistic Regression, KNN, SVM) to classify risk.",
        samplePayload: {
          "Heart_Rate": 84.0,
          "SpO2_Level": 98.2,
          "Systolic_BP": 122.0,
          "Diastolic_BP": 79.0,
          "Body_Temp": 36.8
        },
        sampleResponse: {
          "prediction": false,
          "prediction_label": "Healthy",
          "probability": 0.9134,
          "ensemble_prediction": false,
          "model_outputs": {
            "knn": "Healthy",
            "svm": "Healthy",
            "logreg": "Healthy",
            "rf": "Healthy",
            "small_nn": "Healthy"
          },
          "model_probs": {
            "knn": 1.0,
            "svm": 0.9985,
            "logreg": 0.9396,
            "rf": 0.7029,
            "small_nn": 0.9999
          },
          "disease_probs": {
            "Healthy": 0.9134,
            "Diabetes Mellitus": 0.0838,
            "Hypertension": 0.0023,
            "Asthma": 0.0003,
            "Heart Disease": 0.0002
          },
          "weights": {
            "knn": 0.15,
            "svm": 0.15,
            "logreg": 0.2,
            "rf": 0.25,
            "small_nn": 0.25
          }
        }
      },
      {
        id: "heartflow-explain",
        method: "POST",
        path: "/heartflow/explain",
        summary: "Clinical Feature Attribution & SHAP Weights",
        description: "Computes physiological feature attribution scores and directional risk impacts for each patient telemetry vital.",
        samplePayload: {
          "Heart_Rate": 115.0,
          "SpO2_Level": 93.5,
          "Systolic_BP": 148.0,
          "Diastolic_BP": 95.0,
          "Body_Temp": 38.2
        },
        sampleResponse: {
          "shap_values": [
            0.1503,
            0.0529,
            -0.0211,
            0.1560,
            0.1114,
            0.0538
          ],
          "feature_names": [
            "Heart Rate (bpm)",
            "SpO2 Level (%)",
            "Systolic Blood Pressure (mmHg)",
            "Diastolic Blood Pressure (mmHg)",
            "Body Temperature (°C)",
            "Risk_Severity"
          ]
        }
      },
      {
        id: "heartflow-metrics",
        method: "GET",
        path: "/heartflow/metrics",
        summary: "Ensemble Validation & Classification Metrics",
        description: "Returns offline validation metrics, classification accuracy, macro F1, and edge inference latency benchmarks.",
        samplePayload: null,
        sampleResponse: {
          "ensemble_accuracy": 0.962,
          "ensemble_f1_macro": 0.948,
          "latency_microsec_edge": 18.4,
          "latency_is_estimated": true,
          "models": {
            "rf": { "accuracy": 0.954, "f1": 0.938, "weight": 0.25 },
            "small_nn": { "accuracy": 0.949, "f1": 0.931, "weight": 0.25 },
            "logreg": { "accuracy": 0.922, "f1": 0.904, "weight": 0.2 },
            "knn": { "accuracy": 0.918, "f1": 0.897, "weight": 0.15 },
            "svm": { "accuracy": 0.935, "f1": 0.912, "weight": 0.15 }
          }
        }
      },
      {
        id: "heartflow-dataset",
        method: "GET",
        path: "/heartflow/dataset?limit=2",
        summary: "Clinical Telemetry Sample Explorer",
        description: "Queries paginated observations from the 60,000-record patient telemetry dataset.",
        samplePayload: null,
        sampleResponse: {
          "total": 60000,
          "page": 1,
          "limit": 2,
          "total_pages": 30000,
          "features": [
            "Patient Number",
            "Heart Rate (bpm)",
            "SpO2 Level (%)",
            "Systolic Blood Pressure (mmHg)",
            "Diastolic Blood Pressure (mmHg)",
            "Body Temperature (°C)",
            "Fall Detection",
            "Predicted Disease",
            "Data Accuracy (%)",
            "Heart Rate Alert",
            "SpO2 Level Alert",
            "Blood Pressure Alert",
            "Temperature Alert"
          ],
          "rows": [
            {
              "Patient Number": 1,
              "Heart Rate (bpm)": 98,
              "SpO2 Level (%)": 96,
              "Systolic Blood Pressure (mmHg)": 120,
              "Diastolic Blood Pressure (mmHg)": 86,
              "Body Temperature (°C)": 38.1,
              "Fall Detection": "No",
              "Predicted Disease": "Diabetes Mellitus",
              "Data Accuracy (%)": 95,
              "Heart Rate Alert": "NORMAL"
            }
          ]
        }
      },
      {
        id: "heartflow-tinyml",
        method: "GET",
        path: "/heartflow/export_tinyml?model_name=rf&quantize=false",
        summary: "TinyML C99 Header Export",
        description: "Compiles trained decision tree arrays into a standalone zero-malloc C99 header for ESP32 and Arduino microcontrollers.",
        samplePayload: null,
        sampleResponse: {
          "code": "// HeartFlow OS TinyML C99 · Model: RF (FP32 Single-Precision) · Zero-Malloc · Static RAM: <64B\n#ifndef HEARTFLOW_MODEL_H\n#define HEARTFLOW_MODEL_H\n\n#include <stdint.h>\n#include <math.h>\n#include <string.h>\n\n#define N_CLASSES 5\n#define N_RAW_FEATURES 5\n#define N_SCALED_FEATURES 6\n// Model tree definitions...\n#endif"
        }
      },
      {
        id: "heartflow-health",
        method: "GET",
        path: "/heartflow/health",
        summary: "HeartFlow Runtime Readiness",
        description: "Confirms in-memory model weight warmups across all 5 ensemble classifiers.",
        samplePayload: null,
        sampleResponse: {
          "status": "Healthy",
          "models_loaded": true,
          "models": {
            "knn": true,
            "svm": true,
            "logreg": true,
            "rf": true,
            "small_nn": true
          },
          "retrain_enabled": true
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
        summary: "NLP Sentiment, Intent & Token Explainability",
        description: "Runs RoBERTa embeddings to detect intent classes (Praise, Complaint, Question, Feature Request, Bug Report), polarity, tone, urgency, and token-level attribution.",
        samplePayload: {
          "text": "Great API integration, lightweight and response times are extremely fast.",
          "threshold": 0.5,
          "include_explanation": true
        },
        sampleResponse: {
          "intent": {
            "labels": [
              "Praise"
            ],
            "scores": [
              0.8067
            ],
            "all_intents": {
              "Praise": 0.8067,
              "Feature Request": 0.0751,
              "Complaint": 0.0592,
              "Question": 0.0523,
              "Bug Report": 0.0067
            },
            "top_intent": "Praise",
            "top_confidence": 0.8067
          },
          "sentiment": {
            "label": "POSITIVE",
            "score": 0.9774
          },
          "explainability": [
            {
              "word": "Great",
              "contribution": 0.2263,
              "primary_intent": "Praise"
            },
            {
              "word": "lightweight",
              "contribution": 0.0722,
              "primary_intent": "Praise"
            },
            {
              "word": "fast.",
              "contribution": 0.1009,
              "primary_intent": "Praise"
            }
          ],
          "tone": "Appreciative",
          "urgency": "Low",
          "recommended_action": "Share with Team"
        }
      },
      {
        id: "semantic-batch",
        method: "POST",
        path: "/semantic/batch",
        contentType: "multipart/form-data",
        summary: "Streaming CSV Batch Analysis",
        description: "Streams CSV comment datasets through the NLP inference pipeline, returning a classified CSV with intent, sentiment, tone, and action recommendations.",
        samplePayload: "text\nGreat API integration, lightweight and fast.\nNeeds more documentation on endpoint rate limits.\nSlow response times under high concurrency.",
        sampleResponse: "TEXT,INTENT,CONFIDENCE,SENTIMENT,SENTIMENT_SCORE,TONE,URGENCY,RECOMMENDED_ACTION\n\"Great API integration, lightweight and fast.\",Praise,0.94,POSITIVE,0.95,Appreciative,Low,Share with Team\n\"Needs more documentation on endpoint rate limits.\",Question,0.68,NEUTRAL,0.52,Objective,Medium,Route to Support\n\"Slow response times under high concurrency.\",Complaint,0.88,NEGATIVE,0.91,Critical,High,Escalate to Engineering"
      },
      {
        id: "semantic-health",
        method: "GET",
        path: "/semantic/health",
        summary: "Semantic Service Readiness",
        description: "Confirms Transformer model embeddings, classifier heads, and sentiment pipelines are resident in RAM.",
        samplePayload: null,
        sampleResponse: {
          "status": "healthy",
          "service": "semantic_backend",
          "models_loaded": {
            "embedding": true,
            "classifier_head": true,
            "sentiment": true
          }
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
    const isMultipart = ep.contentType === "multipart/form-data";
    const methodLower = ep.method.toLowerCase();
    const isOpen = openedOperations.has(ep.id);
    const samplePayloadStr = ep.samplePayload
      ? (typeof ep.samplePayload === "string" ? ep.samplePayload : JSON.stringify(ep.samplePayload, null, 2))
      : "";
    const sampleResponseStr = typeof ep.sampleResponse === "string"
      ? ep.sampleResponse
      : JSON.stringify(ep.sampleResponse, null, 2);

    let contentTypeLabel = "No Body";
    if (isMultipart) {
      contentTypeLabel = "multipart/form-data (CSV)";
    } else if (isPost) {
      contentTypeLabel = "application/json";
    }

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
                <span class="op-content-type">${contentTypeLabel}</span>
              </div>

              ${(isPost || isMultipart) ? `
                <div class="op-editor-box">
                  <label for="payload-${ep.id}" class="sr-only">${isMultipart ? 'CSV Content' : 'Request Payload JSON'}</label>
                  <textarea id="payload-${ep.id}" class="op-payload-textarea" spellcheck="false">${escapeHtml(samplePayloadStr)}</textarea>
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
                ${(isPost || isMultipart) ? `
                  <button type="button" class="btn btn-ghost btn-xs" onclick="resetEndpointPayload('${ep.id}')">
                    <span>Reset</span>
                  </button>
                ` : ''}
              </div>
            </div>

            <!-- Response Column -->
            <div class="op-col op-resp-col">
              <div class="op-col-header">
                <div class="op-resp-tabs" role="tablist">
                  <button type="button" class="op-resp-tab active" id="tab-sample-${ep.id}" onclick="setResponseTab('${ep.id}', 'sample')">
                    Sample Contract
                  </button>
                  <button type="button" class="op-resp-tab" id="tab-live-${ep.id}" onclick="setResponseTab('${ep.id}', 'live')" style="display: none;">
                    <span class="live-dot"></span>
                    <span id="tab-live-label-${ep.id}">Live Response</span>
                  </button>
                </div>
                <span class="op-status-sample" id="resp-status-${ep.id}">Expected 200 OK</span>
              </div>

              <!-- Live Server Response (Shown when executed) -->
              <div class="op-live-box" id="live-box-${ep.id}" style="display: none;">
                <div class="op-live-bar">
                  <div class="op-live-status-pill" id="live-pill-${ep.id}">
                    <span class="live-dot"></span>
                    <span id="live-code-${ep.id}">200 OK</span>
                  </div>
                  <span class="op-live-time" id="live-time-${ep.id}">~18ms</span>
                  <div class="op-live-actions">
                    <button type="button" class="op-view-toggle-btn" onclick="setResponseTab('${ep.id}', 'sample')" title="View sample response schema">
                      View Sample
                    </button>
                    <button type="button" class="op-mini-copy" onclick="copyLiveResponse('${ep.id}')" title="Copy response">
                      Copy
                    </button>
                  </div>
                </div>
                <pre class="op-code-pre"><code id="live-output-${ep.id}"></code></pre>
              </div>

              <!-- Sample Response Documentation (Default view) -->
              <div class="op-sample-box" id="sample-box-${ep.id}">
                <div class="op-sample-bar">
                  <span class="op-sample-label">Sample Response (${isMultipart ? 'text/csv' : 'application/json'}):</span>
                  <div class="op-sample-actions">
                    <button type="button" class="op-view-toggle-btn" id="btn-show-live-${ep.id}" onclick="setResponseTab('${ep.id}', 'live')" style="display: none;" title="Return to live response">
                      View Live
                    </button>
                    <button type="button" class="op-mini-copy" onclick="copySampleResponse('${ep.id}')" title="Copy sample">
                      Copy
                    </button>
                  </div>
                </div>
                <pre class="op-code-pre"><code>${escapeHtml(sampleResponseStr)}</code></pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Execute real HTTP request against the live gateway
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
    headers: {}
  };

  if (ep.method === "GET") {
    if (ep.responseType === "html") {
      options.headers["Accept"] = "text/html, */*";
    } else {
      options.headers["Accept"] = "application/json, */*";
    }
  }

  if (ep.method === "POST") {
    const textarea = document.getElementById(`payload-${epId}`);
    const rawVal = textarea ? textarea.value.trim() : "";

    if (ep.contentType === "multipart/form-data") {
      // Build real multipart/form-data containing the CSV file
      const formData = new FormData();
      const csvBlob = new Blob([rawVal], { type: "text/csv" });
      formData.append("file", csvBlob, "comments.csv");
      formData.append("threshold", "0.5");
      formData.append("targetColumn", "text");

      options.body = formData;
      options.headers["Accept"] = "text/csv, application/json, */*";
      // Note: do NOT set Content-Type header; browser must populate multipart boundary automatically.
    } else {
      try {
        const parsed = JSON.parse(rawVal);
        options.headers["Content-Type"] = "application/json";
        options.headers["Accept"] = "application/json";
        options.body = JSON.stringify(parsed);
      } catch (err) {
        alert("Invalid JSON format in request body. Please verify double quotes and syntax.");
        resetExecBtn(execBtn);
        return;
      }
    }
  }

  const startTime = performance.now();

  try {
    const res = await fetch(url, options);
    const latency = Math.round(performance.now() - startTime);

    const contentType = res.headers.get("content-type") || "";
    const rawText = await res.text();

    let displayOutput = rawText;
    if (contentType.includes("application/json")) {
      try {
        const parsedJson = JSON.parse(rawText);
        displayOutput = JSON.stringify(parsedJson, null, 2);
      } catch {
        displayOutput = rawText;
      }
    }

    if (liveTime) liveTime.textContent = `~${latency}ms`;

    if (liveCode && livePill) {
      liveCode.textContent = `${res.status} ${res.statusText || (res.ok ? 'OK' : 'Error')}`;
      livePill.className = "op-live-status-pill " + (res.ok ? "status-success" : (res.status >= 500 ? "status-error" : "status-warn"));
    }

    if (liveOutput) {
      liveOutput.textContent = displayOutput;
    }

    const tabLiveLabel = document.getElementById(`tab-live-label-${epId}`);
    if (tabLiveLabel) {
      tabLiveLabel.textContent = `Live (${res.status})`;
    }

    // Switch to single Live view (hides sample view, preventing double view)
    setResponseTab(epId, "live");
  } catch (err) {
    const latency = Math.round(performance.now() - startTime);
    if (liveTime) liveTime.textContent = `~${latency}ms`;
    if (liveCode && livePill) {
      liveCode.textContent = "Network Error";
      livePill.className = "op-live-status-pill status-error";
    }
    if (liveOutput) {
      const isFileProtocol = window.location.protocol === "file:";
      liveOutput.textContent = `// Network Request Failed\n// Target URL: ${url}\n// Error: ${err.message}\n` +
        (isFileProtocol
          ? `// Note: When opening index.html via local file:// protocol, browser security blocks CORS.\n// Run: 'python -m http.server 8000 --directory frontend' and open http://localhost:8000\n// Or visit GitHub Pages at https://rachit-mangawa.github.io/hf-backend/`
          : `// Ensure ${BASE_URL} is awake and reachable.`);
    }

    const tabLiveLabel = document.getElementById(`tab-live-label-${epId}`);
    if (tabLiveLabel) {
      tabLiveLabel.textContent = "Live (Error)";
    }

    setResponseTab(epId, "live");
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
 * Switch between Live Response view and Sample Contract view
 * Ensures only ONE view is displayed at a time (preventing double view)
 */
function setResponseTab(epId, tabName) {
  const liveBox = document.getElementById(`live-box-${epId}`);
  const sampleBox = document.getElementById(`sample-box-${epId}`);
  const tabLive = document.getElementById(`tab-live-${epId}`);
  const tabSample = document.getElementById(`tab-sample-${epId}`);
  const btnShowLive = document.getElementById(`btn-show-live-${epId}`);

  if (tabName === "live") {
    if (sampleBox) sampleBox.style.display = "none";
    if (liveBox) liveBox.style.display = "flex";
    if (tabLive) {
      tabLive.style.display = "inline-flex";
      tabLive.classList.add("active");
    }
    if (tabSample) tabSample.classList.remove("active");
    if (btnShowLive) btnShowLive.style.display = "none";
  } else {
    // Show sample contract
    if (liveBox) liveBox.style.display = "none";
    if (sampleBox) sampleBox.style.display = "flex";
    if (tabSample) tabSample.classList.add("active");
    if (tabLive) tabLive.classList.remove("active");

    // If liveBox has executed output, show "View Live" button in the sample bar
    const liveCode = document.getElementById(`live-output-${epId}`);
    if (btnShowLive && liveCode && liveCode.textContent.trim()) {
      btnShowLive.style.display = "inline-block";
    }
  }
}

/**
 * Generate and copy cURL command
 */
function copyEndpointCurl(epId) {
  const ep = findEndpoint(epId);
  if (!ep) return;

  const url = `${BASE_URL}${ep.path}`;
  let cmd = "";

  if (ep.contentType === "multipart/form-data") {
    cmd = `curl -X POST "${url}" \\\n  -F "file=@comments.csv" \\\n  -F "threshold=0.5" \\\n  -F "targetColumn=text"`;
  } else if (ep.method === "POST") {
    const textarea = document.getElementById(`payload-${epId}`);
    const rawVal = textarea ? textarea.value.trim() : JSON.stringify(ep.samplePayload);
    let compact = rawVal;
    try {
      compact = JSON.stringify(JSON.parse(rawVal));
    } catch {}
    cmd = `curl -X POST "${url}" \\\n  -H "Content-Type: application/json" \\\n  -d '${compact}'`;
  } else {
    cmd = `curl -X GET "${url}"`;
  }

  copyToClipboard(cmd, `btn-curl-${epId}`, "Copy cURL");
}

/**
 * Reset payload textarea to original sample and restore sample response view
 */
function resetEndpointPayload(epId) {
  const ep = findEndpoint(epId);
  if (!ep) return;
  if (ep.samplePayload) {
    const textarea = document.getElementById(`payload-${epId}`);
    if (textarea) {
      textarea.value = typeof ep.samplePayload === "string"
        ? ep.samplePayload
        : JSON.stringify(ep.samplePayload, null, 2);
    }
  }
  // Reset response view back to Sample only
  setResponseTab(epId, "sample");
  const tabLive = document.getElementById(`tab-live-${epId}`);
  if (tabLive) tabLive.style.display = "none";
  const btnShowLive = document.getElementById(`btn-show-live-${epId}`);
  if (btnShowLive) btnShowLive.style.display = "none";
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
    const val = typeof ep.sampleResponse === "string"
      ? ep.sampleResponse
      : JSON.stringify(ep.sampleResponse, null, 2);
    navigator.clipboard.writeText(val);
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
  // Sync target URL in info bar
  const targetBaseCode = document.getElementById("gw-base-url-code");
  if (targetBaseCode) {
    targetBaseCode.textContent = BASE_URL;
  }

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
