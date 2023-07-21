#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 14:17:57 2023

@author: arjav
"""

from dash import Dash, dcc, html, Output, Input
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from dash import dash_table
import plotly.express as px
import pandas as pd
import base64
import datetime
import io


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

header = None
with open('header.txt', 'r') as h:
    header = h.read()

isochrones = pd.read_table('iso_combined.dat', comment='#',
                           skip_blank_lines=True, delimiter=r'\s+', header=None)
isochrones.columns = header.split()
isochrones['BP-RP'] = isochrones['G_BPmag'] - isochrones['G_RPmag']
isochrones = isochrones[isochrones['Gmag'] <= 21]
isochrones = isochrones[isochrones['BP-RP'] <= 3]


def compute(E_b_v):
    A_v = 3.1 * E_b_v

    # Extinction
    # A_g = 0.83627 * A_v
    A_bp = 1.08337 * A_v
    A_rp = 0.63439 * A_v

    # Color excess/ reddening
    E_bp_rp = A_bp - A_rp
    return E_bp_rp


app = Dash(__name__, external_stylesheets=external_stylesheets,
           suppress_callback_exceptions=True)

server = app.server

app.layout = html.Div([
    html.H1("Isochrone Fitting",
            style={'textAlign': 'center'}),
    # this code section taken from Dash docs https://dash.plotly.com/dash-core-components/upload
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Don't allow multiple files to be uploaded
        multiple=False
    ),
    html.Div(id='output-div'),
    html.Div(id='output-datatable'),
])


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')), delimiter=",")
            df = df.query('label == "Cluster"')
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),
        html.Button(id="submit-button", children="Create Graph"),
        html.Hr(),

        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in df.columns],
            page_size=15
        ),
        dcc.Store(id='stored-data', data=df.to_dict('records')),

        html.Hr(),  # horizontal line
    ])


@app.callback(Output('output-datatable', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              State('upload-data', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [parse_contents(
            list_of_contents, list_of_names, list_of_dates)]
        return children


@app.callback(Output('output-div', 'children'),
              Input('submit-button', 'n_clicks'))
def make_graphs(n):
    if n is not None:
        return html.Div(
            [

                html.Label("Age"),
                dcc.Slider(min=6.6,
                           max=9.8,
                           step=0.1,
                           value=9.0,
                           tooltip={"placement": "bottom",
                                    "always_visible": True},
                           updatemode='drag',
                           persistence=True,
                           persistence_type='session',  # 'memory' or 'local'
                           id="age-slider"
                           ),
                html.Div([
                    html.Label("Distance Modulus"),
                    dcc.Input(
                        id="distance-modulus",
                        type="number",
                        debounce=True,
                        value=10,
                    ),
                    html.Br(),

                    html.Label("Colour Excess E(B-V)"),
                    dcc.Input(
                        id="colour-excess",
                        type="number",
                        debounce=True,
                        value=1,
                    ),
                    html.Br(),
                    html.Label("Metallicity (increment step: 0.05)"),
                    dcc.Input(
                        id="metallicity",
                        type="number",
                        debounce=True,
                        value=0.001,
                        min=0.001,
                        max=0.05,
                    ),

                ]),



                dcc.Graph(id='my-graph')
            ],
            style={"margin": 30}
        )


@app.callback(
    Output('my-graph', 'figure'),
    Input('age-slider', 'value'),
    Input('distance-modulus', 'value'),
    Input('colour-excess', 'value'),
    Input('metallicity', 'value'),
    State('stored-data', 'data')

)
def update_graph(age, distance_modulus, E_b_v, metallicity, data):

    E_bp_rp = compute(E_b_v)
    bool_metallicity = isochrones['Zini'] == metallicity
    bool_age = isochrones['logAge'] == age
    isochrone = isochrones[bool_age & bool_metallicity]

    isochrone['Gmag'] = isochrone['Gmag'] + distance_modulus
    isochrone['BP-RP'] = isochrone['BP-RP'] + E_bp_rp

    data = pd.DataFrame(data)
    fig1 = px.scatter(data,
                      x='bp-rp',
                      y='g',
                      range_y=(max(data['g']), min(data['g'])),
                      color_discrete_sequence=['black'],
                      opacity=0.1,
                      size_max=5
                      )

    fig2 = px.line(isochrone,
                   x='BP-RP',
                   y='Gmag',
                   color_discrete_sequence=['red']
                   )

    fig = go.Figure(data=fig2.data + fig1.data, layout=fig1.layout)

    return fig


if __name__ == "__main__":
    app.run(debug=True)
