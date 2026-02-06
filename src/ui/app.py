# src/ui/app.py
import gradio as gr
from .utils import css, js, Color
import pandas as pd
from ..services.trading_floor import names, lastnames, short_model_names
import plotly.express as px
from ..core.models import Account
from ..utils.formatting import fmt_inr
from ..core.database import read_log

mapper = {
    "trace": Color.WHITE,
    "agent": Color.CYAN,
    "function": Color.GREEN,
    "generation": Color.YELLOW,
    "response": Color.MAGENTA,
    "account": Color.RED,
}

class TraderUI:
    def __init__(self, name: str, lastname: str, model_name: str):
        self.name = name
        self.lastname = lastname
        self.model_name = model_name
        self.account = Account.get(name)

    def reload(self):
        self.account = Account.get(self.name)

    def get_title(self) -> str:
        return f"<div style='text-align: center;font-size:30px;'>{self.name}<span style='color:#666;font-size:18px;'> ({self.model_name}) - {self.lastname}</span></div>"

    def get_portfolio_value_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self.account.portfolio_value_time_series, columns=["datetime", "value"])
        if df.empty:
            return df
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df

    def get_portfolio_value_chart(self):
        df = self.get_portfolio_value_df()
        if df.empty:
            return px.line(pd.DataFrame({"datetime": [], "value": []}), x="datetime", y="value")
        fig = px.line(df, x="datetime", y="value")
        fig.update_layout(height=300, margin=dict(l=40, r=20, t=20, b=40), paper_bgcolor="#fff")
        fig.update_yaxes(tickformat=",.0f")
        return fig

    def get_holdings_df(self) -> pd.DataFrame:
        holdings = self.account.get_holdings()
        if not holdings:
            return pd.DataFrame(columns=["Symbol", "Quantity"])
        df = pd.DataFrame([{"Symbol": s, "Quantity": q} for s, q in holdings.items()])
        return df

    def get_transactions_df(self) -> pd.DataFrame:
        transactions = self.account.list_transactions()
        if not transactions:
            return pd.DataFrame(columns=["Timestamp", "Symbol", "Quantity", "Price", "Rationale"])
        rows = []
        for t in transactions:
            rows.append(
                {
                    "Timestamp": t["timestamp"],
                    "Symbol": t["symbol"],
                    "Quantity": t["quantity"],
                    "Price": fmt_inr(t["price"]),
                    "Rationale": t["rationale"],
                }
            )
        return pd.DataFrame(rows)

    def get_portfolio_value(self) -> str:
        self.reload()
        portfolio_value = self.account.calculate_portfolio_value() or 0.0
        pnl = self.account.calculate_profit_loss(portfolio_value) or 0.0
        color = "#def7e0" if pnl >= 0 else "#fdecec"
        sign = "▲" if pnl >= 0 else "▼"
        html = f"<div style='text-align:center;background:{color};padding:8px;border-radius:6px;'>"
        html += f"<div style='font-size:20px;font-weight:600'>{fmt_inr(portfolio_value)}</div>"
        html += f"<div style='font-size:14px;color:#333'>{sign} {fmt_inr(pnl)}</div></div>"
        return html

    def get_logs(self, previous=None) -> str:
        logs = read_log(self.name, last_n=13)
        response = ""
        for log in logs:
            timestamp, typ, message = log
            color = mapper.get(typ, Color.WHITE).value
            response += f"<div style='font-size:12px;color:{color};'>{timestamp} : [{typ}] {message}</div>"
        response = f"<div style='height:240px; overflow-y:auto;'>{response}</div>"
        if response != previous:
            return response
        return gr.update()

def create_ui():
    traders = [TraderUI(n, ln, mn) for n, ln, mn in zip(names, lastnames, short_model_names)]
    with gr.Blocks(title="Indian Market Traders", css=css, js=js, theme=gr.themes.Default(primary_hue="teal")) as ui:
        with gr.Row():
            for t in traders:
                with gr.Column():
                    gr.HTML(t.get_title())
                    pv = gr.HTML(t.get_portfolio_value)
                    chart = gr.Plot(t.get_portfolio_value_chart, show_label=False)
                    log = gr.HTML(t.get_logs)
                    holdings = gr.Dataframe(value=t.get_holdings_df, label="Holdings", row_count=(5, "dynamic"), col_count=2)
                    tx = gr.Dataframe(value=t.get_transactions_df, label="Recent Transactions", row_count=(5, "dynamic"), col_count=5)
                    # timers
                    timer = gr.Timer(value=120)
                    timer.tick(fn=t.reload, inputs=[], outputs=[], show_progress="hidden")
                    log_timer = gr.Timer(value=1.0)
                    log_timer.tick(fn=t.get_logs, inputs=[log], outputs=[log], show_progress="hidden")
    return ui

if __name__ == "__main__":
    ui = create_ui()
    ui.launch(inbrowser=True)
