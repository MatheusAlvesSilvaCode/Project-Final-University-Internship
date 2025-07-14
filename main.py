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
from utils import classificar_evento
from dash.dependencies import Input, Output, State
import plotly.io as pio
import base64
import pdfkit
from dash import ctx

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
    # print("Dados de frequência carregados. Colunas:", df_freq_consolidated.columns.tolist())
except Exception as error:
    print(f"Erro ao carregar freq_consolidado.csv: {error}")
    df_freq_consolidated = pd.DataFrame()

try:
    df_data_consolidated = pd.read_csv(data_path)
    # print("Dados temporais carregados. Colunas:", df_data_consolidated.columns.tolist())
except Exception as error:
    print(f"Erro ao carregar data_consolidado.csv: {error}")
    df_data_consolidated = pd.DataFrame()

# Carrega dados de eventos
try:
    events_path = os.path.join(base_path, "events", "2025", "2025")
    df_events = carregar_eventos(events_path)
    unique_stations = df_events["estacao"].unique()
    unique_events = df_events["evento"].unique()
    # print("Estações carregadas:", unique_stations)
    # print("Eventos carregados:", unique_events)
except Exception as error:
    print(f"Erro ao carregar eventos: {error}")
    df_events = pd.DataFrame()
    unique_stations = []
    unique_events = []

@lru_cache(maxsize=None)
def obter_classificacao(evento):
    return classificar_evento(evento, df_events)[0]

def criar_tabela_eventos(eventos):
    if eventos is None or (hasattr(eventos, "__len__") and len(eventos) == 0):
        return html.Div("Nenhum evento disponível para exibição")
    try:
        df = pd.DataFrame(eventos)
        df['hora'] = pd.to_datetime(df['data_hora']).dt.strftime('%Hh%Mm%Ss')
        df_exploded = df.explode('estacao')
        df_pivot = df_exploded.pivot_table(
            index='evento',
            columns='estacao',
            values='hora',
            aggfunc='first'
        ).reset_index()
        colunas_ordenadas = ['evento'] + [col for col in STATION_MAPPING.keys() if col in df_pivot.columns]
        df_pivot = df_pivot[colunas_ordenadas]
        return dbc.Table(
            [html.Thead(html.Tr([html.Th("Evento")] + [html.Th(col) for col in df_pivot.columns[1:]])),
             html.Tbody([
                html.Tr([html.Td(str(row['evento']))] + [
                    html.Td(str(row[col]) if pd.notna(row[col]) else "") for col in df_pivot.columns[1:]
                ]) for _, row in df_pivot.iterrows()
            ])],
            bordered=True,
            striped=True,
            hover=True,
            responsive=True,
            style={'margin-top': '20px'}
        )
    except Exception as e:
        # print(f"Erro ao criar tabela de eventos: {e}")
        return html.Div("Erro ao exibir eventos", style={"textAlign": "center", "marginTop": "50px"})

# Layout da página de relatórios
layout_relatorios = html.Div([
    html.Div(
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Topo", id="botao-topo"),
                dbc.DropdownMenuItem("Séries de Aceleração", id="botao-series"),
                dbc.DropdownMenuItem("Espectros de Frequência", id="botao-espectros"),
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
    html.Div(id='dummy-div', style={'display': 'none'}),
    dcc.Download(id="download-pdf"),
    dcc.Download(id="download-origem"),
    dcc.Store(id="export-stations-store", storage_type="memory"),
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Exportar Relatório de Evento")),
            dbc.ModalBody([
                html.Div([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Selecione as estações para exportar:", className="card-title", style={"textAlign": "center"}),
                            dbc.Checklist(
                                id="export-stations-checklist",
                                options=[{"label": est, "value": est} for est in unique_stations],
                                value=[],
                                inline=False,
                                style={"marginBottom": "10px"}
                            ),
                            dbc.Checkbox(
                                id="export-all-checkbox",
                                className="mb-2",
                                label="Todas as estações",
                                value=False,
                                style={"marginBottom": "15px"}
                            ),
                            dbc.Checkbox(
                                id="export-origem-checkbox",
                                className="mb-2",
                                label="Exportar Origem dos Dados",
                                value=False,
                                style={"marginBottom": "15px"}
                            ),
                            html.Div([
                                dbc.Button("Exportar", id="confirm-export-btn", color="primary", className="me-2"),
                                dbc.Button("Cancelar", id="cancel-export-btn", color="secondary")
                            ], style={"textAlign": "center", "marginTop": "10px"})
                        ])
                    ], style={"maxWidth": "400px", "margin": "0 auto", "boxShadow": "0 4px 16px rgba(0,0,0,0.15)"})
                ], style={"display": "flex", "justifyContent": "center", "alignItems": "center", "height": "100%"})
            ])
        ],
        id="export-modal",
        is_open=False,
        centered=True,
        backdrop=True,
        keyboard=True,
        style={"zIndex": 2000}
    ),
    html.H3('RELATÓRIO DE MONITORAMENTO DA BARRAGEM DAVÕES', style={"textAlign": "center", "marginTop": "30px"}),
    html.Div(id="titulo-evento-dinamico", style={"textAlign": "center", "color": "black", "marginTop": "10px", "marginBottom": "10px"}),
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Exportar Evento",
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
        ], width=12),
    ]),
    # Abas fixas para todas as estações + Resumo
    dbc.Tabs(
        id="abas-estacoes",
        active_tab="resumo",
        children=[
            dbc.Tab(label="Resumo", tab_id="resumo")
        ] + [dbc.Tab(label=estacao, tab_id=estacao) for estacao in unique_stations]
    ),
    html.Div(id="conteudo-aba", style={"padding": "20px"})
])

# Layout principal do app
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='filters-store'),
    dcc.Store(id='selected-event-store'),
    dcc.Store(id='event-data-store', data=[]),
    dcc.Store(id='armazenar-dados-eventos'),
    
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
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def render_page_content(pathname):
    if pathname == "/dam-map":
        return layout_mapa_barragem
    elif pathname == "/reports":
        return layout_relatorios
    else:
        return layout_home

@app.callback(
    Output('dropdown-events', 'style'),
    Output('dropdown-events', 'children'),
    Input('button-select-event', 'n_clicks'),
    State('dropdown-events', 'style'),
    State('event-data-store', 'data'),
    prevent_initial_call=True
)
def toggle_dropdown_events(n_clicks, current_style, event_data):
    if n_clicks is None:
        raise PreventUpdate
        
    if current_style['display'] == 'none':
        new_style = {**current_style, 'display': 'block'}
        
        if event_data and len(event_data) > 0:
            try:
                eventos_ordenados = sorted(
                    event_data,
                    key=lambda x: pd.to_datetime(x['data_hora']),
                    reverse=True
                )
                dropdown_items = [
                    dbc.DropdownMenuItem(
                        f"{pd.to_datetime(evento['data_hora']).strftime('%d/%m/%Y %H:%M:%S')} ({evento.get('classificacao', 'N/A')})",
                        id={"type": "evento-dropdown", "index": evento['evento']}
                    ) for evento in eventos_ordenados
                ]
            except Exception as e:
                print(f"Erro ao processar eventos: {e}")
                dropdown_items = [dbc.DropdownMenuItem("Erro ao carregar eventos", disabled=True)]
        else:
            dropdown_items = [dbc.DropdownMenuItem("Nenhum evento disponível", disabled=True)]
            
        return new_style, dropdown_items
    else:
        return {**current_style, 'display': 'none'}, no_update

# Função para renderizar o conteúdo do resumo geral do evento

def mostrar_resumo_evento(evento):
    if not evento:
        return html.P('Nenhum evento válido para exibir.')
    evento_id = str(evento['evento']).strip()
    # Filtra todos os dados do evento
    dados_evento = df_events[df_events["evento"].astype(str).str.strip() == evento_id]
    if dados_evento.empty:
        return html.P("Sem dados para este evento.")
    # Datas
    data_hora_evento = evento.get('data_hora', None)
    data_hora_proc = datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    # Estações acima do trigger
    estacoes_trigger = ', '.join(sorted(map(str, set(dados_evento.loc[pd.Series(dados_evento['trigger']).notna(), 'estacao']))))
    # Classificação e razão
    classificacao, racio = classificar_evento(evento_id, df_events)
    # Pico máximo
    peaks_series = pd.Series(dados_evento['peak'])
    idx_pico = peaks_series.idxmax() if not peaks_series.empty else None
    pico_max = dados_evento.loc[idx_pico] if idx_pico is not None else {'estacao':'-','direcao':'-','peak':0,'valor':0}
    # Tabelas de picos e fatores de pico
    tabela_picos = dados_evento.pivot_table(index='estacao', columns='direcao', values='peak', aggfunc='max').reindex(columns=['T','R','V'])
    tabela_fatores = dados_evento.pivot_table(index='estacao', columns='direcao', values='valor', aggfunc='max').reindex(columns=['T','R','V'])
    # Monta layout
    return html.Div([
        #html.H2("Resumo", style={"marginBottom": "20px"}),
        html.P([
            html.B("Data e Hora de Processamento dos Registos: "), f"{data_hora_proc}"
        ]),
        html.P([
            html.B("Estações acima do Trigger: "), f"{estacoes_trigger if estacoes_trigger else '-'}"
        ]),
        html.P([
            html.B("Classificação do Evento: "), html.B(classificacao)
        ]),
        html.P([
            html.B("Rácio de Estações com Fator de Pico Acima de 10 mg/mg: "), html.B(f"{racio:.2f}")
        ]),
        html.P(html.B("Aceleração Máxima Registada:")),
        dbc.Table([
            html.Tbody([
                html.Tr([
                    html.Td(f"Estação: {pico_max['estacao']}", style={"border": "1px solid #000"}),
                    html.Td(f"Direção: {pico_max['direcao']}", style={"border": "1px solid #000"}),
                    html.Td(f"Magnitude: {pico_max['peak']:.3f} mg", style={"border": "1px solid #000"}),
                    html.Td(f"Fator de Pico: {pico_max['valor']:.3f} mg/mg", style={"border": "1px solid #000"})
                ])
            ])
        ], bordered=True, style={"marginBottom": "20px"}),
        dbc.Row([
            dbc.Col([
                html.H5("Picos de Aceleração [mg]", style={"textAlign": "center"}),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Estação")]+[html.Th(d) for d in ['T','R','V']]
                    )),
                    html.Tbody([
                        html.Tr([
                            html.Td(estacao)
                        ] + [
                            html.Td(f"{tabela_picos.loc[estacao, d]:.3f}" if pd.notna(tabela_picos.loc[estacao, d]) else '-')
                            for d in ['T','R','V']
                        ]) for estacao in tabela_picos.index
                    ])
                ], bordered=True, style={"marginBottom": "20px"})
            ], width=6),
            dbc.Col([
                html.H5("Fatores de Pico [mg/mg]", style={"textAlign": "center"}),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Estação")]+[html.Th(d) for d in ['T','R','V']]
                    )),
                    html.Tbody([
                        html.Tr([
                            html.Td(estacao)
                        ] + [
                            html.Td(f"{tabela_fatores.loc[estacao, d]:.3f}" if pd.notna(tabela_fatores.loc[estacao, d]) else '-')
                            for d in ['T','R','V']
                        ]) for estacao in tabela_fatores.index
                    ])
                ], bordered=True, style={"marginBottom": "20px"})
            ], width=6)
        ])
    ])

# Certifique-se de que o callback do conteúdo das abas está com prevent_initial_call=False
@app.callback(
    Output("conteudo-aba", "children"),
    Input("abas-estacoes", "active_tab"),
    Input('selected-event-store', 'data'),
    State('event-data-store', 'data'),
    prevent_initial_call=False  # Garante que o callback roda ao carregar a página
)
def mostrar_relatorio(aba_ativa, evento_selecionado, event_data):
    # print("DEBUG mostrar_relatorio - evento_selecionado:", evento_selecionado)
    # print("DEBUG mostrar_relatorio - event_data:", event_data)
    if not evento_selecionado:
        # Mostra um loading spinner enquanto o evento não está disponível
        return dbc.Spinner(size="lg", color="primary", fullscreen=False, children=[html.Div("Carregando evento...")])
    evento_para_exibir = evento_selecionado if isinstance(evento_selecionado, dict) else None
    if not evento_para_exibir:
        return html.P('Nenhum evento válido para exibir.')
    if aba_ativa == "resumo":
        return mostrar_resumo_evento(evento_para_exibir)
    # Use sempre a aba ativa como estação
    estacao_ativa = aba_ativa
    # Renderiza o dcc.Store e os gráficos apenas para a estação ativa
    return html.Div([
        dcc.Store(id="zoom-range-store", storage_type="memory"),
        dcc.Store(id="freq-zoom-range-store", storage_type="memory"),
        html.H1('Séries de Aceleração', id="series-aceleracao", style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
        mostrar_conteudo_estacao_filtrada(estacao_ativa, evento_para_exibir, only_tables=True),
        dcc.Graph(id="serie-T"),
        dcc.Graph(id="serie-R"),
        dcc.Graph(id="serie-V"),
        mostrar_conteudo_estacao_filtrada(estacao_ativa, evento_para_exibir, only_tables="freq"),
    ])

# --- Callback para sincronizar o zoom dos gráficos de séries de aceleração ---
@app.callback(
    Output("zoom-range-store", "data"),
    Input("serie-T", "relayoutData"),
    Input("serie-R", "relayoutData"),
    Input("serie-V", "relayoutData"),
    prevent_initial_call=True
)
def sync_zoom(relayout_t, relayout_r, relayout_v):
    ctx = callback_context
    # print(f"[DEBUG] sync_zoom called. relayout_t: {relayout_t}, relayout_r: {relayout_r}, relayout_v: {relayout_v}")
    if not ctx.triggered:
        raise PreventUpdate
    relayout = ctx.triggered[0]['value']
    if relayout and "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        # print(f"[DEBUG] sync_zoom returning: x0={relayout['xaxis.range[0]']}, x1={relayout['xaxis.range[1]']}")
        return {"x0": relayout["xaxis.range[0]"], "x1": relayout["xaxis.range[1]"]}
    return None

# --- Callback para sincronizar o zoom dos gráficos de espectro de frequência ---
@app.callback(
    Output("freq-zoom-range-store", "data"),
    Input("freq-T", "relayoutData"),
    Input("freq-R", "relayoutData"),
    Input("freq-V", "relayoutData"),
    prevent_initial_call=True
)
def sync_freq_zoom(relayout_t, relayout_r, relayout_v):
    ctx = callback_context
    # print(f"[DEBUG] sync_freq_zoom called. relayout_t: {relayout_t}, relayout_r: {relayout_r}, relayout_v: {relayout_v}")
    if not ctx.triggered:
        raise PreventUpdate
    relayout = ctx.triggered[0]['value']
    if relayout and "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        # print(f"[DEBUG] sync_freq_zoom returning: x0={relayout['xaxis.range[0]']}, x1={relayout['xaxis.range[1]']}")
        return {"x0": relayout["xaxis.range[0]"], "x1": relayout["xaxis.range[1]"]}
    return None

# Ajuste em mostrar_conteudo_estacao_filtrada: adicionar parâmetro only_tables=False
# Se only_tables=True, retorna apenas as tabelas e não os gráficos (para evitar gráficos duplicados)
def mostrar_conteudo_estacao_filtrada(estacao_selecionada, evento, only_tables=False):
    # print("DEBUG evento recebido:", evento)
    # print("DEBUG estacao_selecionada:", estacao_selecionada)
    # print("DEBUG df_events['evento'].unique():", df_events['evento'].unique())
    # print("DEBUG df_events['estacao'].unique():", df_events['estacao'].unique())
    # print('DEBUG evento_id:', evento_id)
    # print('DEBUG estacao (após ajuste):', estacao)
    # print('DEBUG filtro:', (df_events["estacao"].astype(str).str.strip() == estacao))
    # print('DEBUG filtro evento:', (df_events["evento"].astype(str).str.strip() == evento_id))
    # print(f"DEBUG convertendo código {estacao} para nome {estacao_nome[0]}")
    if estacao_selecionada is None or evento is None:
        return html.P("Nenhuma estação selecionada.")
    evento_id = str(evento['evento']).strip()
    estacao = str(estacao_selecionada).strip()
    if estacao in STATION_MAPPING.values():
        estacao_nome = [k for k, v in STATION_MAPPING.items() if v == estacao]
        if estacao_nome:
            # print(f"DEBUG convertendo código {estacao} para nome {estacao_nome[0]}")
            estacao = estacao_nome[0]
    # print('DEBUG evento_id:', evento_id)
    # print('DEBUG estacao (após ajuste):', estacao)
    # print('DEBUG filtro:', (df_events["estacao"].astype(str).str.strip() == estacao))
    # print('DEBUG filtro evento:', (df_events["evento"].astype(str).str.strip() == evento_id))
    dados_estacao = df_events[
        (df_events["estacao"].astype(str).str.strip() == estacao) &
        (df_events["evento"].astype(str).str.strip() == evento_id)
    ].copy()
    if dados_estacao.empty:
        return html.P("Sem dados para esta estação.")
    trigger_col = dados_estacao["trigger"]
    evento_col = dados_estacao["evento"]
    if isinstance(trigger_col, pd.Series):
        trigger = trigger_col.iloc[0] if not trigger_col.empty else ""
    else:
        trigger = trigger_col[0] if len(trigger_col) > 0 else ""
    if isinstance(evento_col, pd.Series):
        evento_atual = evento_col.iloc[0] if not evento_col.empty else ""
    else:
        evento_atual = evento_col[0] if len(evento_col) > 0 else ""
    classificacao, racio = classificar_evento(evento_atual, df_events)
    estacoes_ativas = pd.Series(df_events[df_events["evento"] == evento_atual]["estacao"]).unique()
    estacoes_com_evento = pd.Series(df_events[(df_events["evento"] == evento_atual) & (df_events["valor"] > 10)]["estacao"]).unique()
    peaks_series = pd.Series(dados_estacao["peak"])
    if not peaks_series.empty:
        idx_pico = peaks_series.idxmax()
        pico_maximo = dados_estacao.loc[idx_pico]
    else:
        pico_maximo = {"estacao": "", "direcao": "", "peak": 0, "valor": 0}
    aceleracao_maxima = {
        "estacao": pico_maximo["estacao"],
        "direcao": pico_maximo["direcao"],
        "magnitude": f"{pico_maximo['peak']:.3f}".replace(".", ",") + " mg",
        "fator_pico": f"{pico_maximo['valor']:.3f}".replace(".", ",") + " mg/mg"
    }
    dados_agrupados = dados_estacao.groupby("direcao").agg({"peak": "max", "valor": "max"}).reindex(["T", "R", "V"])
    
    # Adicionar data/hora do evento em destaque
    data_hora_evento = evento.get('data_hora', None)
    if data_hora_evento:
        try:
            data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
        except Exception:
            data_hora_formatada = str(data_hora_evento)
    else:
        data_hora_formatada = 'Data/hora não disponível'
    
    # Gráficos de séries temporais
    if not df_data_consolidated.empty:
        codigo_estacao = STATION_MAPPING.get(estacao_selecionada, '')
        if codigo_estacao:
            df_data_consolidated['estacao'] = df_data_consolidated['estacao'].astype(str).str.strip()
            df_data_consolidated['evento'] = df_data_consolidated['evento'].astype(str).str.strip()
            series_filtradas = df_data_consolidated[
                (df_data_consolidated["estacao"] == codigo_estacao) & 
                (df_data_consolidated["evento"] == str(evento_id).strip())
            ]
            
            if not series_filtradas.empty:
                y_min = min(series_filtradas["T"].min(), series_filtradas["R"].min(), series_filtradas["V"].min()) * 1.1
                y_max = max(series_filtradas["T"].max(), series_filtradas["R"].max(), series_filtradas["V"].max()) * 1.1
                def criar_grafico_series(direcao):
                    figura = go.Figure()
                    figura.add_trace(go.Scatter(
                        x=series_filtradas["Time"],
                        y=series_filtradas[direcao],
                        mode='lines',
                        line=dict(color='black', width=1),
                        name=direcao
                    ))
                    figura.update_layout(
                        title=f"Série Temporal - Direção {direcao} (Evento: {data_hora_formatada})",
                        xaxis_title="Tempo (s)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min, y_max])
                    )
                    return dcc.Graph(
                        id=f"serie-{direcao}",
                        figure=figura,
                        style={'margin-bottom': '20px'}
                    )
                graficos_series = html.Div([
                    criar_grafico_series("T"),
                    criar_grafico_series("R"),
                    criar_grafico_series("V")
                ])
            else:
                graficos_series = html.Div([
                    html.P("Dados temporais não encontrados para:"),
                    html.P(f"Estação: {estacao_selecionada} (Código: {codigo_estacao})"),
                    html.P(f"Evento: {evento_id}")
                ])
        else:
            graficos_series = html.P(f"Não foi encontrado mapeamento para a estação {estacao_selecionada}")
    else:
        graficos_series = html.P("Dados temporais não carregados.")
    
    # Gráficos de espectros de frequência
    if not df_freq_consolidated.empty:
        codigo_estacao = STATION_MAPPING.get(estacao_selecionada, '')
        if codigo_estacao:
            df_freq_consolidated['estacao'] = df_freq_consolidated['estacao'].astype(str).str.strip()
            df_freq_consolidated['evento'] = df_freq_consolidated['evento'].astype(str).str.strip()
            freq_filtradas = df_freq_consolidated[
                (df_freq_consolidated["estacao"] == codigo_estacao) & 
                (df_freq_consolidated["evento"] == str(evento_id).strip())
            ]
            
            if not freq_filtradas.empty:
                y_min_freq = 0
                y_max_freq = max(freq_filtradas["T"].max(), freq_filtradas["R"].max(), freq_filtradas["V"].max()) * 1.1
                
                def criar_grafico_freq(direcao):
                    figura = go.Figure()
                    x_freq = pd.Series(freq_filtradas["Freq."]).to_numpy()
                    y_amp = pd.Series(freq_filtradas[direcao]).to_numpy()
                    figura.add_trace(go.Scatter(
                        x=x_freq,
                        y=y_amp,
                        mode='lines',
                        line=dict(color='black', width=1),
                        name=direcao
                    ))
                    # Adiciona bolinhas vermelhas nos 5 maiores picos
                    try:
                        picos_indices = np.argsort(y_amp)[-5:]
                        picos_indices_ordenados = picos_indices[np.argsort(x_freq[picos_indices])]
                        figura.add_trace(go.Scatter(
                            x=x_freq[picos_indices_ordenados],
                            y=y_amp[picos_indices_ordenados],
                            mode='markers',
                            marker=dict(color='red', size=10),
                            name='Picos'
                        ))
                    except Exception as e:
                        # print(f"Erro ao marcar picos no gráfico de {direcao}: {e}")
                        pass
                    figura.update_layout(
                        title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {data_hora_formatada})",
                        xaxis_title="Frequência (Hz)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min_freq, y_max_freq])
                    )
                    return dcc.Graph(id=f"freq-{direcao}", figure=figura, style={'margin-bottom': '20px'})
                
                tabela_maximos = []
                for direcao in ['T', 'R', 'V']:
                    picos = []
                    try:
                        serie_frequencia = pd.Series(freq_filtradas["Freq."]).to_numpy()
                        serie_amplitude = pd.Series(freq_filtradas[direcao]).to_numpy()
                        picos_indices = np.argsort(serie_amplitude)[-5:]
                        picos_indices_ordenados = picos_indices[np.argsort(serie_frequencia[picos_indices])]
                        picos = [(serie_frequencia[i], serie_amplitude[i]) for i in picos_indices_ordenados]
                    except Exception:
                        pass
                    
                    frequencias = [f"{freq:.3f}".replace(".", ",") for freq, _ in picos]
                    tabela_maximos.append({
                        'Direção': direcao,
                        '1': frequencias[0] if len(frequencias) > 0 else '-',
                        '2': frequencias[1] if len(frequencias) > 1 else '-',
                        '3': frequencias[2] if len(frequencias) > 2 else '-',
                        '4': frequencias[3] if len(frequencias) > 3 else '-',
                        '5': frequencias[4] if len(frequencias) > 4 else '-'
                    })
                
                df_tabela_maximos = pd.DataFrame(tabela_maximos)
                
                graficos_freq = html.Div([
                    html.H5("Máximos de Frequência da Estação", style={"textAlign": "center", "marginTop": "20px"}),
                    dbc.Table([
                        html.Thead(html.Tr([html.Th(col) for col in df_tabela_maximos.columns])),
                        html.Tbody([
                            html.Tr([
                                html.Td(str(row[col])) for col in df_tabela_maximos.columns
                            ]) for _, row in df_tabela_maximos.iterrows()
                        ])
                    ],
                    striped=True,
                    bordered=True,
                    hover=True,
                    style={
                        'width': '80%',
                        'margin-left': 'auto',
                        'margin-right': 'auto',
                        'margin-bottom': '30px'
                    }),
                    dcc.Graph(id="freq-T"),
                    dcc.Graph(id="freq-R"),
                    dcc.Graph(id="freq-V")
                ])
            else:
                graficos_freq = html.Div([
                    html.P("Dados de frequência não encontrados para:"),
                    html.P(f"Estação: {estacao_selecionada} (Código: {codigo_estacao})"),
                    html.P(f"Evento: {evento_id}")
                ])
        else:
            graficos_freq = html.P(f"Não foi encontrado mapeamento para a estação {estacao_selecionada}")
    else:
        graficos_freq = html.P("Dados de frequência não carregados.")
    
    if only_tables == True:
        # Retorna apenas as tabelas e informações de aceleração máxima e picos
        return html.Div([
            html.H5("Aceleração Máxima:", style={"fontWeight": "bold", "marginTop": "15px"}),
            dbc.Table([
                html.Tbody([
                    html.Tr([html.Td("Direção:"), html.Td(aceleracao_maxima['direcao'])]),
                    html.Tr([html.Td("Magnitude:"), html.Td(aceleracao_maxima['magnitude'])]),
                    html.Tr([html.Td("Fator de Pico:"), html.Td(aceleracao_maxima['fator_pico'])])
                ])
            ], style={"marginBottom": "20px"}),
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5("Picos de Aceleração [mg]", style={"textAlign": "center"}),
                    dbc.Table([
                        html.Thead(html.Tr([html.Th("Direção"), html.Th("Valor")])),
                        html.Tbody([
                            html.Tr([html.Td(d), html.Td(f"{dados_agrupados.loc[d, 'peak']:.3f}".replace(".", ","))])
                            for d in dados_agrupados.index
                        ])
                    ], style={"width": "300px", "margin": "0 auto"})
                ]), width=6),
                dbc.Col(html.Div([
                    html.H5("Fatores de Pico [mg/mg]", style={"textAlign": "center"}),
                    dbc.Table([
                        html.Thead(html.Tr([html.Th("Direção"), html.Th("Valor")])),
                        html.Tbody([
                            html.Tr([html.Td(d), html.Td(f"{dados_agrupados.loc[d, 'valor']:.3f}".replace(".", ","))])
                            for d in dados_agrupados.index
                        ])
                    ], style={"width": "300px", "margin": "0 auto"})
                ]), width=6)
            ], justify="center"),
        ])
    elif only_tables == "freq":
        # Retorna apenas o conteúdo de espectros de frequência
        return html.Div([
            html.H1('Espectros de Frequência das Séries de Aceleração', id="espectros-frequencia", 
                   style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
            graficos_freq
        ])
    return html.Div([
        # Removido: html.H1('Séries de Aceleração', ...),
        html.H5("Aceleração Máxima:", style={"fontWeight": "bold", "marginTop": "15px"}),
        dbc.Table([
            html.Tbody([
                html.Tr([html.Td("Direção:"), html.Td(aceleracao_maxima['direcao'])]),
                html.Tr([html.Td("Magnitude:"), html.Td(aceleracao_maxima['magnitude'])]),
                html.Tr([html.Td("Fator de Pico:"), html.Td(aceleracao_maxima['fator_pico'])])
            ])
        ], style={"marginBottom": "20px"}),
        
        dbc.Row([
            dbc.Col(html.Div([
                html.H5("Picos de Aceleração [mg]", style={"textAlign": "center"}),
                dbc.Table([
                    html.Thead(html.Tr([html.Th("Direção"), html.Th("Valor")])),
                    html.Tbody([
                        html.Tr([html.Td(d), html.Td(f"{dados_agrupados.loc[d, 'peak']:.3f}".replace(".", ","))])
                        for d in dados_agrupados.index
                    ])
                ], style={"width": "300px", "margin": "0 auto"})
            ]), width=6),
            
            dbc.Col(html.Div([
                html.H5("Fatores de Pico [mg/mg]", style={"textAlign": "center"}),
                dbc.Table([
                    html.Thead(html.Tr([html.Th("Direção"), html.Th("Valor")])),
                    html.Tbody([
                        html.Tr([html.Td(d), html.Td(f"{dados_agrupados.loc[d, 'valor']:.3f}".replace(".", ","))])
                        for d in dados_agrupados.index
                    ])
                ], style={"width": "300px", "margin": "0 auto"})
            ]), width=6)
        ], justify="center"),
        
        html.H1('Espectros de Frequência das Séries de Aceleração', id="espectros-frequencia", 
               style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
        graficos_freq
    ])

# --- Callback para renderizar o conteúdo das abas (mantendo layout original, sem outputs duplicados) ---
# REMOVIDO: Callback duplicado para Output("conteudo-aba", "children")

# --- Callback único para atualizar e sincronizar os gráficos de séries de aceleração ---
@app.callback(
    Output("serie-T", "figure"),
    Output("serie-R", "figure"),
    Output("serie-V", "figure"),
    Input("abas-estacoes", "active_tab"),
    Input('selected-event-store', 'data'),
    Input("zoom-range-store", "data"),
    prevent_initial_call=False
)
def update_and_sync_series_figures(aba_ativa, evento_selecionado, zoom_data):
    import plotly.graph_objects as go
    if not evento_selecionado or aba_ativa == "resumo":
        return go.Figure(), go.Figure(), go.Figure()
    evento_id = str(evento_selecionado['evento']).strip()
    estacao_selecionada = aba_ativa
    codigo_estacao = STATION_MAPPING.get(estacao_selecionada, '')
    # Obter data/hora formatada do evento
    data_hora_evento = evento_selecionado.get('data_hora', None)
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    if not codigo_estacao or df_data_consolidated.empty:
        # print("[DEBUG] codigo_estacao não encontrado ou df_data_consolidated vazio.")
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="Sem dados para esta estação/evento", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return fig_empty, fig_empty, fig_empty
    df_data_consolidated['estacao'] = df_data_consolidated['estacao'].astype(str).str.strip()
    df_data_consolidated['evento'] = df_data_consolidated['evento'].astype(str).str.strip()
    series_filtradas = df_data_consolidated[
        (df_data_consolidated["estacao"] == codigo_estacao) & 
        (df_data_consolidated["evento"] == str(evento_id).strip())
    ]
    # print(f"[DEBUG] series_filtradas.shape: {series_filtradas.shape}")
    # print(f"[DEBUG] series_filtradas.head():\n{series_filtradas.head()}")
    if series_filtradas.empty:
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="Sem dados para esta estação/evento", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return fig_empty, fig_empty, fig_empty
    # Ajuste do range do eixo Y para garantir visualização adequada
    y_min = min(series_filtradas["T"].min(), series_filtradas["R"].min(), series_filtradas["V"].min())
    y_max = max(series_filtradas["T"].max(), series_filtradas["R"].max(), series_filtradas["V"].max())
    delta = (y_max - y_min) * 0.1 if y_max != y_min else 1
    y_min -= delta
    y_max += delta
    def make_fig(direcao):
        fig = go.Figure()
        # Garante que Time é float e ordenado
        x = pd.to_numeric(series_filtradas["Time"], errors="coerce")
        y = series_filtradas[direcao]
        # print(f"[DEBUG] Time min: {x.min()}, max: {x.max()}, dtype: {x.dtype}")
        # print(f"[DEBUG] {direcao} min: {y.min()}, max: {y.max()}, dtype: {y.dtype}")
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            line=dict(color='black', width=1),
            name=direcao
        ))
        fig.update_layout(
            title=f"Série Temporal - Direção {direcao} (Evento: {data_hora_formatada})",
            xaxis_title="Tempo (s)",
            yaxis_title="Aceleração (mg)",
            margin=dict(l=40, r=40, t=40, b=40),
            height=300,
            plot_bgcolor='white',
            yaxis=dict(range=[y_min, y_max]),
            xaxis=dict(range=[x.min(), x.max()])
        )
        return fig
    figs = [make_fig("T"), make_fig("R"), make_fig("V")]
    # Aplica o zoom sincronizado se houver
    if zoom_data:
        x0, x1 = zoom_data["x0"], zoom_data["x1"]
        for fig in figs:
            fig.update_xaxes(range=[x0, x1])
    elif zoom_data is None:
        for fig in figs:
            fig.update_xaxes(range=None)
    return figs[0], figs[1], figs[2]

# --- Callback para atualizar e sincronizar os gráficos de espectro de frequência ---
@app.callback(
    Output("freq-T", "figure"),
    Output("freq-R", "figure"),
    Output("freq-V", "figure"),
    Input("abas-estacoes", "active_tab"),
    Input('selected-event-store', 'data'),
    Input("freq-zoom-range-store", "data"),
    prevent_initial_call=False
)
def update_and_sync_freq_figures(aba_ativa, evento_selecionado, zoom_data):
    import plotly.graph_objects as go
    if not evento_selecionado or aba_ativa == "resumo":
        return go.Figure(), go.Figure(), go.Figure()
    evento_id = str(evento_selecionado['evento']).strip()
    estacao_selecionada = aba_ativa
    codigo_estacao = STATION_MAPPING.get(estacao_selecionada, '')
    # Obter data/hora formatada do evento
    data_hora_evento = evento_selecionado.get('data_hora', None)
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    if not codigo_estacao or df_freq_consolidated.empty:
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="Sem dados para esta estação/evento", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return fig_empty, fig_empty, fig_empty
    df_freq_consolidated['estacao'] = df_freq_consolidated['estacao'].astype(str).str.strip()
    df_freq_consolidated['evento'] = df_freq_consolidated['evento'].astype(str).str.strip()
    freq_filtradas = df_freq_consolidated[
        (df_freq_consolidated["estacao"] == codigo_estacao) & 
        (df_freq_consolidated["evento"] == str(evento_id).strip())
    ]
    if freq_filtradas.empty:
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="Sem dados para esta estação/evento", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return fig_empty, fig_empty, fig_empty
    y_min_freq = 0
    y_max_freq = max(freq_filtradas["T"].max(), freq_filtradas["R"].max(), freq_filtradas["V"].max()) * 1.1
    def make_freq_fig(direcao):
        x_freq = pd.Series(freq_filtradas["Freq."]).to_numpy()
        y_amp = pd.Series(freq_filtradas[direcao]).to_numpy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_freq,
            y=y_amp,
            mode='lines',
            line=dict(color='black', width=1),
            name=direcao
        ))
        # Adiciona bolinhas vermelhas nos 5 maiores picos
        try:
            picos_indices = np.argsort(y_amp)[-5:]
            picos_indices_ordenados = picos_indices[np.argsort(x_freq[picos_indices])]
            fig.add_trace(go.Scatter(
                x=x_freq[picos_indices_ordenados],
                y=y_amp[picos_indices_ordenados],
                mode='markers',
                marker=dict(color='red', size=10),
                name='Picos'
            ))
        except Exception as e:
            # print(f"Erro ao marcar picos no gráfico de {direcao}: {e}")
            pass
        fig.update_layout(
            title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {data_hora_formatada})",
            xaxis_title="Frequência (Hz)",
            yaxis_title="Aceleração (mg)",
            margin=dict(l=40, r=40, t=40, b=40),
            height=300,
            plot_bgcolor='white',
            yaxis=dict(range=[y_min_freq, y_max_freq])
        )
        return fig
    figs = [make_freq_fig("T"), make_freq_fig("R"), make_freq_fig("V")]
    # Aplica o zoom sincronizado se houver
    if zoom_data:
        x0, x1 = zoom_data["x0"], zoom_data["x1"]
        for fig in figs:
            fig.update_xaxes(range=[x0, x1])
    elif zoom_data is None:
        for fig in figs:
            fig.update_xaxes(range=None)
    return figs[0], figs[1], figs[2]

@app.callback(
    Output('url', 'pathname'),
    Input('selected-event-store', 'data'),
    prevent_initial_call=True
)
def redirecionar_para_reports(evento_selecionado):
    if evento_selecionado:
        return '/reports'
    raise PreventUpdate

# Registra os callbacks
register_map_callbacks(app)
register_home_callbacks(app)

# Novo callback para atualizar o título do evento dinamicamente
@app.callback(
    Output('titulo-evento-dinamico', 'children'),
    Input('selected-event-store', 'data'),
    prevent_initial_call=False
)
def atualizar_titulo_evento(evento):
    if not evento:
        return ""
    data_hora_evento = evento.get('data_hora', None)
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    return html.H4(f"Evento: {data_hora_formatada}", style={"color": "black", "margin": "0"})

# --- Callbacks para controle do modal de exportação ---

@app.callback(
    Output('export-modal', 'is_open'),
    Input('button-select-event', 'n_clicks'),
    Input('cancel-export-btn', 'n_clicks'),
    Input('confirm-export-btn', 'n_clicks'),
    State('export-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_export_modal(btn_export, btn_cancel, btn_confirm, is_open):
    triggered = ctx.triggered_id
    if triggered == 'button-select-event':
        return True
    elif triggered == 'cancel-export-btn' or triggered == 'confirm-export-btn':
        return False
    return is_open

# --- Callback único para sincronizar checkboxes e armazenar seleção ---
@app.callback(
    Output('export-stations-checklist', 'value'),
    Output('export-all-checkbox', 'value'),
    Output('export-stations-store', 'data'),
    Input('export-stations-checklist', 'value'),
    Input('export-all-checkbox', 'value'),
    Input('confirm-export-btn', 'n_clicks'),
    State('export-stations-checklist', 'options'),
    prevent_initial_call=True
)
def sync_and_store_checklist(selected, all_selected, n_export, options):
    ctx_id = ctx.triggered_id
    all_values = [opt['value'] for opt in options]
    # Se clicou no botão Exportar
    if ctx_id == 'confirm-export-btn':
        if all_selected or not selected:
            return all_values, True, all_values
        return selected, set(selected) == set(all_values), selected
    # Se clicou no checkbox 'Todas'
    elif ctx_id == 'export-all-checkbox':
        if all_selected:
            return all_values, True, None  # None = não exporta ainda
        else:
            return [], False, None
    # Se clicou em algum checklist individual
    else:
        if set(selected) == set(all_values):
            return selected, True, None
        else:
            return selected, False, None

# --- Ajustar callback de exportação para usar as estações selecionadas e exportar TXT se solicitado ---
@app.callback(
    Output('download-pdf', 'data'),
    Output('download-origem', 'data'),
    Input('export-stations-store', 'data'),
    State('selected-event-store', 'data'),
    State('zoom-range-store', 'data'),
    State('freq-zoom-range-store', 'data'),
    State('export-origem-checkbox', 'value'),
    prevent_initial_call=True
)
def exportar_relatorio_pdf(selected_stations, evento, zoom_data, freq_zoom_data, export_origem):
    if not selected_stations or not evento:
        raise PreventUpdate
    evento_id = str(evento['evento']).strip()
    # Definir data_hora_formatada aqui
    data_hora_evento = evento.get('data_hora', None)
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    imagens_series = {}
    imagens_freq = {}
    for estacao_nome, codigo_estacao in STATION_MAPPING.items():
        if estacao_nome not in selected_stations:
            continue
        # Séries de aceleração
        if not df_data_consolidated.empty:
            df_data_consolidated['estacao'] = df_data_consolidated['estacao'].astype(str).str.strip()
            df_data_consolidated['evento'] = df_data_consolidated['evento'].astype(str).str.strip()
            series_filtradas = df_data_consolidated[
                (df_data_consolidated["estacao"] == codigo_estacao) &
                (df_data_consolidated["evento"] == evento_id)
            ]
            if not series_filtradas.empty:
                y_min = min(series_filtradas["T"].min(), series_filtradas["R"].min(), series_filtradas["V"].min())
                y_max = max(series_filtradas["T"].max(), series_filtradas["R"].max(), series_filtradas["V"].max())
                delta = (y_max - y_min) * 0.1 if y_max != y_min else 1
                y_min -= delta
                y_max += delta
                for direcao in ["T", "R", "V"]:
                    fig = go.Figure()
                    x = pd.to_numeric(series_filtradas["Time"], errors="coerce")
                    y = series_filtradas[direcao]
                    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color='black', width=1), name=direcao))
                    fig.update_layout(
                        title=f"Série Temporal - Direção {direcao} (Evento: {data_hora_formatada}, Estação: {estacao_nome})",
                        xaxis_title="Tempo (s)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min, y_max])
                    )
                    if zoom_data:
                        x0, x1 = zoom_data.get("x0"), zoom_data.get("x1")
                        if x0 is not None and x1 is not None:
                            fig.update_xaxes(range=[x0, x1])
                    # Exportar como SVG (vetorial)
                    img_bytes = pio.to_image(fig, format="svg")
                    imagens_series[f"{estacao_nome}-{direcao}"] = base64.b64encode(img_bytes).decode()
        # Espectros de frequência
        if not df_freq_consolidated.empty:
            df_freq_consolidated['estacao'] = df_freq_consolidated['estacao'].astype(str).str.strip()
            df_freq_consolidated['evento'] = df_freq_consolidated['evento'].astype(str).str.strip()
            freq_filtradas = df_freq_consolidated[
                (df_freq_consolidated["estacao"] == codigo_estacao) &
                (df_freq_consolidated["evento"] == evento_id)
            ]
            if not freq_filtradas.empty:
                y_min_freq = 0
                y_max_freq = max(freq_filtradas["T"].max(), freq_filtradas["R"].max(), freq_filtradas["V"].max()) * 1.1
                for direcao in ["T", "R", "V"]:
                    x_freq = pd.Series(freq_filtradas["Freq."]).to_numpy()
                    y_amp = pd.Series(freq_filtradas[direcao]).to_numpy()
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=x_freq, y=y_amp, mode='lines', line=dict(color='black', width=1), name=direcao))
                    try:
                        picos_indices = np.argsort(y_amp)[-5:]
                        picos_indices_ordenados = picos_indices[np.argsort(x_freq[picos_indices])]
                        fig.add_trace(go.Scatter(
                            x=x_freq[picos_indices_ordenados],
                            y=y_amp[picos_indices_ordenados],
                            mode='markers',
                            marker=dict(color='red', size=10),
                            name='Picos'))
                    except Exception:
                        pass
                    fig.update_layout(
                        title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {data_hora_formatada}, Estação: {estacao_nome})",
                        xaxis_title="Frequência (Hz)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min_freq, y_max_freq])
                    )
                    if freq_zoom_data:
                        x0, x1 = freq_zoom_data.get("x0"), freq_zoom_data.get("x1")
                        if x0 is not None and x1 is not None:
                            fig.update_xaxes(range=[x0, x1])
                    # Exportar como SVG (vetorial)
                    img_bytes = pio.to_image(fig, format="svg")
                    imagens_freq[f"{estacao_nome}-{direcao}"] = base64.b64encode(img_bytes).decode()
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
        "<style>"
        "body { font-family: Arial, sans-serif; margin: 30px; }"
        "h2, h3, h4 { margin-bottom: 10px; }"
        "p { margin: 8px 0; }"
        ".estacao-page { page-break-before: always; }"
        ".grafico-img { width: 100%; display: block; margin-left: auto; margin-right: auto; margin-bottom: 10px; }"  # Removido height/object-fit
        ".centered { text-align: center; }"
        ".tabela-pdf { margin-left: auto; margin-right: auto; border-collapse: collapse; margin-bottom: 20px; }"
        ".tabela-pdf th, .tabela-pdf td { border: 1px solid #888; padding: 4px 10px; }"
        "</style></head><body>"
    ]
    # Resumo formatado e tabelas
    resumo_html = mostrar_resumo_evento(evento)
    def extract_tabelas(resumo_html):
        tabelas = []
        if hasattr(resumo_html, 'children'):
            children = resumo_html.children
            if isinstance(children, (list, tuple)):
                for c in children:
                    if hasattr(c, 'props') and getattr(c, 'type', None) == 'Table':
                        tabelas.append(c)
                    elif hasattr(c, 'children'):
                        for cc in (c.children if isinstance(c.children, (list, tuple)) else [c.children]):
                            if hasattr(cc, 'props') and getattr(cc, 'type', None) == 'Table':
                                tabelas.append(cc)
        return tabelas
    def dash_table_to_html(table):
        if not hasattr(table, 'props'):
            return ''
        props = table.props
        thead = props.get('children', [])[0]
        tbody = props.get('children', [])[1]
        head_html = '<tr>' + ''.join(f'<th>{cell.props["children"]}</th>' for cell in thead.props['children'].props['children']) + '</tr>'
        body_html = ''
        for row in tbody.props['children']:
            body_html += '<tr>' + ''.join(f'<td>{cell.props["children"]}</td>' for cell in row.props['children']) + '</tr>'
        return f'<table class="tabela-pdf">{head_html}{body_html}</table>'
    # Centralizar resumo e tabelas
    html_parts.append("<div class='centered' style='page-break-after: always;'>")
    html_parts.append(f"<h2>RELATÓRIO DE MONITORAMENTO DA BARRAGEM DAVÕES</h2>")
    html_parts.append(f"<h3>Evento: {data_hora_formatada}</h3>")
    def extract_text_only(resumo_html):
        if hasattr(resumo_html, 'children'):
            children = resumo_html.children
            if isinstance(children, (list, tuple)):
                return ''.join([extract_text_only(c) for c in children if not (hasattr(c, 'props') and getattr(c, 'type', None) == 'Table')])
            elif isinstance(children, str):
                return children
            elif hasattr(children, 'children'):
                return extract_text_only(children.children)
        elif isinstance(resumo_html, str):
            return resumo_html
        return ''
    resumo_texto = extract_text_only(resumo_html)
    campos = [
        "Data e Hora de Processamento dos Registos:",
        "Estações acima do Trigger:",
        "Classificação do Evento:",
        "Rácio de Estações com Fator de Pico Acima de 10 mg/mg:",
        "Aceleração Máxima Registada:"
    ]
    for campo in campos:
        resumo_texto = resumo_texto.replace(campo, f"</p><p><b>{campo}</b> ")
    html_parts.append(f"<div style='margin-bottom:20px;'><p>{resumo_texto}</p></div>")
    # Tabelas centralizadas (mantém as tabelas na primeira página)
    for tabela in extract_tabelas(resumo_html):
        html_parts.append(dash_table_to_html(tabela))
    html_parts.append("</div>")
    # Páginas de gráficos de Série de Aceleração
    for estacao_nome in selected_stations:
        html_parts.append(f"<div class='estacao-page'><h2 class='centered'>Séries de Aceleração - Estação: {estacao_nome}</h2>")
        # Gráficos empilhados verticalmente, ocupando toda a largura
        html_parts.append("<div style='display: flex; flex-direction: column; justify-content: flex-start; align-items: center; width: 100%; margin-top: 20px;'>")
        for direcao in ["T", "R", "V"]:
            key = f"{estacao_nome}-{direcao}"
            if key in imagens_series:
                html_parts.append(f"<div style='width: 95%; max-width: 800px; margin-bottom: 18px;'><h4 style='text-align:center; margin-bottom: 5px; font-size: 1.1em; font-weight: bold;'>Série de Aceleração - Direção {direcao}</h4>"
                                  f"<img class='grafico-img' style='width:100%; height:320px; display:block; margin:0 auto;' src='data:image/svg+xml;base64,{imagens_series[key]}' />"
                                  f"</div>")
        html_parts.append("</div></div>")
    # Páginas de gráficos de Espectro de Frequência
    for estacao_nome in selected_stations:
        html_parts.append(f"<div class='estacao-page'><h2 class='centered'>Espectros de Frequência - Estação: {estacao_nome}</h2>")
        html_parts.append("<div style='display: flex; flex-direction: column; justify-content: flex-start; align-items: center; width: 100%; margin-top: 20px;'>")
        for direcao in ["T", "R", "V"]:
            key = f"{estacao_nome}-{direcao}"
            if key in imagens_freq:
                html_parts.append(f"<div style='width: 95%; max-width: 800px; margin-bottom: 18px;'><h4 style='text-align:center; margin-bottom: 5px; font-size: 1.1em; font-weight: bold;'>Espectro de Frequência - Direção {direcao}</h4>"
                                  f"<img class='grafico-img' style='width:100%; height:320px; display:block; margin:0 auto;' src='data:image/svg+xml;base64,{imagens_freq[key]}' />"
                                  f"</div>")
        html_parts.append("</div></div>")
    html_parts.append("</body></html>")
    html_full = "".join(html_parts)
    # Geração do TXT de origem dos dados
    txt_data = None
    if export_origem:
        linhas = []
        evento_id = str(evento['evento']).strip()
        data_hora = evento.get('data_hora', '')
        # Caminho base dos arquivos
        base_event_path = os.path.join('events', '2025', '2025')
        for estacao_nome in selected_stations:
            codigo_estacao = STATION_MAPPING.get(estacao_nome, '')
            linhas.append(f'Estação: {estacao_nome}')
            # Arquivos de série e espectro
            data_csv = f"{base_event_path}/01/27/11h52m12s_{codigo_estacao}_data.csv"
            freq_csv = f"{base_event_path}/01/27/11h52m12s_{codigo_estacao}_freq.csv"
            linhas.append(f'  Série de Aceleração: {data_csv}')
            linhas.append(f'  Espectro de Frequência: {freq_csv}')
            # Picos, RMS, value de cada canal
            for canal in ['T', 'R', 'V']:
                # Picos e RMS dos DataFrames
                try:
                    df_data = df_data_consolidated[(df_data_consolidated['estacao'] == codigo_estacao) & (df_data_consolidated['evento'] == evento_id)]
                    pico = df_data[canal].max() if not df_data.empty else '-'
                    rms = np.sqrt(np.mean(df_data[canal]**2)) if not df_data.empty else '-'
                    linhas.append(f'    Canal {canal}: Pico={pico}, RMS={rms}')
                except Exception:
                    linhas.append(f'    Canal {canal}: Pico=-, RMS=-')
            # DFFT do JSON
            try:
                json_path = os.path.join(base_path, base_event_path, '01', '27', '11h52m12s.json')
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    dados_json = json.load(f)
                for canal in ['T', 'R', 'V']:
                    linhas.append(f'    DFFT (canal {canal}):')
                    for ch in dados_json['channels']:
                        if ch.get('chName') == canal:
                            for val in ch.get('value', [])[:5]:
                                freq = val.get('freq', '-')
                                ampl = val.get('ampl', '-')
                                linhas.append(f'      freq: {freq}, ampl: {ampl}')
            except Exception:
                linhas.append('    DFFT: Não encontrado ou erro ao ler JSON')
            linhas.append('')
        txt_data = '\n'.join(linhas)
    # 3. Converter HTML em PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_html:
        tmp_html.write(html_full.encode('utf-8'))
        tmp_html_path = tmp_html.name
    pdf_path = tmp_html_path.replace('.html', '.pdf')
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    pdfkit.from_file(tmp_html_path, pdf_path, configuration=config)
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    os.remove(tmp_html_path)
    os.remove(pdf_path)
    pdf_download = dcc.send_bytes(pdf_bytes, filename=f"relatorio_evento_{evento_id}.pdf")
    if txt_data:
        txt_download = dcc.send_string(txt_data, filename=f"origem_dados_evento_{evento_id}.txt")
    else:
        txt_download = None
    return pdf_download, txt_download

if __name__ == '__main__':
    app.run(debug=True)