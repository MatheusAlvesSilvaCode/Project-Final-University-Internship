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
        print(f"Erro ao criar tabela de eventos: {e}")
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
    html.H3('RELATÓRIO DE MONITORAMENTO DA BARRAGEM DAVÕES', style={"textAlign": "center", "marginTop": "30px"}),
    html.Div(id="titulo-evento-dinamico", style={"textAlign": "center", "color": "black", "marginTop": "10px", "marginBottom": "10px"}),
    dbc.Row([
        dbc.Col([
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
    print("DEBUG mostrar_relatorio - evento_selecionado:", evento_selecionado)
    print("DEBUG mostrar_relatorio - event_data:", event_data)
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
    return mostrar_conteudo_estacao_filtrada(estacao_ativa, evento_para_exibir)

def mostrar_conteudo_estacao_filtrada(estacao_selecionada, evento):
    print("DEBUG evento recebido:", evento)
    print("DEBUG estacao_selecionada:", estacao_selecionada)
    print("DEBUG df_events['evento'].unique():", df_events['evento'].unique())
    print("DEBUG df_events['estacao'].unique():", df_events['estacao'].unique())
    if estacao_selecionada is None or evento is None:
        return html.P("Nenhuma estação selecionada.")
    evento_id = str(evento['evento']).strip()
    estacao = str(estacao_selecionada).strip()
    if estacao in STATION_MAPPING.values():
        estacao_nome = [k for k, v in STATION_MAPPING.items() if v == estacao]
        if estacao_nome:
            print(f"DEBUG convertendo código {estacao} para nome {estacao_nome[0]}")
            estacao = estacao_nome[0]
    print('DEBUG evento_id:', evento_id)
    print('DEBUG estacao (após ajuste):', estacao)
    print('DEBUG filtro:', (df_events["estacao"].astype(str).str.strip() == estacao))
    print('DEBUG filtro evento:', (df_events["evento"].astype(str).str.strip() == evento_id))
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
                        title=f"Série Temporal - Direção {direcao} (Evento: {evento_id})",
                        xaxis_title="Tempo (s)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min, y_max])
                    )
                    return dcc.Graph(figure=figura, style={'margin-bottom': '20px'})
                
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
                        print(f"Erro ao marcar picos no gráfico de {direcao}: {e}")
                    figura.update_layout(
                        title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {evento_id})",
                        xaxis_title="Frequência (Hz)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min_freq, y_max_freq])
                    )
                    return dcc.Graph(figure=figura, style={'margin-bottom': '20px'})
                
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
                    criar_grafico_freq("T"),
                    criar_grafico_freq("R"),
                    criar_grafico_freq("V")
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
    
    return html.Div([
        # Remover o título do evento daqui
        html.H5("Aceleração Máxima:", style={"fontWeight": "bold", "marginTop": "15px"}),
        dbc.Table([
            html.Tbody([
                #html.Tr([html.Td("Estação:"), html.Td(aceleracao_maxima['estacao'])]),
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
        
        html.H1('Séries de Aceleração', id="series-aceleracao", 
               style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
        graficos_series,
        
        html.H1('Espectros de Frequência das Séries de Aceleração', id="espectros-frequencia", 
               style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
        graficos_freq
    ])

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

if __name__ == '__main__':
    app.run(debug=True)