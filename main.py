from dash import Dash, html, dcc, dash_table, callback, Output, Input, State, ALL, no_update
import os
import pandas as pd
import dash_bootstrap_components as dbc
from consolidate_events import carregar_eventos
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
from dash import callback_context
import pdfkit
import tempfile
from dash.dcc import Download
from dash.exceptions import PreventUpdate
from functools import lru_cache
from mapa_barragem import layout as layout_mapa_barragem, register_callbacks as register_map_callbacks
from home import layout as layout_home, registrar_callbacks as register_home_callbacks

# Inicializa o app Dash
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

# Configuração dos caminhos dos arquivos
base_path = r'C:\Users\mathe\Desktop\Estágio\Final'
freq_path = os.path.join(base_path, 'freq_consolidado.csv')
data_path = os.path.join(base_path, 'data_consolidado.csv')

# Mapeamento de códigos de estação
STATION_MAPPING = {
    'S-01-1': '20160005',
    'S-06-1': '20160004',
    'S-01-2': '20160008',
    'S-07-1': '20160003',
    'S-09-1': '20160007',
    'S-10-1': '20160006'
}

# Carrega os dados com tratamento de erros
try:
    df_freq_consolidated = pd.read_csv(freq_path)
    print("Dados de frequência carregados. Colunas:", df_freq_consolidated.columns.tolist())
except Exception as error:
    print(f"Erro ao carregar freq_consolidado.csv: {error}")
    df_freq_consolidated = pd.DataFrame()

try:
    df_data_consolidated = pd.read_csv(data_path)
    print("Dados temporais carregados. Colunas:", df_data_consolidated.columns.tolist())
except Exception as error:
    print(f"Erro ao carregar data_consolidado.csv: {error}")
    df_data_consolidated = pd.DataFrame()

# Carrega dados de eventos
try:
    events_path = os.path.join(base_path, "events", "2025", "2025")
    df_events = carregar_eventos(events_path)
    unique_stations = df_events["estacao"].unique()
    unique_events = df_events["evento"].unique()
    print("Estações carregadas:", unique_stations)
    print("Eventos carregados:", unique_events)
except Exception as error:
    print(f"Erro ao carregar eventos: {error}")
    df_events = pd.DataFrame()
    unique_stations = []
    unique_events = []

def classificar_evento(evento, df):
    dados_evento = df[df["evento"] == evento]
    estacoes_acionadas = dados_evento[dados_evento["valor"] > 10]["estacao"].nunique()
    total_estacoes = dados_evento["estacao"].nunique()
    
    if total_estacoes == 0:
        return "Sem dados", 0
    
    proporcao = estacoes_acionadas / total_estacoes
    
    if proporcao < 0.10:
        classificacao = "Ruído"
    elif proporcao <= 0.75:
        classificacao = "Evento Local"
    else:
        classificacao = "Evento Global"
    
    return classificacao, proporcao

@lru_cache(maxsize=None)
def obter_classificacao(evento):
    return classificar_evento(evento, df_events)[0]

def encontrar_picos(serie_frequencia, serie_amplitude, num_picos=5):
    indices_picos = np.argsort(serie_amplitude)[-num_picos:]
    indices_picos_ordenados = indices_picos[np.argsort(serie_frequencia[indices_picos])]
    return [(serie_frequencia[i], serie_amplitude[i]) for i in indices_picos_ordenados]

# Layout da página de relatórios
reports_layout = html.Div([
    html.Div(
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Top", id="button-top"),
                dbc.DropdownMenuItem("Séries de Aceleração", id="button-series"),
                dbc.DropdownMenuItem("Espectros de Frequência", id="button-spectra"),
            ],
            label="Menu",
            nav=True,
            in_navbar=True,
            style={
                "position": "fixed",
                "top": "20px",
                "right": "20px",
                "zIndex": "1000",
            },
        ),
    ),
    
    html.Div(
        dbc.Button(
            "Selecionar Evento",
            id="button-select-event",
            color="primary",
            className="mb-3",
            style={
                "position": "fixed",
                "top": "60px",
                "right": "20px",
                "zIndex": "1000",
            },
        ),
    ),
    
    html.Div(
        dbc.DropdownMenu(
            id="dropdown-events",
            label="Eventos Disponíveis",
            style={
                "position": "fixed",
                "top": "100px",
                "right": "20px",
                "zIndex": "1000",
                "display": "none",
            },
        ),
    ),
    
    html.Div(id='dummy-div', style={'display': 'none'}),
    dcc.Download(id="download-pdf"),
    html.H3('RELATÓRIO DE MONITORAMENTO DA BARRAGEM DAIVÕES', style={"textAlign": "center", "marginTop": "30px"}),

    dbc.Tabs(
        id="station-tabs",
        active_tab=unique_stations[0] if len(unique_stations) > 0 else None,
        children=[dbc.Tab(label=estacao, tab_id=estacao) for estacao in unique_stations]
    ),
    html.Div(id="tab-content", style={"padding": "20px"})
])

# Layout principal do app
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='filters-store'),
    dcc.Store(id='selected-event-store'),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H4("Menu Principal", style={"padding": "10px", "borderBottom": "1px solid #ddd", "marginBottom": "10px"}),
                
                html.Div([
                    html.H6("OPÇÕES PRINCIPAIS", style={"color": "#555", "padding": "5px 10px", "marginTop": "15px"}),
                    dbc.Nav([
                        dbc.NavLink("Início", href="/home", active="exact", style={"padding": "8px 15px"}),
                        dbc.NavLink("Relatórios", href="/reports", active="exact", style={"padding": "8px 15px"}),
                        dbc.NavLink("Mapa da Barragem", href="/dam-map", active="exact", style={"padding": "8px 15px"}),
                    ], vertical=True, pills=True),
                ]),
                
                html.Div([
                    html.H6("OUTRAS OPÇÕES", style={"color": "#555", "padding": "5px 10px", "marginTop": "20px"}),
                    dbc.Nav([
                        dbc.NavLink("Opção 4", href="#", style={"padding": "8px 15px"}),
                        dbc.NavLink("Opção 5", href="#", style={"padding": "8px 15px"}),
                    ], vertical=True, pills=True),
                ]),
                
                html.Div([
                    html.H6("OUTRAS OPÇÕES 2", style={"color": "#555", "padding": "5px 10px", "marginTop": "20px"}),
                    dbc.Nav([
                        dbc.NavLink("Opção 6", href="#", style={"padding": "8px 15px"}),
                        dbc.NavLink("Opção 7", href="#", style={"padding": "8px 15px"}),
                    ], vertical=True, pills=True),
                ]),
            ], style={
                "position": "fixed",
                "width": "16.666%",
                "height": "100vh",
                "overflowY": "auto",
                "backgroundColor": "#f8f9fa",
                "borderRight": "1px solid #dee2e6",
                "padding": "10px",
                "zIndex": "100"
            })
        ], width=2, style={"padding": "0"}),
        
        dbc.Col([
            html.Div(id='page-content')
        ], width=10, style={"marginLeft": "16.666%"})
    ])
])

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page_content(pathname):
    if pathname == "/dam-map":
        return layout_mapa_barragem
    elif pathname == "/reports":
        return reports_layout
    else:
        return layout_home

# Registra os callbacks
register_map_callbacks(app)
register_home_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)