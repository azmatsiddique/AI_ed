# src/ui/utils.py
from enum import Enum

css = """
/* Dark theme terminal style adjustments for Gradio */
:root {
    --bg-primary: #0b0e14;
    --bg-secondary: #0f131a;
    --border-color: #1f2937;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    
    --warren-color: #3b82f6;
    --george-color: #f59e0b;
    --ray-color: #10b981;
    --cathie-color: #8b5cf6;
    
    --green-up: #4ade80;
    --green-up-bg: rgba(74, 222, 128, 0.1);
    --red-down: #f87171;
    --red-down-bg: rgba(248, 113, 113, 0.1);
}

/* Base Gradio Override */
body, .gradio-container {
    background-color: var(--bg-primary) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    color: var(--text-primary) !important;
}

/* Custom Header Banner */
.global-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}

.header-logo-section {
    display: flex;
    align-items: center;
    gap: 12px;
}

.header-logo {
    font-size: 28px;
    color: #eab308;
}

.header-titles h1 {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin: 0;
    color: #f8fafc;
}

.header-titles p {
    font-size: 11px;
    color: var(--text-secondary);
    margin: 2px 0 0 0;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.header-stats-section {
    display: flex;
    gap: 32px;
}

.header-stat-box {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}

.stat-label {
    font-size: 9px;
    color: var(--text-secondary);
    font-weight: 600;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

.stat-value {
    font-size: 18px;
    font-weight: 700;
    font-family: monospace;
}

.global-pnl-up {
    color: var(--green-up) !important;
}

.global-pnl-down {
    color: var(--red-down) !important;
}

.status-indicator-row {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 27px;
}

.status-dot {
    width: 8px;
    height: 8px;
    background-color: var(--green-up);
    border-radius: 50%;
}

.status-dot.pulse {
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7);
    animation: statusPulse 1.6s infinite cubic-bezier(0.66, 0, 0, 1);
}

.status-text {
    font-size: 11px;
    font-weight: 700;
    color: var(--green-up);
}

@keyframes statusPulse {
    to {
        box-shadow: 0 0 0 8px rgba(74, 222, 128, 0);
    }
}

/* Tab styling overrides */
.tabs {
    border: none !important;
    background-color: transparent !important;
}

.tab-nav {
    border-bottom: 2px solid var(--border-color) !important;
    padding-bottom: 0 !important;
    gap: 8px !important;
}

.tab-nav button {
    border: 1px solid transparent !important;
    border-bottom: none !important;
    border-radius: 8px 8px 0 0 !important;
    background-color: transparent !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    font-size: 13px !important;
    transition: all 0.2s ease !important;
}

.tab-nav button.selected {
    background-color: var(--bg-secondary) !important;
    border-color: var(--border-color) !important;
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--bg-secondary) !important;
    margin-bottom: -2px !important;
}

.tab-nav button:hover:not(.selected) {
    color: var(--text-primary) !important;
    background-color: rgba(255, 255, 255, 0.03) !important;
}

/* Individual agent card layout */
.trader-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid var(--border-color);
}

.trader-header-warren { border-left: 4px solid var(--warren-color); background: rgba(59, 130, 246, 0.05); }
.trader-header-george { border-left: 4px solid var(--george-color); background: rgba(245, 158, 11, 0.05); }
.trader-header-ray { border-left: 4px solid var(--ray-color); background: rgba(16, 185, 129, 0.05); }
.trader-header-cathie { border-left: 4px solid var(--cathie-color); background: rgba(139, 92, 246, 0.05); }

.trader-avatar {
    font-size: 24px;
}

.trader-meta {
    display: flex;
    flex-direction: column;
}

.trader-name {
    font-size: 16px;
    font-weight: 700;
    color: #f8fafc;
}

.trader-model {
    font-size: 11px;
    color: var(--text-secondary);
}

/* Overview Cards styling */
.overview-row {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
}

.overview-card {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.overview-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.overview-card-warren { border-top: 3px solid var(--warren-color); }
.overview-card-george { border-top: 3px solid var(--george-color); }
.overview-card-ray { border-top: 3px solid var(--ray-color); }
.overview-card-cathie { border-top: 3px solid var(--cathie-color); }

.overview-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}

.overview-card-avatar {
    font-size: 20px;
}

.overview-card-meta {
    display: flex;
    flex-direction: column;
}

.overview-card-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
}

.overview-card-model {
    font-size: 10px;
    color: var(--text-secondary);
}

.overview-card-body {
    display: flex;
    flex-direction: column;
}

.overview-val-label {
    font-size: 9px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}

.overview-val-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
}

.overview-val-amount {
    font-size: 20px;
    font-weight: 700;
    font-family: monospace;
    color: #ffffff;
}

.overview-pnl-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
}

.pnl-up {
    color: var(--green-up);
    background-color: var(--green-up-bg);
    border: 1px solid rgba(74, 222, 128, 0.2);
}

.pnl-down {
    color: var(--red-down);
    background-color: var(--red-down-bg);
    border: 1px solid rgba(248, 113, 113, 0.2);
}

.overview-holdings {
    font-size: 11px;
    color: var(--text-secondary);
    border-top: 1px solid #1e293b;
    padding-top: 8px;
    margin-top: 4px;
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
}

/* Portfolio value badge details */
.portfolio-value-badge {
    text-align: center;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    background-color: var(--bg-secondary);
    margin-bottom: 12px;
}

.pv-badge-up {
    border-left: 4px solid var(--green-up);
}

.pv-badge-down {
    border-left: 4px solid var(--red-down);
}

.portfolio-value-amount {
    font-size: 22px;
    font-weight: 800;
    font-family: monospace;
    color: #ffffff;
}

.portfolio-value-pnl {
    font-size: 13px;
    font-weight: 600;
    margin-top: 4px;
    font-family: monospace;
}

/* Monospace console terminal styling */
.terminal-container {
    background-color: #05070a;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    margin-bottom: 16px;
}

.terminal-header {
    background-color: #0f131a;
    border-bottom: 1px solid var(--border-color);
    padding: 6px 12px;
    display: flex;
    align-items: center;
    gap: 16px;
}

.terminal-buttons {
    display: flex;
    gap: 6px;
}

.terminal-buttons .btn {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.terminal-buttons .close { background-color: #ff5f56; }
.terminal-buttons .minimize { background-color: #ffbd2e; }
.terminal-buttons .expand { background-color: #27c93f; }

.terminal-title {
    color: var(--text-secondary);
    font-family: monospace;
    font-size: 11px;
    flex-grow: 1;
    text-align: center;
    margin-right: 48px;
}

.terminal-body {
    height: 240px;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column-reverse;
    font-family: 'Fira Code', 'Courier New', Courier, monospace;
    background-color: #05070a;
}

.log-line {
    font-size: 11px;
    line-height: 1.5;
    margin-bottom: 4px;
    white-space: pre-wrap;
    word-break: break-all;
    border-bottom: 1px solid rgba(255,255,255,0.02);
    padding-bottom: 2px;
    text-align: left;
}

.log-time {
    color: #4b5563;
}

.log-type {
    font-weight: bold;
    padding-right: 4px;
}

/* Timeline Feed CSS */
.tx-timeline {
    max-height: 320px;
    overflow-y: auto;
    padding: 8px;
    border: 1px solid var(--border-color);
    background-color: var(--bg-secondary);
    border-radius: 8px;
}

.all-desk-timeline {
    max-height: 400px;
}

.tx-item {
    border-left: 3px solid #4b5563;
    padding: 8px 12px;
    margin-bottom: 8px;
    background-color: rgba(255, 255, 255, 0.01);
    border-radius: 0 6px 6px 0;
    transition: background-color 0.2s ease;
    text-align: left;
}

.tx-item:hover {
    background-color: rgba(255, 255, 255, 0.03);
}

.tx-card-buy {
    border-left-color: var(--green-up);
    background-color: rgba(74, 222, 128, 0.02);
}

.tx-card-sell {
    border-left-color: var(--red-down);
    background-color: rgba(248, 113, 113, 0.02);
}

.tx-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.tx-trader-pill {
    font-size: 9px;
    font-weight: 800;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
}

.tx-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    color: #000;
}

.tx-badge-buy {
    background-color: var(--green-up);
    color: #0b0e14;
}

.tx-badge-sell {
    background-color: var(--red-down);
    color: #0b0e14;
}

.tx-symbol {
    font-weight: 700;
    color: #f8fafc;
    font-family: monospace;
}

.tx-qty {
    color: var(--text-primary);
    font-size: 12px;
}

.tx-price {
    color: var(--text-secondary);
    font-family: monospace;
    font-size: 12px;
}

.tx-total {
    color: var(--text-primary);
    font-family: monospace;
    font-size: 12px;
    font-weight: 600;
}

.tx-time {
    font-size: 10px;
    color: #4b5563;
    margin-top: 2px;
}

.tx-rationale-box {
    margin-top: 6px;
    padding: 6px 8px;
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    font-size: 11px;
    color: var(--text-secondary);
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    transition: all 0.25s ease;
}

.tx-rationale-box:hover {
    color: var(--text-primary);
    background-color: rgba(0, 0, 0, 0.3);
}

.tx-rationale-box.expanded {
    -webkit-line-clamp: unset;
    display: block;
    color: var(--text-primary);
}

.tx-rationale-label {
    font-weight: 600;
    color: #94a3b8;
}

.no-tx {
    text-align: center;
    color: var(--text-secondary);
    padding: 24px;
    font-size: 12px;
}

/* Spaced holdings table */
.gradio-container table {
    border-collapse: separate !important;
    border-spacing: 0 4px !important;
    background-color: transparent !important;
}

.gradio-container th {
    background-color: #0f131a !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 10px !important;
    letter-spacing: 0.5px !important;
    border-bottom: 2px solid var(--border-color) !important;
    padding: 10px 12px !important;
}

.gradio-container td {
    background-color: rgba(255,255,255,0.01) !important;
    border-top: 1px solid var(--border-color) !important;
    border-bottom: 1px solid var(--border-color) !important;
    padding: 10px 12px !important;
    font-size: 12px !important;
}

.gradio-container tr:hover td {
    background-color: rgba(255,255,255,0.03) !important;
}

/* Hide Gradio default labels on Plots and Tables where redundant */
.gr-block > label {
    font-size: 11px !important;
    color: var(--text-secondary) !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    margin-bottom: 6px !important;
}

footer {
    display: none !important;
}
"""

js = """
() => {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

class Color(Enum):
    RED = "#ff6b6b"
    GREEN = "#4ade80"
    YELLOW = "#fbbf24"
    BLUE = "#60a5fa"
    MAGENTA = "#f472b6"
    CYAN = "#2dd4bf"
    WHITE = "#e2e8f0"
