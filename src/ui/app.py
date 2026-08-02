# src/ui/app.py
"""Gradio dashboard UI for AI Trading Floor driven by TRADER_CONFIGS & async account calls."""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

import gradio as gr
from .utils import css, js, Color
import pandas as pd
import plotly.express as px
from ..core.models import Account
from ..utils.formatting import fmt_inr
from ..core.database import async_read_log, setup_database
from ..core.market import get_share_price
from ..utils.config import TRADER_CONFIGS, TraderConfig, settings

mapper = {
    "trace": Color.WHITE,
    "agent": Color.CYAN,
    "function": Color.GREEN,
    "generation": Color.YELLOW,
    "response": Color.MAGENTA,
    "account": Color.RED,
}


class TraderUI:
    """UI controller for an individual trader agent."""

    def __init__(self, config: TraderConfig):
        self.config = config
        self.name = config.name
        self.lastname = config.lastname
        self.model_name = config.short_model_name
        self.emoji = config.emoji
        self.color = config.color
        self.account = None

    async def init_account(self):
        """Asynchronously load account model."""
        self.account = await Account.get(self.name)
        return self

    async def reload(self):
        """Asynchronously reload account model."""
        self.account = await Account.get(self.name)

    def get_title(self) -> str:
        return f"""
        <div class="trader-header trader-header-{self.name.lower()}">
            <span class="trader-avatar">{self.emoji}</span>
            <div class="trader-meta">
                <span class="trader-name">{self.name} {self.lastname}</span>
                <span class="trader-model">{self.model_name}</span>
            </div>
        </div>
        """

    def get_portfolio_value_df(self) -> pd.DataFrame:
        if not self.account:
            return pd.DataFrame(columns=["datetime", "value"])
        df = pd.DataFrame(self.account.portfolio_value_time_series, columns=["datetime", "value"])
        if df.empty:
            return df
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df

    def get_portfolio_value_chart(self):
        df = self.get_portfolio_value_df()
        if df.empty:
            fig = px.line(pd.DataFrame({"datetime": [], "value": []}), x="datetime", y="value")
        else:
            fig = px.line(df, x="datetime", y="value")
            fig.update_traces(
                line=dict(color=self.color, width=2.5),
                hovertemplate="₹%{y:,.2f}<extra></extra>"
            )
            
        fig.update_layout(
            height=260,
            margin=dict(l=40, r=20, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            font=dict(color="#8b949e", size=10),
            xaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False, title="", tickfont=dict(color="#8b949e")),
            yaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False, title="", tickfont=dict(color="#8b949e"))
        )
        return fig

    def get_sparkline_chart(self):
        df = self.get_portfolio_value_df()
        if df.empty:
            fig = px.line(pd.DataFrame({"datetime": [], "value": []}), x="datetime", y="value")
        else:
            fig = px.line(df, x="datetime", y="value")
            fig.update_traces(line=dict(color=self.color, width=2.0), hoverinfo="skip")
            
        fig.update_layout(
            height=70,
            margin=dict(l=5, r=5, t=5, b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False, showgrid=False, zeroline=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False),
            showlegend=False
        )
        return fig

    def get_holdings_df(self) -> pd.DataFrame:
        if not self.account:
            return pd.DataFrame(columns=["Symbol", "Quantity", "Price", "Total Value"])
        holdings = self.account.get_holdings()
        if not holdings:
            return pd.DataFrame(columns=["Symbol", "Quantity", "Price", "Total Value"])
        rows = []
        for symbol, qty in holdings.items():
            try:
                price = get_share_price(symbol)
            except Exception:
                price = 0.0
            val = qty * price
            rows.append({
                "Symbol": symbol,
                "Quantity": qty,
                "Price": fmt_inr(price),
                "Total Value": fmt_inr(val)
            })
        return pd.DataFrame(rows)

    def get_transactions_html(self) -> str:
        if not self.account:
            return "<div class='no-tx'>No transactions recorded yet.</div>"
        transactions = self.account.list_transactions()
        if not transactions:
            return "<div class='no-tx'>No transactions recorded yet.</div>"
        
        sorted_tx = sorted(transactions, key=lambda x: x["timestamp"], reverse=True)
        html = "<div class='tx-timeline'>"
        for t in sorted_tx:
            qty = t["quantity"]
            is_buy = qty > 0
            tx_type = "BUY" if is_buy else "SELL"
            badge_class = "tx-badge-buy" if is_buy else "tx-badge-sell"
            card_class = "tx-card-buy" if is_buy else "tx-card-sell"
            display_qty = abs(qty)
            price_formatted = fmt_inr(t["price"])
            total_formatted = fmt_inr(display_qty * float(t["price"]))
            
            html += f"""
            <div class="tx-item {card_class}">
                <div class="tx-row">
                    <span class="tx-badge {badge_class}">{tx_type}</span>
                    <span class="tx-symbol">{t['symbol']}</span>
                    <span class="tx-qty">{display_qty} shares</span>
                    <span class="tx-price">@ {price_formatted}</span>
                    <span class="tx-total">(Total: {total_formatted})</span>
                </div>
                <div class="tx-time">{t['timestamp']}</div>
                <div class="tx-rationale-box" onclick="this.classList.toggle('expanded')">
                    <span class="tx-rationale-label">Rationale:</span> {t['rationale']}
                </div>
            </div>
            """
        html += "</div>"
        return html

    async def get_portfolio_value(self) -> str:
        await self.reload()
        portfolio_value = float(self.account.calculate_portfolio_value() or 0.0)
        pnl = float(self.account.calculate_profit_loss(portfolio_value) or 0.0)
        badge_class = "pv-badge-up" if pnl >= 0 else "pv-badge-down"
        pnl_badge_class = "pnl-up" if pnl >= 0 else "pnl-down"
        sign = "▲" if pnl >= 0 else "▼"
        
        return f"""
        <div class="portfolio-value-badge {badge_class}">
            <div class="portfolio-value-amount">{fmt_inr(portfolio_value)}</div>
            <div class="portfolio-value-pnl {pnl_badge_class}">{sign} {fmt_inr(pnl)}</div>
        </div>
        """

    async def get_logs(self, previous=None) -> str:
        logs = await async_read_log(self.name, last_n=30)
        logs_list = list(logs)
        logs_list.reverse()
        
        response = ""
        for log in logs_list:
            timestamp, typ, message = log
            color = mapper.get(typ, Color.WHITE).value
            response += f"<div class='log-line'><span class='log-time'>{timestamp}</span> : <span class='log-type log-type-{typ.lower()}' style='color:{color};'>[{typ.upper()}]</span> <span class='log-msg'>{message}</span></div>"
            
        html = f"""
        <div class="terminal-container">
            <div class="terminal-header">
                <div class="terminal-buttons">
                    <span class="btn close"></span>
                    <span class="btn minimize"></span>
                    <span class="btn expand"></span>
                </div>
                <div class="terminal-title">{self.name.lower()}_agent@trading-desk:~</div>
            </div>
            <div class="terminal-body">
                {response}
            </div>
        </div>
        """
        if html != previous:
            return html
        return gr.update()

    async def get_overview_card(self) -> str:
        await self.reload()
        portfolio_value = float(self.account.calculate_portfolio_value() or 0.0)
        pnl = float(self.account.calculate_profit_loss(portfolio_value) or 0.0)
        
        pnl_class = "pnl-up" if pnl >= 0 else "pnl-down"
        pnl_badge = f"<span class='overview-pnl-badge {pnl_class}'>{'▲' if pnl >= 0 else '▼'} {fmt_inr(pnl)}</span>"
        
        holdings = self.account.get_holdings()
        holdings_summary = [f"{s} ({q})" for s, q in list(holdings.items())[:3]]
        holdings_text = ", ".join(holdings_summary) if holdings_summary else "No holdings"
        if len(holdings) > 3:
            holdings_text += "..."
            
        return f"""
        <div class="overview-card overview-card-{self.name.lower()}">
            <div class="overview-card-header">
                <div class="overview-card-avatar">{self.emoji}</div>
                <div class="overview-card-meta">
                    <span class="overview-card-name">{self.name} {self.lastname}</span>
                    <span class="overview-card-model">{self.model_name}</span>
                </div>
            </div>
            <div class="overview-card-body">
                <div class="overview-val-label">Portfolio Value</div>
                <div class="overview-val-row">
                    <span class="overview-val-amount">{fmt_inr(portfolio_value)}</span>
                    {pnl_badge}
                </div>
                <div class="overview-holdings">
                    <strong>Holdings:</strong> {holdings_text}
                </div>
            </div>
        </div>
        """


async def get_global_header_html(traders: list[TraderUI]) -> str:
    total_val = 0.0
    total_pnl = 0.0

    for t in traders:
        await t.reload()
        pv = float(t.account.calculate_portfolio_value() or 0.0)
        pnl = float(t.account.calculate_profit_loss(pv) or 0.0)
        total_val += pv
        total_pnl += pnl
        
    pnl_class = "global-pnl-up" if total_pnl >= 0 else "global-pnl-down"
    sign = "▲" if total_pnl >= 0 else "▼"
    
    return f"""
    <div class="global-header">
        <div class="header-logo-section">
            <span class="header-logo">⚡</span>
            <div class="header-titles">
                <h1>AI TRADING DESK</h1>
                <p>Multi-Agent Real-Time Algorithmic Execution</p>
            </div>
        </div>
        
        <div class="header-stats-section">
            <div class="header-stat-box">
                <span class="stat-label">COMBINED DESK VALUE</span>
                <span class="stat-value">{fmt_inr(total_val)}</span>
            </div>
            
            <div class="header-stat-box">
                <span class="stat-label">TOTAL DESK P&L</span>
                <span class="stat-value {pnl_class}">{sign} {fmt_inr(total_pnl)}</span>
            </div>
            
            <div class="header-stat-box">
                <span class="stat-label">PINCHTAB BROWSER ENGINE</span>
                <div class="status-indicator-row">
                    <span class="status-dot pulse" style="background-color: #00e5cc; box-shadow: 0 0 8px #00e5cc;"></span>
                    <span class="status-text" style="color: #00e5cc;">ONLINE (PORT 9867)</span>
                </div>
            </div>
            <div class="header-stat-box">
                <span class="stat-label">DESK STATUS</span>
                <div class="status-indicator-row">
                    <span class="status-dot pulse"></span>
                    <span class="status-text">LIVE RUNNING</span>
                </div>
            </div>
        </div>
    </div>
    """


def get_all_transactions_html(traders: list[TraderUI]) -> str:
    all_txs = []
    for t in traders:
        if t.account:
            txs = t.account.list_transactions()
            for tx in txs:
                tx = tx.copy()
                tx["trader"] = t.name
                all_txs.append(tx)
            
    if not all_txs:
        return "<div class='no-tx'>No transactions recorded yet across the desk.</div>"
        
    sorted_txs = sorted(all_txs, key=lambda x: x["timestamp"], reverse=True)
    html = "<div class='tx-timeline all-desk-timeline'>"
    for t in sorted_txs[:15]:
        qty = t["quantity"]
        is_buy = qty > 0
        tx_type = "BUY" if is_buy else "SELL"
        badge_class = "tx-badge-buy" if is_buy else "tx-badge-sell"
        card_class = "tx-card-buy" if is_buy else "tx-card-sell"
        display_qty = abs(qty)
        price_formatted = fmt_inr(t["price"])
        total_formatted = fmt_inr(display_qty * float(t["price"]))
        
        html += f"""
        <div class="tx-item {card_class}">
            <div class="tx-row">
                <span class="tx-trader-pill">{t['trader'].upper()}</span>
                <span class="tx-badge {badge_class}">{tx_type}</span>
                <span class="tx-symbol">{t['symbol']}</span>
                <span class="tx-qty">{display_qty} shares</span>
                <span class="tx-price">@ {price_formatted}</span>
                <span class="tx-total">(Total: {total_formatted})</span>
            </div>
            <div class="tx-time">{t['timestamp']}</div>
            <div class="tx-rationale-box" onclick="this.classList.toggle('expanded')">
                <span class="tx-rationale-label">Rationale:</span> {t['rationale']}
            </div>
        </div>
        """
    html += "</div>"
    return html


def make_data_refresh_fn(traders: list[TraderUI]):
    async def refresh_data():
        for t in traders:
            await t.reload()
            
        header_html = await get_global_header_html(traders)
        all_tx_html = get_all_transactions_html(traders)
        
        results = [header_html, all_tx_html]
        
        for t in traders:
            results.append(await t.get_overview_card())
            results.append(t.get_sparkline_chart())
            results.append(await t.get_portfolio_value())
            results.append(t.get_portfolio_value_chart())
            results.append(t.get_holdings_df())
            results.append(t.get_transactions_html())
            
        return results
    return refresh_data


def create_ui():
    import asyncio
    traders = [TraderUI(cfg) for cfg in TRADER_CONFIGS]
    
    # Pre-initialize accounts synchronously for initial render
    async def _init_all():
        await setup_database()
        for t in traders:
            await t.init_account()
    asyncio.run(_init_all())
    
    with gr.Blocks(title="AI Trading Floor Terminal") as ui:
        # 1. Global Header Status
        global_header = gr.HTML(value=lambda: asyncio.run(get_global_header_html(traders)))
        
        trader_components = []
        
        with gr.Tabs():
            with gr.TabItem("📊 Desk Overview"):
                with gr.Row():
                    for t in traders:
                        with gr.Column(scale=1, min_width=250):
                            card = gr.HTML(value=asyncio.run(t.get_overview_card()))
                            spark = gr.Plot(value=t.get_sparkline_chart(), show_label=False)
                            
                            t_comp = {
                                "trader": t,
                                "overview_card": card,
                                "sparkline": spark
                            }
                            trader_components.append(t_comp)
                            
                gr.Markdown("### 📜 Real-Time Desk Transactions Feed")
                all_tx_feed = gr.HTML(value=lambda: get_all_transactions_html(traders))
                
            for i, t in enumerate(traders):
                with gr.TabItem(f"{t.emoji} {t.name} Terminal"):
                    with gr.Row():
                        with gr.Column(scale=3, min_width=400):
                            title_html = gr.HTML(value=t.get_title())
                            pv_badge = gr.HTML(value=asyncio.run(t.get_portfolio_value()))
                            chart = gr.Plot(value=t.get_portfolio_value_chart(), show_label=False)
                            holdings = gr.Dataframe(
                                value=t.get_holdings_df(),
                                label="Active Holdings",
                                row_count=(5, "dynamic"),
                                column_count=4,
                                interactive=False
                            )
                            
                        with gr.Column(scale=2, min_width=300):
                            gr.Markdown(f"### 🖥️ {t.name.upper()} Agent Live Console")
                            log = gr.HTML(value=asyncio.run(t.get_logs()))
                            
                            gr.Markdown("### 🕒 Transaction History Timeline")
                            tx_timeline = gr.HTML(value=t.get_transactions_html())
                            
                        trader_components[i].update({
                            "pv_badge": pv_badge,
                            "chart": chart,
                            "holdings": holdings,
                            "tx_timeline": tx_timeline,
                            "log": log
                        })
                        
        log_timer = gr.Timer(value=1.5)
        for t_comp in trader_components:
            t_obj = t_comp["trader"]
            log_comp = t_comp["log"]
            log_timer.tick(
                fn=t_obj.get_logs,
                inputs=[log_comp],
                outputs=[log_comp],
                show_progress="hidden"
            )
            
        data_timer = gr.Timer(value=15.0)
        data_outputs = [global_header, all_tx_feed]
        for t_comp in trader_components:
            data_outputs.extend([
                t_comp["overview_card"],
                t_comp["sparkline"],
                t_comp["pv_badge"],
                t_comp["chart"],
                t_comp["holdings"],
                t_comp["tx_timeline"]
            ])
            
        data_timer.tick(
            fn=make_data_refresh_fn(traders),
            inputs=[],
            outputs=data_outputs,
            show_progress="hidden"
        )
        
    return ui

if __name__ == "__main__":
    ui = create_ui()
    ui.launch(inbrowser=True, css=css, js=js)
