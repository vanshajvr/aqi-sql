import html

import plotly.graph_objects as go

from ..theme import ACCENT, CARD_BG, GRID, POSITIVE, base_layout

GUARDRAIL = 4  # max false alerts per 30 days; same constant as 17_alert_rules.sql
MUTED = "#8b949e"


def _test(df17):
    return df17[df17["split"] == "test"].copy()


def build_tradeoff(df17):
    """Each rule on the test years: false alerts (cost) vs onset recall (value)."""
    d = _test(df17)
    d["code"] = d["rule"].str[0]
    d["label"] = d["rule"].str[2:]
    colors = [POSITIVE if s else (ACCENT if g else MUTED)
              for s, g in zip(d["selected_on_train"], d["within_guardrail"])]

    fig = go.Figure(go.Scatter(
        x=d["false_alerts_per_30d"], y=d["onset_recall"] * 100,
        mode="markers+text", text=d["code"], textposition="top center",
        textfont=dict(color="#f0f6fc", size=12),
        marker=dict(size=[18 if s else 12 for s in d["selected_on_train"]], color=colors,
                    line=dict(color=CARD_BG, width=2)),
        customdata=d[["label", "recall", "precision", "alerts_per_30d"]].values,
        hovertemplate="<b>%{text}: %{customdata[0]}</b>"
                      "<br>First bad days warned: %{y:.0f}%"
                      "<br>False alerts: %{x} per month"
                      "<br>All bad days warned: %{customdata[1]:.0%}"
                      "<br>Alerts that were right: %{customdata[2]:.0%}"
                      "<br>Alerts sent: %{customdata[3]} per month<extra></extra>",
    ))
    fig.add_vrect(x0=0, x1=GUARDRAIL, fillcolor="rgba(63,185,80,0.06)", line_width=0)
    fig.add_vline(x=GUARDRAIL, line=dict(color=MUTED, width=1, dash="dot"),
                  annotation_text=f"false-alarm budget: {GUARDRAIL}/month",
                  annotation_position="top left", annotation_font=dict(color=MUTED, size=11))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title="False alerts per month (cost)", gridcolor=GRID, rangemode="tozero",
                   range=[0, d["false_alerts_per_30d"].max() + 1]),
        yaxis=dict(title="First bad days warned (%)", gridcolor=GRID, range=[-8, 112],
                   ticksuffix="%"),
    )
    return base_layout(fig, height=440, top_margin=40)


def build_table(df17):
    """Test-year scorecard, one row per rule; the selected rule is highlighted."""
    d = _test(df17)
    rows = []
    for r in d.itertuples():
        cls = ' class="selected-rule"' if r.selected_on_train else ""
        rows.append(
            f"<tr{cls}><td>{html.escape(r.rule)}</td>"
            f"<td>{r.onset_recall:.0%}</td><td>{r.recall:.0%}</td><td>{r.precision:.0%}</td>"
            f"<td>{r.alerts_per_30d}</td><td>{r.false_alerts_per_30d}</td></tr>"
        )
    return f"""<div class="table-scroll"><table class="alert-table">
      <thead><tr><th>Rule</th><th>First bad days warned</th><th>All bad days warned</th>
      <th>Alerts right</th><th>Alerts / month</th><th>False / month</th></tr></thead>
      <tbody>{''.join(rows)}</tbody></table></div>"""
