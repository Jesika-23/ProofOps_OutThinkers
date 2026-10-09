"""Service topology inline SVG generator for Mission Control UI.
Renders four services with dependency arrows, live metrics, and status glows.
"""

from typing import Any, Dict


def render_topology_svg(S: Dict[str, Any]) -> str:
    """Generate high-contrast, scalable SVG depicting system architecture and status."""
    services = S.get("services", {})
    api = services.get("orders_api", {})
    worker = services.get("worker", {})
    cache = services.get("cache", {})
    db = services.get("database", {})

    def get_color(status: str) -> str:
        if status == "healthy":
            return "#22C55E"
        if status == "degraded":
            return "#F59E0B"
        return "#EF4444"

    api_col = get_color(api.get("status", "healthy"))
    worker_col = get_color(worker.get("status", "healthy"))
    cache_col = get_color(cache.get("status", "healthy"))
    db_col = get_color(db.get("status", "healthy"))

    api_err = api.get("error_rate", 0.3)
    api_lat = api.get("latency_ms", 120)
    worker_q = worker.get("queue_depth", 4)
    cache_hit = cache.get("hit_rate_pct", 94) if cache.get("reachable", True) else 0
    db_conn = db.get("connections", 18)
    db_int = db.get("integrity", "ok")

    svg = f"""
<svg viewBox="0 0 540 330" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" style="background: #0D131F; border-radius: 12px; border: 1px solid #1E273D;">
  <defs>
    <style>
      .node-box {{ rx: 10px; ry: 10px; transition: stroke 0.6s ease, fill 0.6s ease; }}
      .title-text {{ font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 700; fill: #E6EAF2; }}
      .metric-text {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; fill: #8B96AD; }}
      .val-text {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; fill: #F1F5F9; }}
      .edge {{ stroke: #2A364F; stroke-width: 1.5; stroke-dasharray: 4,4; marker-end: url(#arrow); }}
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 9 5 L 0 9 z" fill="#3E4D6B" />
    </marker>
    <filter id="glow-api" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="{api_col}" flood-opacity="0.35"/>
    </filter>
    <filter id="glow-cache" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="{cache_col}" flood-opacity="0.35"/>
    </filter>
    <filter id="glow-db" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="{db_col}" flood-opacity="0.35"/>
    </filter>
    <filter id="glow-worker" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="{worker_col}" flood-opacity="0.35"/>
    </filter>
  </defs>

  <!-- DEPENDENCY EDGES -->
  <!-- orders_api -> cache -->
  <path d="M 120 100 L 120 180" class="edge" />
  <!-- orders_api -> db -->
  <path d="M 160 100 L 260 180" class="edge" />
  <!-- orders_api -> worker -->
  <path d="M 210 65 L 340 65" class="edge" />
  <!-- worker -> cache -->
  <path d="M 370 100 L 170 200" class="edge" />

  <!-- NODE 1: orders_api -->
  <g transform="translate(40, 30)" filter="url(#glow-api)">
    <rect width="180" height="72" class="node-box" fill="#141B2B" stroke="{api_col}" stroke-width="2"/>
    <circle cx="20" cy="22" r="5" fill="{api_col}"/>
    <text x="32" y="26" class="title-text">orders_api</text>
    <text x="18" y="48" class="metric-text">ERR:</text>
    <text x="50" y="48" class="val-text">{api_err}%</text>
    <text x="96" y="48" class="metric-text">LAT:</text>
    <text x="126" y="48" class="val-text">{api_lat}ms</text>
  </g>

  <!-- NODE 2: worker -->
  <g transform="translate(320, 30)" filter="url(#glow-worker)">
    <rect width="180" height="72" class="node-box" fill="#141B2B" stroke="{worker_col}" stroke-width="2"/>
    <circle cx="20" cy="22" r="5" fill="{worker_col}"/>
    <text x="32" y="26" class="title-text">worker</text>
    <text x="18" y="48" class="metric-text">QUEUE DEPTH:</text>
    <text x="108" y="48" class="val-text">{worker_q}</text>
  </g>

  <!-- NODE 3: cache -->
  <g transform="translate(40, 190)" filter="url(#glow-cache)">
    <rect width="180" height="72" class="node-box" fill="#141B2B" stroke="{cache_col}" stroke-width="2"/>
    <circle cx="20" cy="22" r="5" fill="{cache_col}"/>
    <text x="32" y="26" class="title-text">cache (redis)</text>
    <text x="18" y="48" class="metric-text">STATUS:</text>
    <text x="72" y="48" class="val-text">{'UP' if cache.get('reachable') else 'DOWN'}</text>
    <text x="105" y="48" class="metric-text">HIT:</text>
    <text x="134" y="48" class="val-text">{cache_hit}%</text>
  </g>

  <!-- NODE 4: database -->
  <g transform="translate(320, 190)" filter="url(#glow-db)">
    <rect width="180" height="72" class="node-box" fill="#141B2B" stroke="{db_col}" stroke-width="2"/>
    <circle cx="20" cy="22" r="5" fill="{db_col}"/>
    <text x="32" y="26" class="title-text">database (postgres)</text>
    <text x="18" y="48" class="metric-text">CONNS:</text>
    <text x="66" y="48" class="val-text">{db_conn}/100</text>
    <text x="110" y="48" class="metric-text">INT:</text>
    <text x="138" y="48" class="val-text">{db_int}</text>
  </g>
</svg>
"""
    return svg
