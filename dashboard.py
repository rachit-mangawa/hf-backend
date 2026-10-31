"""Developer Console and Status Dashboard renderer for HF Backend Gateway.

Renders system telemetry, registered service cards, dynamic endpoint explorers,
and real-time health monitors with a modern, high-craft developer interface.
Completely generic: dynamically inspects any registered routers and endpoints
without hardcoded project names.
"""

import html
import json
from typing import Any


def render_statuspage(
    health_data: dict[str, Any],
    gateway_info: dict[str, Any] | None = None,
    routes_info: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    status = health_data.get("status", "unknown")
    loaded = health_data.get("loaded", {})
    failed = health_data.get("failed", {})
    warm_status = health_data.get("warm_status", {})
    warmup_seconds = health_data.get("total_warmup_seconds", 0.0)

    gateway_cfg = gateway_info or {}
    routes_map = routes_info or {}

    max_size_mb = round(gateway_cfg.get("max_body_size_bytes", 10485760) / (1024 * 1024), 1)
    timeout_s = round(gateway_cfg.get("request_timeout_seconds", 60.0), 1)
    docs_url = gateway_cfg.get("docs_url", "/project")

    # Status badge config
    if status == "healthy":
        status_label = "All Systems Operational"
        status_color = "#10b981"
        status_bg = "rgba(16, 185, 129, 0.1)"
        status_border = "rgba(16, 185, 129, 0.25)"
        status_dot = "#10b981"
    elif status == "degraded":
        status_label = "System Degraded"
        status_color = "#f59e0b"
        status_bg = "rgba(245, 158, 11, 0.1)"
        status_border = "rgba(245, 158, 11, 0.25)"
        status_dot = "#f59e0b"
    else:
        status_label = "Service Disruption"
        status_color = "#f43f5e"
        status_bg = "rgba(244, 63, 94, 0.1)"
        status_border = "rgba(244, 63, 94, 0.25)"
        status_dot = "#f43f5e"

    total_services = len(loaded) + len(failed)
    total_endpoints = sum(len(routes) for routes in routes_map.values())

    # Build service cards dynamically without hardcoded project names
    service_cards = []
    for prefix, target in loaded.items():
        w_stat = warm_status.get(prefix, "unknown")
        if w_stat == "warmed":
            warm_pill = '<span class="pill pill-success">Warmed</span>'
        elif w_stat == "no warmup":
            warm_pill = '<span class="pill pill-neutral">No Warmup</span>'
        else:
            warm_pill = f'<span class="pill pill-danger">{html.escape(w_stat)}</span>'

        service_routes = routes_map.get(prefix, [])
        route_count = len(service_routes)

        # Build dynamic route list
        route_items = []
        for r in service_routes:
            methods_html = "".join(
                f'<span class="method-tag method-{html.escape(m.lower())}">{html.escape(m)}</span>'
                for m in r.get("methods", ["GET"])
            )
            r_path = html.escape(r.get("path", ""))
            route_items.append(
                f"""
                <div class="endpoint-row" data-path="{r_path}">
                  <div class="endpoint-left">
                    {methods_html}
                    <code class="endpoint-path">{r_path}</code>
                  </div>
                  <div class="endpoint-actions">
                    <button type="button" class="action-btn" onclick="copySnippet('curl -s http://localhost:7860{r_path}')" title="Copy cURL command">cURL</button>
                    <a href="{html.escape(docs_url)}" class="action-btn" title="Open in Swagger UI">Docs</a>
                  </div>
                </div>
                """
            )

        routes_html = (
            "\n".join(route_items)
            if route_items
            else f'<div class="no-endpoints">No custom endpoints mapped. Health check: <code>{html.escape(prefix)}/health</code></div>'
        )

        service_cards.append(
            f"""
            <div class="card service-card" data-service-prefix="{html.escape(prefix)}" data-service-target="{html.escape(target)}">
              <div class="card-header">
                <div class="service-identity">
                  <div class="prefix-wrap">
                    <span class="service-prefix">{html.escape(prefix)}</span>
                    <span class="endpoint-count-badge">{route_count} route{'s' if route_count != 1 else ''}</span>
                  </div>
                  <code class="service-target">{html.escape(target)}</code>
                </div>
                <div class="service-badges">
                  <span class="pill pill-success">Mounted</span>
                  {warm_pill}
                </div>
              </div>

              <div class="endpoints-wrapper">
                <div class="endpoints-header">
                  <span>Registered Endpoints</span>
                  <a href="{html.escape(prefix)}/health" target="_blank" class="sub-link">Check {html.escape(prefix)}/health &rarr;</a>
                </div>
                <div class="endpoints-list">
                  {routes_html}
                </div>
              </div>
            </div>
            """
        )

    # Failed service cards
    for prefix, err in failed.items():
        service_cards.append(
            f"""
            <div class="card service-card service-failed" data-service-prefix="{html.escape(prefix)}">
              <div class="card-header">
                <div class="service-identity">
                  <span class="service-prefix">{html.escape(prefix)}</span>
                  <span class="service-error-title">Mount Failure</span>
                </div>
                <div class="service-badges">
                  <span class="pill pill-danger">Failed to Mount</span>
                </div>
              </div>
              <div class="error-box">
                <code>{html.escape(err)}</code>
              </div>
            </div>
            """
        )

    services_rendered = (
        "\n".join(service_cards)
        if service_cards
        else '<div class="empty-state">No services registered in <code>registry.py</code>.</div>'
    )

    raw_json_str = json.dumps(health_data, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HF Backend Gateway Status</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>">
  <style>
    :root {{
      --bg: #090d16;
      --bg-card: #0f172a;
      --bg-card-hover: #131c31;
      --bg-subtle: #1e293b;
      --border: #1e2838;
      --border-hover: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent: #38bdf8;
      --accent-muted: rgba(56, 189, 248, 0.12);
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #f43f5e;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1.25rem 4rem;
      background-image: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.05), transparent 60%);
    }}

    .container {{
      width: 100%;
      max-width: 960px;
    }}

    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .brand-mark {{
      width: 32px;
      height: 32px;
      background: var(--accent-muted);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.1rem;
    }}

    .brand-title {{
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text);
    }}

    .brand-badge {{
      font-size: 0.7rem;
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
      border: 1px solid var(--border);
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .nav-btn {{
      font-size: 0.8rem;
      font-weight: 500;
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.15s ease;
      cursor: pointer;
    }}

    .nav-btn:hover {{
      color: var(--text);
      border-color: var(--border-hover);
      background: var(--bg-card-hover);
    }}

    .nav-btn-primary {{
      background: var(--accent-muted);
      border-color: rgba(56, 189, 248, 0.3);
      color: var(--accent);
    }}

    .nav-btn-primary:hover {{
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--accent);
    }}

    /* Status Banner */
    .banner {{
      background: {status_bg};
      border: 1px solid {status_border};
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.75rem;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    .banner-left {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .status-dot {{
      width: 10px;
      height: 10px;
      background-color: {status_dot};
      border-radius: 50%;
      box-shadow: 0 0 10px {status_dot};
    }}

    .banner-headline {{
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--text);
    }}

    .banner-meta {{
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.1rem;
    }}

    .banner-telemetry {{
      display: flex;
      align-items: center;
      gap: 1rem;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    .latency-pill {{
      font-family: var(--font-mono);
      background: rgba(0, 0, 0, 0.3);
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      border: 1px solid var(--border);
      color: var(--text);
    }}

    /* Metrics Grid */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }}

    @media (max-width: 768px) {{
      .metrics-grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}

    @media (max-width: 480px) {{
      .metrics-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .metric-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1.15rem 1.25rem;
    }}

    .metric-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      font-weight: 600;
      margin-bottom: 0.4rem;
    }}

    .metric-value {{
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text);
      font-feature-settings: "tnum";
    }}

    .metric-sub {{
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}

    /* Navigation Tabs & Search Controls */
    .controls-strip {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}

    .tab-nav {{
      display: flex;
      gap: 0.35rem;
      background: rgba(15, 23, 42, 0.6);
      padding: 0.25rem;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.8rem;
      font-weight: 500;
      padding: 0.35rem 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .tab-btn.active {{
      background: var(--bg-subtle);
      color: var(--text);
    }}

    .search-box {{
      position: relative;
      flex: 1;
      max-width: 320px;
    }}

    .search-input {{
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      font-size: 0.8rem;
      padding: 0.4rem 0.75rem 0.4rem 2rem;
      outline: none;
      transition: border-color 0.15s ease;
    }}

    .search-input:focus {{
      border-color: var(--accent);
    }}

    .search-icon {{
      position: absolute;
      left: 0.65rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 0.75rem;
      pointer-events: none;
    }}

    /* Service Cards */
    .tab-content {{
      display: none;
    }}

    .tab-content.active {{
      display: block;
    }}

    .services-stack {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }}

    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.4rem;
      transition: border-color 0.15s ease;
    }}

    .card:hover {{
      border-color: var(--border-hover);
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}

    .prefix-wrap {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .service-prefix {{
      font-family: var(--font-mono);
      font-weight: 700;
      font-size: 1.15rem;
      color: var(--accent);
    }}

    .endpoint-count-badge {{
      font-size: 0.7rem;
      font-family: var(--font-mono);
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-muted);
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      border: 1px solid var(--border);
    }}

    .service-target {{
      display: block;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }}

    .service-badges {{
      display: flex;
      gap: 0.4rem;
      align-items: center;
    }}

    .pill {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0.2rem 0.6rem;
      border-radius: 9999px;
      border: 1px solid transparent;
    }}

    .pill-success {{
      background: rgba(16, 185, 129, 0.12);
      color: var(--success);
      border-color: rgba(16, 185, 129, 0.25);
    }}

    .pill-neutral {{
      background: rgba(100, 116, 139, 0.15);
      color: var(--text-muted);
      border-color: rgba(100, 116, 139, 0.25);
    }}

    .pill-danger {{
      background: rgba(244, 63, 94, 0.12);
      color: var(--danger);
      border-color: rgba(244, 63, 94, 0.25);
    }}

    /* Endpoints Explorer inside Cards */
    .endpoints-wrapper {{
      border-top: 1px solid var(--border);
      padding-top: 1rem;
      margin-top: 0.75rem;
    }}

    .endpoints-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
    }}

    .sub-link {{
      color: var(--accent);
      text-decoration: none;
      font-family: var(--font-mono);
      font-size: 0.75rem;
    }}

    .sub-link:hover {{
      text-decoration: underline;
    }}

    .endpoints-list {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}

    .endpoint-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(0, 0, 0, 0.2);
      padding: 0.45rem 0.75rem;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.03);
      font-family: var(--font-mono);
      font-size: 0.8rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}

    .endpoint-left {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}

    .method-tag {{
      font-size: 0.65rem;
      font-weight: 700;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      text-transform: uppercase;
    }}

    .method-get {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; }}
    .method-post {{ background: rgba(16, 185, 129, 0.15); color: #10b981; }}
    .method-websocket, .method-ws {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; }}
    .method-delete {{ background: rgba(244, 63, 94, 0.15); color: #f43f5e; }}

    .endpoint-path {{
      color: var(--text);
    }}

    .endpoint-actions {{
      display: flex;
      gap: 0.35rem;
    }}

    .action-btn {{
      font-size: 0.7rem;
      font-family: var(--font-sans);
      background: var(--bg-subtle);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.15s ease;
    }}

    .action-btn:hover {{
      color: var(--text);
      border-color: var(--border-hover);
    }}

    .service-failed {{
      background: rgba(244, 63, 94, 0.03);
      border-color: rgba(244, 63, 94, 0.3);
    }}

    .service-error-title {{
      color: var(--danger);
      font-size: 0.85rem;
      font-weight: 600;
      display: block;
      margin-top: 0.25rem;
    }}

    .error-box {{
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(244, 63, 94, 0.2);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: #fda4af;
      overflow-x: auto;
    }}

    /* Gateway Specs Tab */
    .specs-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      margin-bottom: 1.5rem;
    }}

    .specs-table th, .specs-table td {{
      padding: 0.75rem 1rem;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}

    .specs-table th {{
      color: var(--text-dim);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
    }}

    .specs-table td {{
      color: var(--text-muted);
    }}

    .specs-table code {{
      font-family: var(--font-mono);
      color: var(--text);
    }}

    /* Raw JSON Viewer */
    .json-box {{
      background: #020617;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #38bdf8;
      overflow-x: auto;
      max-height: 480px;
    }}

    /* Toast Notification */
    .toast {{
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: var(--bg-subtle);
      border: 1px solid var(--border-hover);
      color: var(--text);
      font-size: 0.8rem;
      padding: 0.6rem 1.2rem;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.2s ease;
      pointer-events: none;
      z-index: 100;
    }}

    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}

    footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 2rem;
      border-top: 1px solid var(--border);
      font-size: 0.8rem;
      color: var(--text-dim);
      flex-wrap: wrap;
      gap: 1rem;
      margin-top: auto;
    }}

    .footer-links {{
      display: flex;
      gap: 1rem;
    }}

    .footer-links a {{
      color: var(--text-muted);
      text-decoration: none;
      transition: color 0.15s ease;
    }}

    .footer-links a:hover {{
      color: var(--text);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-group">
        <div class="brand-mark">⚡</div>
        <div>
          <div class="brand-title">HF Backend Gateway</div>
          <div class="brand-badge">Hugging Face Space &bull; Port 7860</div>
        </div>
      </div>
      <div class="header-actions">
        <button type="button" class="nav-btn" id="btn-refresh" onclick="refreshHealth()">
          <span id="refresh-icon">&#8635;</span> Refresh
        </button>
        <a href="{html.escape(docs_url)}" class="nav-btn nav-btn-primary" title="Open Interactive API Docs">Swagger UI &rarr;</a>
        <a href="/health" class="nav-btn" target="_blank" title="View raw JSON health response">/health</a>
      </div>
    </header>

    <div class="banner">
      <div class="banner-left">
        <div class="status-dot"></div>
        <div>
          <div class="banner-headline" id="banner-text">{status_label}</div>
          <div class="banner-meta">Memory-resident routers with fast-fail isolation</div>
        </div>
      </div>
      <div class="banner-telemetry">
        <span>Latency: <strong class="latency-pill" id="latency-label">~10ms</strong></span>
        <span>Auto-refresh: <input type="checkbox" id="auto-refresh-toggle" checked onchange="toggleAutoRefresh(this.checked)" style="vertical-align: middle; cursor: pointer;"></span>
      </div>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Mounted Services</div>
        <div class="metric-value">{len(loaded)} / {total_services}</div>
        <div class="metric-sub">{len(failed)} mount failure{'s' if len(failed) != 1 else ''}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Active Routes</div>
        <div class="metric-value">{total_endpoints}</div>
        <div class="metric-sub">Across registered subprojects</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Warmup Duration</div>
        <div class="metric-value">{warmup_seconds:.2f}s</div>
        <div class="metric-sub">Lifespan sequential pre-warming</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Payload Guard</div>
        <div class="metric-value">{max_size_mb} MB</div>
        <div class="metric-sub">{timeout_s}s execution timeout</div>
      </div>
    </div>

    <div class="controls-strip">
      <div class="tab-nav">
        <button type="button" class="tab-btn active" onclick="switchTab('services')">Registered Services</button>
        <button type="button" class="tab-btn" onclick="switchTab('specs')">Gateway Specs</button>
        <button type="button" class="tab-btn" onclick="switchTab('json')">Raw JSON</button>
      </div>

      <div class="search-box">
        <span class="search-icon">&#128269;</span>
        <input type="text" id="route-filter" class="search-input" placeholder="Filter routes or services... [/]" oninput="filterServices(this.value)">
      </div>
    </div>

    <!-- Tab 1: Services & Routes -->
    <div id="tab-services" class="tab-content active">
      <div class="services-stack" id="services-list">
        {services_rendered}
      </div>
    </div>

    <!-- Tab 2: Gateway Specs -->
    <div id="tab-specs" class="tab-content">
      <div class="card">
        <h3 style="font-size: 0.95rem; margin-bottom: 1rem; color: var(--text);">Gateway Security &amp; Middleware Configuration</h3>
        <table class="specs-table">
          <thead>
            <tr>
              <th>Component</th>
              <th>Enforcement Rule</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>SecurityHeadersMiddleware</code></td>
              <td>nosniff, Referrer-Policy, X-XSS-Protection, HSTS on HTTPS</td>
              <td><span class="pill pill-success">Enforced</span></td>
            </tr>
            <tr>
              <td><code>Frame-Ancestors CSP</code></td>
              <td>Allows <code>huggingface.co</code> framing; blocks external clickjacking</td>
              <td><span class="pill pill-success">Enforced</span></td>
            </tr>
            <tr>
              <td><code>RequestLimitMiddleware</code></td>
              <td>Hard ceiling: {max_size_mb} MB body; {timeout_s}s timeout</td>
              <td><span class="pill pill-success">Active</span></td>
            </tr>
            <tr>
              <td><code>Interactive API Documentation</code></td>
              <td>Swagger UI at <code>{html.escape(docs_url)}</code></td>
              <td><span class="pill pill-success">Online</span></td>
            </tr>
            <tr>
              <td><code>Container Pre-warming</code></td>
              <td>Weights baked into Docker layer via <code>prefetch.py</code></td>
              <td><span class="pill pill-success">Baked</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 3: Raw JSON -->
    <div id="tab-json" class="tab-content">
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
          <span style="font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono);">GET /health response payload</span>
          <button type="button" class="action-btn" onclick="copySnippet(document.getElementById('raw-json-code').innerText)">Copy JSON</button>
        </div>
        <pre class="json-box"><code id="raw-json-code">{html.escape(raw_json_str)}</code></pre>
      </div>
    </div>

    <footer>
      <span>HF Gateway Engine &bull; Hugging Face Docker Space</span>
      <div class="footer-links">
        <a href="{html.escape(docs_url)}">Swagger Docs</a>
        <a href="/health">/health</a>
        <a href="/openapi.json">OpenAPI Spec</a>
        <a href="https://github.com/rachit-mangawa/hf-backend" target="_blank" rel="noopener">GitHub</a>
      </div>
    </footer>
  </div>

  <div id="toast" class="toast">Copied to clipboard</div>

  <script>
    // Tab switching
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
      const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (activeBtn) activeBtn.classList.add('active');
      const target = document.getElementById('tab-' + tabId);
      if (target) target.classList.add('active');
    }}

    // Filter services and endpoints
    function filterServices(query) {{
      const q = query.toLowerCase().trim();
      document.querySelectorAll('.service-card').forEach(card => {{
        const prefix = card.getAttribute('data-service-prefix') || '';
        const target = card.getAttribute('data-service-target') || '';
        let hasMatchingEndpoint = false;
        card.querySelectorAll('.endpoint-row').forEach(row => {{
          const path = row.getAttribute('data-path') || '';
          if (!q || path.toLowerCase().includes(q)) {{
            row.style.display = 'flex';
            hasMatchingEndpoint = true;
          }} else {{
            row.style.display = 'none';
          }}
        }});

        if (!q || prefix.toLowerCase().includes(q) || target.toLowerCase().includes(q) || hasMatchingEndpoint) {{
          card.style.display = 'block';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    // Copy to clipboard with toast notification
    function copySnippet(text) {{
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard'));
      }} else {{
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showToast('Copied to clipboard');
      }}
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }}

    // Live health refresh
    let autoRefreshTimer = null;
    function refreshHealth() {{
      const t0 = performance.now();
      const icon = document.getElementById('refresh-icon');
      if (icon) icon.style.transform = 'rotate(180deg)';
      fetch('/health')
        .then(r => {{
          const ms = Math.round(performance.now() - t0);
          document.getElementById('latency-label').innerText = ms + 'ms';
          return r.json();
        }})
        .then(data => {{
          document.getElementById('raw-json-code').innerText = JSON.stringify(data, null, 2);
          if (icon) icon.style.transform = 'none';
        }})
        .catch(err => {{
          document.getElementById('latency-label').innerText = 'offline';
          if (icon) icon.style.transform = 'none';
        }});
    }}

    function toggleAutoRefresh(enable) {{
      if (autoRefreshTimer) clearInterval(autoRefreshTimer);
      if (enable) {{
        autoRefreshTimer = setInterval(refreshHealth, 10000);
      }}
    }}

    // Initial setup
    toggleAutoRefresh(true);

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {{
      if (e.key === '/' && document.activeElement !== document.getElementById('route-filter')) {{
        e.preventDefault();
        document.getElementById('route-filter').focus();
      }} else if (e.key === 'r' && e.target.tagName !== 'INPUT') {{
        refreshHealth();
      }}
    }});
  </script>
</body>
</html>
"""
