import plotly.express as px
import plotly.graph_objects as go

FONTS = "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif, Apple Color Emoji, Segoe UI Emoji"
COLOR_SEQUENCE = px.colors.qualitative.Safe

BASE_GRAPH_LAYOUT = go.Layout(
    margin=dict(l=50, r=50, t=40, b=30),
    autosize=True,
    font=dict(family=FONTS),
    colorway=COLOR_SEQUENCE,
    title=dict(x=0.5, xanchor="center"),
    legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
)
BASE_GRAPH_FIG = go.Figure(layout=BASE_GRAPH_LAYOUT)
