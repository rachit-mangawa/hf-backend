"""Minimalist Statuspage HTML renderer for HF Backend Gateway.

Renders system status, per-project readiness badges, boot warmup timings,
and endpoint links with clean, modern dark-mode styling.
"""

import html
from typing import Any


def render_statuspage(health_data: dict[str, Any]) -> str:
    status = health_data.get("status", "unknown")
    loaded = health_data.get("loaded", {})
    failed = health_data.get("failed", {})
    warm_status = health_data.get("warm_status", {})
    warmup_seconds = health_data.get("total_warmup_seconds", 0.0)

    if status == "healthy":
        beacon_color = "#10b981"
        beacon_bg = "rgba(16, 185, 129, 0.12)"
        beacon_border = "rgba(16, 185, 129, 0.3)"
        status_text = "All Systems Operational"
        status_icon = "●"
    elif status == "degraded":
        beacon_color = "#f59e0b"
        beacon_bg = "rgba(245, 158, 11, 0.12)"
        beacon_border = "rgba(245, 158, 11, 0.3)"
        status_text = "System Degraded"
        status_icon = "▲"
    else:
        beacon_color = "#ef4444"
        beacon_bg = "rgba(239, 68, 68, 0.12)"
        beacon_border = "rgba(239, 68, 68, 0.3)"
        status_text = "System Disruption"
        status_icon = "✕"

    service_rows = []
    # Loaded projects
    for prefix, target in loaded.items():
        w_stat = warm_status.get(prefix, "unknown")
        if w_stat == "warmed":
            warm_badge = '<span class="badge badge-success">Warmed</span>'
        elif w_stat == "no warmup":
            warm_badge = '<span class="badge badge-neutral">No Warmup</span>'
        else:
            warm_badge = f'<span class="badge badge-danger">{html.escape(w_stat)}</span>'

        # Specific metadata tags based on service name
        if "semantic" in prefix:
            model_tags = (
                '<span class="tag">all-MiniLM-L6-v2</span>'
                '<span class="tag">twitter-roberta-sentiment</span>'
                '<span class="tag">intent-classifier</span>'
            )
            inspect_link = f'<a href="{prefix}/health" class="link-btn">/semantic/health</a>'
        else:
            model_tags = '<span class="tag">Standard Router</span>'
            inspect_link = ""

        service_rows.append(f"""
        <div class="service-card">
          <div class="service-header">
            <div class="service-title">
              <span class="service-prefix">{html.escape(prefix)}</span>
              <span class="service-target">{html.escape(target)}</span>
            </div>
            <div class="service-badges">
              <span class="badge badge-success">Mounted</span>
              {warm_badge}
            </div>
          </div>
          <div class="service-meta">
            <div class="tags-group">
              {model_tags}
            </div>
            <div class="links-group">
              {inspect_link}
            </div>
          </div>
        </div>
        """)

    # Failed projects
    for prefix, err in failed.items():
        service_rows.append(f"""
        <div class="service-card service-failed">
          <div class="service-header">
            <div class="service-title">
              <span class="service-prefix">{html.escape(prefix)}</span>
              <span class="service-error">{html.escape(err)}</span>
            </div>
            <div class="service-badges">
              <span class="badge badge-danger">Failed to Mount</span>
            </div>
          </div>
        </div>
        """)

    services_html = "\n".join(service_rows) if service_rows else '<div class="empty-state">No services registered</div>'

    total_services = len(loaded) + len(failed)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HF Backend Gateway Status</title>
  <style>
    :root {{
      --bg: #0b0f17;
      --card-bg: #121824;
      --card-border: #1e2838;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font-family);
      line-height: 1.5;
      padding: 2.5rem 1.25rem;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .container {{
      width: 100%;
      max-width: 760px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--card-border);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .brand-icon {{
      font-size: 1.5rem;
    }}
    .brand-name {{
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .brand-tag {{
      font-size: 0.75rem;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.25);
      padding: 0.15rem 0.5rem;
      border-radius: 9999px;
      font-weight: 500;
    }}
    .status-banner {{
      background: {beacon_bg};
      border: 1px solid {beacon_border};
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.75rem;
    }}
    .status-headline {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .beacon {{
      color: {beacon_color};
      font-size: 1.1rem;
      animation: pulse 2s infinite ease-in-out;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.6; transform: scale(1.15); }}
    }}
    .status-title {{
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--text-main);
    }}
    .status-updated {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 600px) {{
      .stats-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem 1.25rem;
    }}
    .stat-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      margin-bottom: 0.35rem;
      font-weight: 600;
    }}
    .stat-value {{
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--text-main);
      font-feature-settings: "tnum";
    }}
    .stat-sub {{
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
    }}
    .section-title {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      font-weight: 700;
      margin-bottom: 0.85rem;
    }}
    .services-list {{
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      margin-bottom: 2rem;
    }}
    .service-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1.25rem 1.5rem;
      transition: border-color 0.15s ease;
    }}
    .service-card:hover {{
      border-color: rgba(56, 189, 248, 0.4);
    }}
    .service-failed {{
      border-color: rgba(239, 68, 68, 0.4);
      background: rgba(239, 68, 68, 0.04);
    }}
    .service-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .service-prefix {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-weight: 700;
      font-size: 1.05rem;
      color: var(--accent);
      margin-right: 0.75rem;
    }}
    .service-target {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .service-error {{
      font-size: 0.85rem;
      color: var(--danger);
      display: block;
      margin-top: 0.25rem;
    }}
    .service-badges {{
      display: flex;
      gap: 0.4rem;
    }}
    .badge {{
      font-size: 0.7rem;
      font-weight: 600;
      padding: 0.2rem 0.55rem;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .badge-success {{
      background: rgba(16, 185, 129, 0.15);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .badge-neutral {{
      background: rgba(100, 116, 139, 0.15);
      color: var(--text-muted);
      border: 1px solid rgba(100, 116, 139, 0.3);
    }}
    .badge-danger {{
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    .service-meta {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 0.5rem;
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .tags-group {{
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }}
    .tag {{
      font-size: 0.7rem;
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-muted);
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .link-btn {{
      font-size: 0.75rem;
      color: var(--accent);
      text-decoration: none;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .link-btn:hover {{
      text-decoration: underline;
    }}
    footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 1.5rem;
      border-top: 1px solid var(--card-border);
      font-size: 0.8rem;
      color: var(--text-dim);
      flex-wrap: wrap;
      gap: 0.75rem;
    }}
    .footer-links {{
      display: flex;
      gap: 1rem;
    }}
    .footer-links a {{
      color: var(--text-muted);
      text-decoration: none;
    }}
    .footer-links a:hover {{
      color: var(--text-main);
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <span class="brand-icon">⚡</span>
        <span class="brand-name">HF Backend</span>
        <span class="brand-tag">Gateway</span>
      </div>
      <div>
        <a href="/health" class="link-btn" title="View machine-readable JSON">JSON Endpoint</a>
      </div>
    </header>

    <div class="status-banner">
      <div class="status-headline">
        <span class="beacon">{status_icon}</span>
        <div>
          <div class="status-title">{status_text}</div>
          <div class="status-updated">Pre-warmed memory resident routing</div>
        </div>
      </div>
      <div class="status-updated">
        <span>Docker Space</span>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Warmup Latency</div>
        <div class="stat-value">{warmup_seconds:.2f}s</div>
        <div class="stat-sub">Lifespan sequential pre-warming</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active Services</div>
        <div class="stat-value">{len(loaded)} / {total_services}</div>
        <div class="stat-sub">Isolated router mounts</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">First Inference</div>
        <div class="stat-value">&lt; 100ms</div>
        <div class="stat-sub">Zero cold-start delay</div>
      </div>
    </div>

    <div class="section-title">Registered Services</div>
    <div class="services-list">
      {services_html}
    </div>

    <footer>
      <span>Hugging Face Docker Space &bull; Port 7860</span>
      <div class="footer-links">
        <a href="/health">/health</a>
        <a href="https://github.com/rachit-mangawa/hf-backend" target="_blank" rel="noopener">GitHub</a>
        <a href="/?format=json">Raw JSON</a>
      </div>
    </footer>
  </div>
</body>
</html>
"""
