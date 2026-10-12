# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

OUTPUT = Path('output')
LABOR_TARGET = 30.0

kpis        = pd.read_csv(OUTPUT / 'kpis.csv', header=None, index_col=0).squeeze()
monthly     = pd.read_csv(OUTPUT / 'monthly_trend.csv')
locations   = pd.read_csv(OUTPUT / 'location_scorecard.csv')
markets     = pd.read_csv(OUTPUT / 'market_summary.csv')
dayparts    = pd.read_csv(OUTPUT / 'daypart_analysis.csv')
overstaffed = pd.read_csv(OUTPUT / 'overstaffed.csv')

all_markets = ['All Markets'] + sorted(locations['market'].unique().tolist())

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

CARD = {'borderRadius': '8px', 'padding': '16px', 'backgroundColor': 'white',
        'boxShadow': '0 1px 4px rgba(0,0,0,0.08)', 'marginBottom': '16px'}

app.layout = dbc.Container(fluid=True, style={'backgroundColor': '#f0f2f5', 'minHeight': '100vh'}, children=[

    dbc.Row([dbc.Col([
        html.H2("MeadowTable Grille — Operations & Labor Efficiency",
                style={'color': '#2C5F2E', 'fontWeight': 'bold', 'marginTop': '20px'}),
        html.P("18-Month Business Analytics Dashboard  |  Finance & Operations",
               style={'color': '#666', 'marginBottom': '20px'}),
    ])]),

    dbc.Row([
        dbc.Col([
            html.Label("Market", style={'fontWeight': 'bold', 'fontSize': '13px'}),
            dcc.Dropdown(id='market-filter', options=[{'label': m, 'value': m} for m in all_markets],
                         value='All Markets', clearable=False)
        ], width=3),
        dbc.Col([
            html.Label("Daypart", style={'fontWeight': 'bold', 'fontSize': '13px'}),
            dcc.Dropdown(id='daypart-filter',
                         options=[{'label': 'All Dayparts', 'value': 'All'},
                                  {'label': 'Lunch', 'value': 'Lunch'},
                                  {'label': 'Dinner', 'value': 'Dinner'}],
                         value='All', clearable=False)
        ], width=3),
    ], style={**CARD, 'marginBottom': '20px'}),

    dbc.Row(id='kpi-row'),

    dbc.Row([
        dbc.Col([html.Div(style=CARD, children=[
            html.H6("Monthly Revenue & Labor Cost", style={'color': '#333'}),
            dcc.Graph(id='revenue-trend', style={'height': '280px'})
        ])], width=8),
        dbc.Col([html.Div(style=CARD, children=[
            html.H6("Labor % vs. 30% Target", style={'color': '#333'}),
            dcc.Graph(id='labor-gauge', style={'height': '280px'})
        ])], width=4),
    ]),

    dbc.Row([
        dbc.Col([html.Div(style=CARD, children=[
            html.H6("Labor % by Daypart & Day of Week", style={'color': '#333'}),
            dcc.Graph(id='heatmap', style={'height': '300px'})
        ])], width=6),
        dbc.Col([html.Div(style=CARD, children=[
            html.H6("Top Overstaffing Cost by Location", style={'color': '#C0392B'}),
            dcc.Graph(id='roi-chart', style={'height': '300px'})
        ])], width=6),
    ]),

    dbc.Row([dbc.Col([html.Div(style=CARD, children=[
        html.H6("Location Labor Scorecard", style={'color': '#333'}),
        html.P("Sorted by labor %. Red = >3pp above target. Blue = >3pp below target.",
               style={'fontSize': '12px', 'color': '#888'}),
        html.Div(id='location-table')
    ])])])
])


@app.callback(
    Output('kpi-row',        'children'),
    Output('revenue-trend',  'figure'),
    Output('labor-gauge',    'figure'),
    Output('heatmap',        'figure'),
    Output('roi-chart',      'figure'),
    Output('location-table', 'children'),
    Input('market-filter',   'value'),
    Input('daypart-filter',  'value'),
)
def update(market, daypart):
    locs = locations.copy()
    if market != 'All Markets':
        locs = locs[locs['market'] == market]

    avg_labor  = locs['avg_labor_pct'].mean()
    total_rev  = locs['total_revenue'].sum()
    total_var  = locs['total_variance_cost'].sum()
    rec_annual = float(kpis['recoverable_annual'])
    n_over     = int(float(kpis['overstaffed_locations']))

    def kpi(value, label, color='#2C5F2E'):
        return dbc.Col([html.Div(style={**CARD, 'textAlign': 'center'}, children=[
            html.H3(value, style={'color': color, 'margin': 0, 'fontWeight': 'bold'}),
            html.P(label,  style={'color': '#888', 'margin': 0, 'fontSize': '12px'}),
        ])], width=3)

    lp_color = '#C0392B' if avg_labor > 32 else '#27AE60' if avg_labor < 29 else '#2C5F2E'
    kpi_row = [
        kpi(f"${total_rev/1_000_000:.1f}M",    "Total Revenue (18 mo)"),
        kpi(f"{avg_labor:.1f}%",                "Avg Labor %  (target: 30%)", lp_color),
        kpi(f"${total_var:,.0f}",               "Total Labor Variance Cost",  '#E07000'),
        kpi(f"${rec_annual:,.0f}",              "Est. Annual Recoverable",    '#C0392B'),
    ]

    rev_fig = go.Figure()
    rev_fig.add_trace(go.Bar(x=monthly['year_month'], y=monthly['total_revenue'],
                             name='Revenue', marker_color='#BDE0BF', yaxis='y'))
    rev_fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['total_labor_cost'],
                                 name='Labor Cost', line=dict(color='#C0392B', width=2),
                                 yaxis='y'))
    rev_fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['avg_labor_pct'],
                                 name='Labor %', line=dict(color='#E07000', width=1.5, dash='dot'),
                                 yaxis='y2'))
    rev_fig.add_hline(y=LABOR_TARGET, yref='y2', line_dash='dash',
                      line_color='#333', annotation_text='30% Target', annotation_position='right')
    rev_fig.update_layout(
        margin=dict(l=40, r=60, t=10, b=40),
        yaxis=dict(title='$'),
        yaxis2=dict(title='Labor %', overlaying='y', side='right', range=[25, 38]),
        legend=dict(orientation='h', y=-0.25),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(tickangle=45, tickfont=dict(size=8))
    )

    avg_all = locations['avg_labor_pct'].mean()
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(avg_labor, 1),
        delta={'reference': LABOR_TARGET, 'valueformat': '.1f',
               'increasing': {'color': '#C0392B'}, 'decreasing': {'color': '#27AE60'}},
        gauge={
            'axis': {'range': [20, 40]},
            'bar': {'color': lp_color},
            'steps': [
                {'range': [20, 28], 'color': '#EBF5FB'},
                {'range': [28, 32], 'color': '#D5F5E3'},
                {'range': [32, 40], 'color': '#FADBD8'},
            ],
            'threshold': {'line': {'color': '#333', 'width': 3}, 'value': LABOR_TARGET}
        },
        title={'text': "System Avg Labor %"}
    ))
    gauge_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='white')

    dp_filt = dayparts.copy()
    if daypart != 'All':
        dp_filt = dp_filt[dp_filt['daypart'] == daypart]

    pivot = dp_filt.pivot_table(index='daypart', columns='day_of_week',
                                values='avg_labor_pct', aggfunc='mean')
    dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    pivot = pivot.reindex(columns=[d for d in dow_order if d in pivot.columns])

    heat_fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0,'#D5F5E3'],[0.5,'#FDEBD0'],[1,'#FADBD8']],
        zmid=LABOR_TARGET,
        text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
        texttemplate='%{text}',
        showscale=True,
        colorbar=dict(title='Labor %', thickness=12)
    ))
    heat_fig.update_layout(
        margin=dict(l=60, r=20, t=10, b=40),
        plot_bgcolor='white', paper_bgcolor='white'
    )

    top_over = overstaffed.nlargest(10, 'recoverable_cost_annual')
    roi_fig = go.Figure(go.Bar(
        x=top_over['recoverable_cost_annual'],
        y=top_over['store_name'].str.replace('MeadowTable ', ''),
        orientation='h',
        marker_color='#C0392B',
        text=[f"${v:,.0f}" for v in top_over['recoverable_cost_annual']],
        textposition='outside'
    ))
    roi_fig.update_layout(
        margin=dict(l=120, r=80, t=10, b=40),
        xaxis=dict(title='Annual Recoverable ($)', tickprefix='$'),
        plot_bgcolor='white', paper_bgcolor='white'
    )

    tbl_df = locs[['store_name','market','avg_labor_pct','vs_target',
                   'total_revenue','total_variance_cost','total_overtime_hrs']].copy()
    tbl_df.columns = ['Location','Market','Labor %','vs Target','Revenue','Variance Cost','OT Hours']
    tbl_df['Labor %']       = tbl_df['Labor %'].round(1)
    tbl_df['vs Target']     = tbl_df['vs Target'].round(2)
    tbl_df['Revenue']       = tbl_df['Revenue'].apply(lambda x: f"${x:,.0f}")
    tbl_df['Variance Cost'] = tbl_df['Variance Cost'].apply(lambda x: f"${x:,.0f}")
    tbl_df['OT Hours']      = tbl_df['OT Hours'].round(0)
    tbl_df = tbl_df.sort_values('Labor %', ascending=False)

    table = dash_table.DataTable(
        data=tbl_df.to_dict('records'),
        columns=[{'name': c, 'id': c} for c in tbl_df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'fontSize': '12px', 'padding': '6px', 'textAlign': 'left'},
        style_header={'fontWeight': 'bold', 'backgroundColor': '#f0f0f0'},
        style_data_conditional=[
            {'if': {'filter_query': '{vs Target} > 3'},
             'backgroundColor': '#FADBD8', 'color': '#C0392B'},
            {'if': {'filter_query': '{vs Target} < -3'},
             'backgroundColor': '#EBF5FB', 'color': '#1A5276'},
        ],
        page_size=15, sort_action='native',
    )

    return kpi_row, rev_fig, gauge_fig, heat_fig, roi_fig, table


if __name__ == '__main__':
    print("\n🍽  MeadowTable Ops Dashboard starting...")
    print("   Open: http://localhost:8050\n")
    app.run(debug=True, port=8050)

