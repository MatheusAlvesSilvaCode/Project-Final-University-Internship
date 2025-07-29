# Importa o componente Dash principal e vários componentes para construir a interface e callbacks
from dash import Dash, html, dcc, dash_table, callback, Output, Input, State, ALL, no_update
# Importa o módulo os para manipulação de caminhos e arquivos
import os
# Importa pandas para manipulação de dados em DataFrame
import pandas as pd
# Importa componentes de Bootstrap para Dash
import dash_bootstrap_components as dbc
# Importa a função para carregar eventos dos arquivos JSON
from consolidate_events import carregar_eventos
# Importa classes para manipulação de datas e horas
from datetime import datetime, timedelta
# Importa numpy para operações numéricas
import numpy as np
# Importa plotly para criação de gráficos
import plotly.graph_objects as go
# Importa contexto do callback para saber qual callback foi disparado
from dash import callback_context
# Importa pdfkit para gerar PDF a partir de HTML
import pdfkit
# Importa tempfile para criar arquivos temporários
import tempfile
# Importa componente de download do Dash
from dash.dcc import Download
# Importa exceção para evitar atualizações desnecessárias
from dash.exceptions import PreventUpdate
# Importa decorador para cache de funções
from functools import lru_cache
# Importa layout e callbacks do mapa da barragem
from mapa_barragem import layout as layout_mapa_barragem, register_callbacks as register_map_callbacks
# Importa layout e callbacks da página inicial
from home import layout as layout_home, registrar_callbacks as register_home_callbacks
# Importa função utilitária para classificar eventos
from utils import classificar_evento
# Importa dependências para callbacks
from dash.dependencies import Input, Output, State
# Importa plotly.io para exportar gráficos como imagens
import plotly.io as pio
# Importa base64 para codificar imagens
import base64
# Importa pdfkit novamente (duplicado, mas não afeta funcionamento)
import pdfkit
# Importa contexto do callback (ctx) para saber qual callback foi disparado
from dash import ctx
# Importa no arquivo minio_loader.py os arquivos consolidados. 
from minio_loader import consolidar_dados

# Inicializa o app Dash com tema Bootstrap e permite callbacks de páginas não carregadas
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

# Define o caminho base do projeto
base_path = r'C:\Users\mathe\Desktop\Estágio\Final'
# Define o caminho do arquivo de frequências consolidadas
freq_path = os.path.join(base_path, 'freq_consolidado.csv')
# Define o caminho do arquivo de dados temporais consolidados
data_path = os.path.join(base_path, 'data_consolidado.csv')

# Carrega dados do MinIO
try:
    df_freq_consolidated, df_data_consolidated, df_events_minio = consolidar_dados()
    print("Dados carregados do MinIO com sucesso")
    print(f"DEBUG: df_freq_consolidated shape: {df_freq_consolidated.shape}")
    print(f"DEBUG: df_data_consolidated shape: {df_data_consolidated.shape}")
    print(f"DEBUG: df_events_minio shape: {df_events_minio.shape}")
except Exception as e:
    print(f"Erro ao carregar dados do MinIO: {e}")
    df_freq_consolidated = pd.DataFrame()
    df_data_consolidated = pd.DataFrame()
    df_events_minio = pd.DataFrame()

# Dicionário que mapeia nomes das estações. Essa informação de cada um tem nos JSON.
STATION_MAPPING = {
    'S-01-1': '20160005',
    'S-06-1': '20160004',
    'S-01-2': '20160008',
    'S-07-1': '20160003',
    'S-09-1': '20160007',
    'S-10-1': '20160006'
}

# Mapeamento reverso para converter códigos de estação para nomes
STATION_MAPPING_REVERSE = {v: k for k, v in STATION_MAPPING.items()}

# Tenta carregar os dados de frequência consolidados
try:
    if df_freq_consolidated.empty:
        df_freq_consolidated = pd.read_csv(freq_path)  # Lê o arquivo CSV de frequências
except Exception as error:
    print(f"Erro ao carregar freq_consolidado.csv: {error}")  # Mostra erro se não conseguir ler
    if df_freq_consolidated.empty:
        df_freq_consolidated = pd.DataFrame()  # Cria DataFrame vazio em caso de erro

# Tenta carregar os dados temporais consolidados
try:
    if df_data_consolidated.empty:
        df_data_consolidated = pd.read_csv(data_path)  # Lê o arquivo CSV de dados temporais
except Exception as error:
    print(f"Erro ao carregar data_consolidado.csv: {error}")  # Mostra erro se não conseguir ler
    if df_data_consolidated.empty:
        df_data_consolidated = pd.DataFrame()  # Cria DataFrame vazio em caso de erro

# Tenta carregar os dados de eventos a partir dos arquivos JSON
try:  # Tenta executar o bloco de código abaixo para carregar os eventos
    events_path = os.path.join(base_path, "events", "2025", "2025")  # Monta o caminho completo para a pasta de eventos
    print(f"DEBUG: Tentando carregar eventos de: {events_path}")
    df_events = carregar_eventos(events_path)  # Chama a função para carregar os eventos a partir dos arquivos JSON
    print(f"DEBUG: df_events carregado com shape: {df_events.shape}")
    
    # Se não conseguiu carregar do MinIO, usa os dados locais
    if df_events_minio.empty and not df_events.empty:
        df_events = df_events
        print("DEBUG: Usando dados locais (MinIO vazio)")
    elif not df_events_minio.empty:
        df_events = df_events_minio
        print("DEBUG: Usando dados do MinIO")
    
    unique_stations = df_events["estacao"].unique()  # Obtém a lista de estações únicas presentes nos eventos
    unique_events = df_events["evento"].unique()  # Obtém a lista de eventos únicos
    print(f"DEBUG: Estações carregadas: {unique_stations}")
    print(f"DEBUG: Eventos carregados: {unique_events}")
except Exception as error:  # Se ocorrer qualquer erro ao tentar carregar os eventos, executa o bloco abaixo
    print(f"Erro ao carregar eventos: {error}")  # Exibe a mensagem de erro no console para depuração
    df_events = pd.DataFrame()  # Cria um DataFrame vazio para df_events, garantindo que o código não quebre depois
    unique_stations = []  # Define a lista de estações como vazia, pois não foi possível carregar
    unique_events = []  # Define a lista de eventos como vazia, pois não foi possível carregar

# Função em cache para classificar eventos rapidamente
@lru_cache(maxsize=None)
def obter_classificacao(evento):
    return classificar_evento(evento, df_events)[0]

# Função para criar resumo básico quando não há dados completos
def criar_resumo_basico(evento):
    """Cria um resumo básico quando não há dados completos no DataFrame"""
    data_hora_proc = datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    data_hora_evento = evento.get('data_hora', None)

    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)

    estacoes = evento.get('estacao', [])
    if isinstance(estacoes, str):
        estacoes = [estacoes]
    elif not isinstance(estacoes, list):
        estacoes = []

    estacoes_str = ', '.join(estacoes) if estacoes else 'N/A'

    return html.Div([
        html.P([
            html.B("Data e Hora de Processamento dos Registos: "), f"{data_hora_proc}"
        ]),
        html.P([
            html.B("Evento: "), f"{evento.get('evento', 'N/A')}"
        ]),
        html.P([
            html.B("Data e Hora do Evento: "), f"{data_hora_formatada}"
        ]),
        html.P([
            html.B("Estações: "), f"{estacoes_str}"
        ]),
        html.P([
            html.B("Classificação: "), f"{evento.get('classificacao', 'N/A')}"
        ]),
        html.P([
            html.B("Observação: "), "Dados detalhados não disponíveis no momento."
        ])
    ])

# Função para criar tabela de eventos em formato Dash/HTML
def criar_tabela_eventos(eventos):
    if eventos is None or (hasattr(eventos, "__len__") and len(eventos) == 0):
        return html.Div("Nenhum evento disponível para exibição")

    try:
        df = pd.DataFrame(eventos)
        df['hora'] = pd.to_datetime(df['data_hora']).dt.strftime('%Hh%Mm%Ss')
        df_explodido = df.explode('estacao')
        df_pivot = df_explodido.pivot_table(
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
        return html.Div("Erro ao exibir eventos", style={"textAlign": "center", "marginTop": "50px"})

# Layout da página de relatórios atualizado com o botão do mapa
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
    html.Div(id='div-dummy', style={'display': 'none'}),
    dcc.Download(id="download-pdf"),
    dcc.Download(id="download-origem"),
    dcc.Store(id="armazenar-estacoes-exportar", storage_type="memory"),
    dcc.Store(id="armazenar-mapa-modal", data=False),
    dcc.Store(id="zoom-range-store", storage_type="memory"),
    dcc.Store(id="freq-zoom-range-store", storage_type="memory"),
    
    # Modal para exibir o mapa da barragem
    dbc.Modal(
        [
            dbc.ModalHeader("Mapa da Barragem"),
            dbc.ModalBody(
                html.Img(src="/assets/SOS-Daivoes.svg", style={"width": "100%", "height": "auto"})
            ),
            dbc.ModalFooter(
                dbc.Button("Fechar", id="fechar-mapa-btn", className="ml-auto")
            )
        ],
        id="mapa-modal",
        size="lg",
        is_open=False,
    ),
    
    # Modal de exportação
    dbc.Modal(
        [
            dbc.ModalBody(
                html.Div([
                    # Card 1: Exportação PDF
                    html.Div([
                        html.H5("EXPORTAR PDF:", className="card-title", style={"textAlign": "center"}),
                        dbc.Checkbox(
                            id="export-all-checkbox",
                            className="mb-2",
                            label="Todas as estações",
                            value=False,
                            style={"marginBottom": "15px"}
                        ),
                        dbc.Checklist(
                            id="export-stations-checklist",
                            options=[{"label": est, "value": est} for est in unique_stations],
                            value=[],
                            inline=False,
                            style={"marginBottom": "10px"}
                        ),
                        dbc.Checkbox(
                            id="export-origem-checkbox",
                            value=False,
                        ),
                        html.Div([
                            dbc.Button("Exportar", id="confirm-export-btn", color="primary", className="me-2"),
                            dbc.Button("Cancelar", id="cancel-export-btn", color="secondary")
                        ], style={"textAlign": "center", "marginTop": "10px"})
                    ], style={"maxWidth": "400px", "margin": "0 24px", "boxShadow": "0 4px 16px rgba(0,0,0,0.15)", "padding": "24px", "background": "#fff", "borderRadius": "12px"}),
                    
                    # Card 2: Exportação de dados de origem dos gráficos
                    html.Div([
                        html.H5("EXPORTAR TXT", className="card-title", style={"textAlign": "center"}),
                        html.Div([
                            html.Div([
                                html.H6("Séries de Aceleração", style={"marginBottom": "0.5rem"}),
                                dbc.Checkbox(
                                    id="check-all-export-dados",
                                    className="mb-2",
                                    label="Exportar todas as estações",
                                    style={"marginBottom": "15px"}
                                ),
                                dbc.Checklist(
                                    options=[{"label": est, "value": est} for est in unique_stations],
                                    value=[],
                                    id="checklist-series-export",
                                    inline=False,
                                    style={"marginBottom": "1rem"}
                                ),
                            ], style={"marginBottom": "1.5rem"}),
                            html.Hr(),
                            html.Div([
                                html.H6("Espectros de Frequência", style={"marginBottom": "0.5rem"}),
                                dbc.Checkbox(
                                    id="check-all-export-dados",
                                    className="mb-2",
                                    label="Exportar todas as estações",
                                    style={"marginBottom": "15px"}
                                ),
                                dbc.Checklist(
                                    options=[{"label": est, "value": est} for est in unique_stations],
                                    value=[],
                                    id="checklist-freq-export",
                                    inline=False,
                                    style={"marginBottom": "1rem"}
                                ),
                            ]),
                        ], style={"minWidth": "260px", "maxWidth": "340px", "margin": "0 auto"}),
                        html.Hr(),
                        dbc.Button("Exportar Dados", id="btn-exportar-dados", color="primary", className="w-100 mt-2"),
                    ], style={"maxWidth": "400px", "margin": "0 24px", "boxShadow": "0 4px 16px rgba(0,0,0,0.15)", "padding": "24px", "background": "#fff", "borderRadius": "12px"})
                ], style={
                    "display": "flex",
                    "flexDirection": "row",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "minHeight": "40vh",
                    "width": "100%"
                })
            )
        ],
        id="modal-exportar",
        is_open=False,
        size="lg",
        centered=True,
    ),
    
    html.H3('RELATÓRIO DE EVENTO SÍSMICO - BARRAGEM DE DAIVÕES', style={"textAlign": "center", "marginTop": "30px"}),
    html.Div(id="titulo-evento-dinamico", style={"textAlign": "center", "color": "black", "marginTop": "10px", "marginBottom": "10px"}),
    
    # Botões de exportação e mapa
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
            dbc.Button(
                "Mapa da Barragem",
                id="botao-mapa-barragem",
                color="secondary",
                className="mb-3",
                style={
                    "position": "fixed",
                    "top": "120px",
                    "right": "20px",
                    "zIndex": "1000",
                },
            ),
        ], width=12),
    ]),
    
    # Abas dinâmicas para estações + Resumo
    dbc.Tabs(
        id="abas-estacoes",
        active_tab="resumo",
        children=[
            dbc.Tab(label="Resumo", tab_id="resumo")
        ],
        style={
            "position": "sticky",
            "top": "0",
            "zIndex": "999",
            "background": "#fff"
        }
    ),
    html.Div(id="conteudo-aba", style={"padding": "20px"})
])

# Layout principal do app
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),  # Componente para controlar a URL da página
    dcc.Store(id='filters-store'),  # Armazena filtros aplicados
    dcc.Store(id='selected-event-store'),  # Armazena o evento selecionado
    dcc.Store(id='event-data-store', data=[]),  # Armazena dados dos eventos
    dcc.Store(id='armazenar-dados-eventos'),  # Armazena dados dos eventos filtrados
    
    # Menu lateral fixo
    html.Div(id='menu-lateral', style={
        "position": "fixed",  # Fixa o menu na tela
        "width": "16.666%",  # Largura do menu lateral
        "height": "100vh",  # Altura total da tela
        "overflowY": "auto",  # Permite rolagem vertical
        "backgroundColor": "#f8f9fa",  # Cor de fundo
        "borderRight": "1px solid #dee2e6",  # Borda à direita
        "padding": "10px",  # Espaçamento interno
        "zIndex": "100"  # Z-index para sobrepor outros elementos
    }),
    
    # Conteúdo principal
    html.Div(id='page-content', style={
        "marginLeft": "16.666%",  # Margem para não sobrepor o menu
        "padding": "20px"
    })
])

# Função para mostrar resumo do evento
def mostrar_resumo_evento(evento):
    if not evento:
        return html.P('Nenhum evento válido para exibir.')
    
    evento_id = str(evento['evento']).strip()
    
    # Verificar se df_events tem a coluna 'evento'
    if not hasattr(df_events, 'columns') or 'evento' not in df_events.columns:
        print("DEBUG: Coluna 'evento' não encontrada, criando resumo básico")
        return criar_resumo_basico(evento)
    
    dados_evento = df_events[df_events["evento"].astype(str).str.strip() == evento_id]
    if dados_evento.empty:
        print("DEBUG: Nenhum dado encontrado no DataFrame, criando resumo básico")
        return criar_resumo_basico(evento)
    
    data_hora_evento = evento.get('data_hora', None)
    data_hora_proc = datetime.now().strftime('%Y-%m-%d, %H:%M:%S')
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    
    estacoes_trigger = ', '.join(sorted(map(str, set(dados_evento.loc[pd.Series(dados_evento['trigger']).notna(), 'estacao']))))
    classificacao, racio = classificar_evento(evento_id, df_events)
    
    series_picos = pd.Series(dados_evento['peak'])
    idx_pico = series_picos.idxmax() if not series_picos.empty else None
    pico_max = dados_evento.loc[idx_pico] if idx_pico is not None else {'estacao':'-','direcao':'-','peak':0,'valor':0}
    
    tabela_picos = dados_evento.pivot_table(index='estacao', columns='direcao', values='peak', aggfunc='max').reindex(columns=['T','R','V'])
    tabela_fatores = dados_evento.pivot_table(index='estacao', columns='direcao', values='valor', aggfunc='max').reindex(columns=['T','R','V'])
    
    return html.Div([
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
                        html.Th("Estação")] + [html.Th(d) for d in ['T','R','V']
                    ])),
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
                        html.Th("Estação")] + [html.Th(d) for d in ['T','R','V']
                    ])),
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

# Função para mostrar conteúdo da estação filtrada baseada no layout de referência
def mostrar_conteudo_estacao_filtrada(estacao_selecionada, evento, apenas_tabelas=False):
    global df_data_consolidated, df_freq_consolidated
    
    if estacao_selecionada is None or evento is None:
        return html.P("Nenhuma estação selecionada.")
    
    evento_id = str(evento['evento']).strip()
    estacao = str(estacao_selecionada).strip()
    
    if estacao in STATION_MAPPING.values():
        estacao_nome = [k for k, v in STATION_MAPPING.items() if v == estacao]
        if estacao_nome:
            estacao = estacao_nome[0]
    
    # Verificar se df_events tem a coluna 'evento'
    if not hasattr(df_events, 'columns') or 'evento' not in df_events.columns:
        return html.Div([
            html.H4(f"Estação: {estacao}"),
            html.P("Dados detalhados da estação não disponíveis no momento."),
            html.P(f"Evento: {evento_id}")
        ])
    
    dados_estacao = df_events[
        (df_events["estacao"].astype(str).str.strip() == estacao) &
        (df_events["evento"].astype(str).str.strip() == evento_id)
    ].copy()
    
    if dados_estacao.empty:
        return html.P("Nenhum dado para esta estação.")
    
    # Obter dados de aceleração para a estação e evento
    codigo_estacao = STATION_MAPPING.get(estacao, estacao)
    
    # Verificar se df_data_consolidated tem os dados necessários
    if df_data_consolidated.empty or 'estacao' not in df_data_consolidated.columns:
        return html.Div([
            html.H4(f"Estação: {estacao}"),
            html.P("Dados de aceleração não disponíveis no momento."),
            html.P(f"Evento: {evento_id}")
        ])
    
    # Verificar se a coluna 'evento' existe no df_data_consolidated
    if 'evento' not in df_data_consolidated.columns:
        return html.Div([
            html.H4(f"Estação: {estacao}"),
            html.P("Dados de evento não encontrados nos dados consolidados."),
            html.P(f"Evento: {evento_id}")
        ])
    
    # Filtrar dados usando o código da estação
    dados_aceleracao = df_data_consolidated[
        (df_data_consolidated["estacao"] == codigo_estacao) &
        (df_data_consolidated["evento"] == evento_id)
    ]
    
    # Obter dados de frequência para a estação e evento
    if df_freq_consolidated.empty or 'estacao' not in df_freq_consolidated.columns or 'evento' not in df_freq_consolidated.columns:
        dados_frequencia = pd.DataFrame()
    else:
        dados_frequencia = df_freq_consolidated[
            (df_freq_consolidated["estacao"] == codigo_estacao) &
            (df_freq_consolidated["evento"] == evento_id)
        ]
    
    # Criar gráfico de série temporal de aceleração
    figura_aceleracao = go.Figure()
    
    if not dados_aceleracao.empty:
        for direcao in ['T', 'R', 'V']:
            if direcao in dados_aceleracao.columns:
                figura_aceleracao.add_trace(go.Scatter(
                    x=dados_aceleracao['Time'],
                    y=dados_aceleracao[direcao],
                    mode='lines',
                    name=direcao,
                    line=dict(width=1)
                ))
    
    figura_aceleracao.update_layout(
        title=f"Série Temporal de Aceleração - Estação {estacao}",
        xaxis_title="Tempo (s)",
        yaxis_title="Aceleração (mg)",
        height=400
    )
    
    # Criar gráfico de espectros de frequência
    figura_frequencia = go.Figure()
    
    if not dados_frequencia.empty:
        for direcao in ['T', 'R', 'V']:
            if direcao in dados_frequencia.columns:
                figura_frequencia.add_trace(go.Scatter(
                    x=dados_frequencia['Freq.'],
                    y=dados_frequencia[direcao],
                    mode='lines',
                    name=direcao,
                    line=dict(width=1)
                ))
    
    figura_frequencia.update_layout(
        title=f"Espectros de Frequência - Estação {estacao}",
        xaxis_title="Frequência (Hz)",
        yaxis_title="Amplitude (mg)",
        height=400
    )
    
    # Criar tabelas com valores de pico
    tabela_picos = dados_estacao.pivot_table(index='direcao', values='peak', aggfunc='max').reindex(['T','R','V'])
    tabela_fatores = dados_estacao.pivot_table(index='direcao', values='valor', aggfunc='max').reindex(['T','R','V'])
    
    # Calcular aceleração máxima
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
            # Verificar se as colunas necessárias existem
            if 'estacao' not in df_data_consolidated.columns or 'evento' not in df_data_consolidated.columns:
                # Tentar carregar do arquivo local
                try:
                    data_path = os.path.join(base_path, 'data_consolidado.csv')
                    if os.path.exists(data_path):
                        df_data_local = pd.read_csv(data_path)
                        if 'estacao' in df_data_local.columns and 'evento' in df_data_local.columns:
                            df_data_consolidated = df_data_local
                        else:
                            graficos_series = html.P("Estrutura de dados incompatível")
                            return html.Div([graficos_series])
                    else:
                        graficos_series = html.P("Arquivo de dados não encontrado")
                        return html.Div([graficos_series])
                except Exception as e:
                    graficos_series = html.P(f"Erro ao carregar dados: {str(e)}")
                    return html.Div([graficos_series])
            
            df_data_consolidated['estacao'] = df_data_consolidated['estacao'].astype(str).str.strip()
            df_data_consolidated['evento'] = df_data_consolidated['evento'].astype(str).str.strip()
            series_filtradas = df_data_consolidated[
                (df_data_consolidated["estacao"] == codigo_estacao) & 
                (df_data_consolidated["evento"] == str(evento_id).strip())
            ]
            
            if not series_filtradas.empty and all(col in series_filtradas.columns for col in ['T', 'R', 'V', 'Time']):
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
                        yaxis=dict(range=[y_min, y_max], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7),
                        xaxis=dict(range=[series_filtradas["Time"].min(), series_filtradas["Time"].max()], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7)
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
            # Verificar se as colunas necessárias existem
            if 'estacao' not in df_freq_consolidated.columns or 'evento' not in df_freq_consolidated.columns:
                # Tentar carregar do arquivo local
                try:
                    freq_path = os.path.join(base_path, 'freq_consolidado.csv')
                    if os.path.exists(freq_path):
                        df_freq_local = pd.read_csv(freq_path)
                        if 'estacao' in df_freq_local.columns and 'evento' in df_freq_local.columns:
                            df_freq_consolidated = df_freq_local
                        else:
                            graficos_freq = html.P("Estrutura de dados incompatível")
                            return html.Div([graficos_freq])
                    else:
                        graficos_freq = html.P("Arquivo de frequência não encontrado")
                        return html.Div([graficos_freq])
                except Exception as e:
                    graficos_freq = html.P(f"Erro ao carregar dados: {str(e)}")
                    return html.Div([graficos_freq])
            
            df_freq_consolidated['estacao'] = df_freq_consolidated['estacao'].astype(str).str.strip()
            df_freq_consolidated['evento'] = df_freq_consolidated['evento'].astype(str).str.strip()
            freq_filtradas = df_freq_consolidated[
                (df_freq_consolidated["estacao"] == codigo_estacao) & 
                (df_freq_consolidated["evento"] == str(evento_id).strip())
            ]
            
            if not freq_filtradas.empty and all(col in freq_filtradas.columns for col in ['T', 'R', 'V', 'Freq.']):
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
                        pass
                    figura.update_layout(
                        title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {data_hora_formatada})",
                        xaxis_title="Frequência (Hz)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min_freq, y_max_freq], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7),
                        xaxis=dict(range=[x_freq.min(), x_freq.max()], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7)
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
    
    if apenas_tabelas == True:
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
    elif apenas_tabelas == "freq":
        # Retorna apenas o conteúdo de espectros de frequência
        return html.Div([
            html.H1('Espectros de Frequência das Séries de Aceleração', id="espectros-frequencia", 
                   style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
            graficos_freq
        ])
    
    return html.Div([
        # Informações de aceleração máxima
        html.H5("Aceleração Máxima:", style={"fontWeight": "bold", "marginTop": "15px"}),
        dbc.Table([
            html.Tbody([
                html.Tr([html.Td("Direção:"), html.Td(aceleracao_maxima['direcao'])]),
                html.Tr([html.Td("Magnitude:"), html.Td(aceleracao_maxima['magnitude'])]),
                html.Tr([html.Td("Fator de Pico:"), html.Td(aceleracao_maxima['fator_pico'])])
            ])
        ], style={"marginBottom": "20px"}),
        
        # Tabelas de picos e fatores de pico
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
        
        # Título dos espectros de frequência
        html.H1('Espectros de Frequência das Séries de Aceleração', id="espectros-frequencia", 
               style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
        graficos_freq
    ])

# Callbacks para renderizar páginas
# Callback para renderizar o conteúdo da página conforme a URL
@app.callback(
    Output('page-content', 'children'),  # Saída: conteúdo da página
    Input('url', 'pathname'),  # Entrada: caminho da URL
    prevent_initial_call=False  # Permite chamada inicial
)
def render_page_content(pathname):
    if pathname == "/dam-map":  # Se a URL for /dam-map
        return layout_mapa_barragem  # Mostra o layout do mapa da barragem
    elif pathname == "/reports":  # Se a URL for /reports
        return layout_relatorios  # Mostra o layout de relatórios
    else:
        return layout_home  # Mostra o layout da página inicial

# Callback para atualizar o menu lateral
@callback(
    Output('menu-lateral', 'children'),
    Input('url', 'pathname')
)
def update_menu_lateral(pathname):
    return [
        html.H4("Menu Principal", style={"padding": "10px", "borderBottom": "1px solid #ddd", "marginBottom": "10px"}),
        html.Div([
            html.H6("OPÇÕES PRINCIPAIS", style={"color": "#555", "padding": "5px 10px", "marginTop": "15px"}),
            dbc.Nav([
                dbc.NavLink("Início", href="/", active=pathname == "/", style={"padding": "8px 15px"}),
                dbc.NavLink("Relatórios", href="/reports", active=pathname == "/reports", style={"padding": "8px 15px"}),
                dbc.NavLink("Mapa da Barragem", href="/dam-map", active=pathname == "/dam-map", style={"padding": "8px 15px"}),
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
    ]

# Callback para atualizar as abas das estações dinamicamente
@app.callback(
    Output("abas-estacoes", "children"),
    Input('selected-event-store', 'data'),
    prevent_initial_call=False
)
def atualizar_abas_estacoes(evento_selecionado):
    print(f"DEBUG: atualizar_abas_estacoes chamado com evento_selecionado: {evento_selecionado}")
    
    if not evento_selecionado:
        print("DEBUG: Nenhum evento selecionado, retornando apenas aba Resumo")
        return [dbc.Tab(label="Resumo", tab_id="resumo")]
    
    # Obter estações únicas do evento selecionado
    evento_id = str(evento_selecionado.get('evento', '')).strip()
    print(f"DEBUG: evento_id extraído: {evento_id}")
    
    if not evento_id:
        print("DEBUG: evento_id vazio, retornando apenas aba Resumo")
        return [dbc.Tab(label="Resumo", tab_id="resumo")]
    
    # Verificar se df_events está carregado e tem a coluna 'evento'
    print(f"DEBUG: df_events shape: {df_events.shape if hasattr(df_events, 'shape') else 'DataFrame não carregado'}")
    print(f"DEBUG: df_events colunas: {df_events.columns.tolist() if hasattr(df_events, 'columns') else 'N/A'}")
    
    # Verificar se a coluna 'evento' existe
    if not hasattr(df_events, 'columns') or 'evento' not in df_events.columns:
        print("DEBUG: Coluna 'evento' não encontrada no DataFrame")
        # Tentar usar as estações do evento selecionado diretamente
        estacoes_evento = evento_selecionado.get('estacao', [])
        if isinstance(estacoes_evento, str):
            estacoes_evento = [estacoes_evento]
        elif not isinstance(estacoes_evento, list):
            estacoes_evento = []
        
        print(f"DEBUG: Usando estações do evento selecionado: {estacoes_evento}")
        abas = [dbc.Tab(label="Resumo", tab_id="resumo")]
        for estacao in estacoes_evento:
            if estacao:
                abas.append(dbc.Tab(label=str(estacao), tab_id=str(estacao)))
        return abas
    
    # Filtrar dados do evento
    dados_evento = df_events[df_events["evento"].astype(str).str.strip() == evento_id]
    print(f"DEBUG: dados_evento encontrados: {len(dados_evento)} registros")
    
    if dados_evento.empty:
        print("DEBUG: Nenhum dado encontrado para o evento, retornando apenas aba Resumo")
        return [dbc.Tab(label="Resumo", tab_id="resumo")]
    
    # Obter estações únicas
    estacoes_evento = dados_evento["estacao"].unique()
    print(f"DEBUG: estações encontradas: {estacoes_evento}")
    
    # Criar abas: Resumo + uma aba para cada estação
    abas = [dbc.Tab(label="Resumo", tab_id="resumo")]
    for estacao in estacoes_evento:
        abas.append(dbc.Tab(label=str(estacao), tab_id=str(estacao)))
    
    print(f"DEBUG: abas criadas: {[tab.label for tab in abas]}")
    return abas

# Callback para atualizar o conteúdo das abas
@app.callback(
    Output("conteudo-aba", "children"),
    Input("abas-estacoes", "active_tab"),
    Input('selected-event-store', 'data'),
    State('event-data-store', 'data'),
    prevent_initial_call=False
)
def mostrar_relatorio(aba_ativa, evento_selecionado, event_data):
    print(f"DEBUG: mostrar_relatorio chamado - aba_ativa: {aba_ativa}, evento_selecionado: {evento_selecionado}")
    
    if not evento_selecionado:
        print("DEBUG: Nenhum evento selecionado, mostrando spinner")
        return dbc.Spinner(size="lg", color="primary", fullscreen=False, children=[html.Div("Carregando evento...")])
    
    evento_para_exibir = evento_selecionado if isinstance(evento_selecionado, dict) else None
    if not evento_para_exibir:
        print("DEBUG: Evento não é um dict válido")
        return html.P('Nenhum evento válido para exibir.')
    
    print(f"DEBUG: Mostrando conteúdo para aba: {aba_ativa}")
    if aba_ativa == "resumo":
        return mostrar_resumo_evento(evento_para_exibir)
    else:
        # Use sempre a aba ativa como estação
        estacao_ativa = aba_ativa
        return html.Div([
            dcc.Store(id="zoom-range-store", storage_type="memory"),
            dcc.Store(id="freq-zoom-range-store", storage_type="memory"),
            html.H1('Séries de Aceleração', id="series-aceleracao", style={"textAlign": "center", "margin": "20px 0 20px 20px", "marginTop": "30px"}),
            mostrar_conteudo_estacao_filtrada(estacao_ativa, evento_para_exibir, apenas_tabelas=True),
            dcc.Graph(id="serie-T"),
            dcc.Graph(id="serie-R"),
            dcc.Graph(id="serie-V"),
            mostrar_conteudo_estacao_filtrada(estacao_ativa, evento_para_exibir, apenas_tabelas="freq"),
        ])

# Callback para mostrar/esconder modal do mapa
@app.callback(
    Output("mapa-modal", "is_open"),
    Input("botao-mapa-barragem", "n_clicks"),
    Input("fechar-mapa-btn", "n_clicks"),
    State("mapa-modal", "is_open"),
    prevent_initial_call=True
)
def alternar_modal_mapa(n1, n2, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "botao-mapa-barragem":
        return True
    elif button_id == "fechar-mapa-btn":
        return False
    return is_open

# Callback para selecionar todas as estações nas checklists
@app.callback(
    Output("checklist-exportar-series", "value"),
    Input("checkbox-selecionar-todas-series", "value"),
    State("checklist-exportar-series", "options"),
    prevent_initial_call=True
)
def selecionar_todas_series(selecionar_todas, opcoes):
    if selecionar_todas:
        return [opcao["value"] for opcao in opcoes]
    return []

@app.callback(
    Output("checklist-exportar-freq", "value"),
    Input("checkbox-selecionar-todas-freq", "value"),
    State("checklist-exportar-freq", "options"),
    prevent_initial_call=True
)
def selecionar_todas_freq(selecionar_todas, opcoes):
    if selecionar_todas:
        return [opcao["value"] for opcao in opcoes]
    return []

# Callback para atualizar o título do evento dinamicamente
@app.callback(
    Output('titulo-evento-dinamico', 'children'),
    Input('selected-event-store', 'data'),
    prevent_initial_call=False
)
def atualizar_titulo_evento(evento):
    if not evento:
        return ""
    data_hora_evento = evento.get('data_hora', None)
    evento_id = evento.get('evento', None)
    try:
        data_hora_formatada = pd.to_datetime(data_hora_evento).strftime('%Y-%m-%d, %H:%M:%S')
    except Exception:
        data_hora_formatada = str(data_hora_evento)
    # Obter classificação do evento
    classificacao = None
    if evento_id is not None:
        try:
            classificacao, _ = classificar_evento(str(evento_id), df_events)
        except Exception:
            classificacao = None
    if classificacao:
        return html.H4(f"Evento: {data_hora_formatada} ({classificacao})", style={"color": "black", "margin": "0"})
    else:
        return html.H4(f"Evento: {data_hora_formatada}", style={"color": "black", "margin": "0"})

# --- Callbacks para controle do modal de exportação ---

@app.callback(
    Output('modal-exportar', 'is_open'),
    Input('button-select-event', 'n_clicks'),
    Input('cancel-export-btn', 'n_clicks'),
    Input('confirm-export-btn', 'n_clicks'),
    State('modal-exportar', 'is_open'),
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

# Callback para sincronizar o zoom dos gráficos de séries de aceleração
@app.callback(
    Output("zoom-range-store", "data"),
    Input("serie-T", "relayoutData"),
    Input("serie-R", "relayoutData"),
    Input("serie-V", "relayoutData"),
    prevent_initial_call=True
)
def sync_zoom(relayout_t, relayout_r, relayout_v):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    relayout = ctx.triggered[0]['value']
    if relayout and "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        return {"x0": relayout["xaxis.range[0]"], "x1": relayout["xaxis.range[1]"]}
    return None

# Callback para sincronizar o zoom dos gráficos de espectro de frequência
@app.callback(
    Output("freq-zoom-range-store", "data"),
    Input("freq-T", "relayoutData"),
    Input("freq-R", "relayoutData"),
    Input("freq-V", "relayoutData"),
    prevent_initial_call=True
)
def sync_freq_zoom(relayout_t, relayout_r, relayout_v):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    relayout = ctx.triggered[0]['value']
    if relayout and "xaxis.range[0]" in relayout and "xaxis.range[1]" in relayout:
        return {"x0": relayout["xaxis.range[0]"], "x1": relayout["xaxis.range[1]"]}
    return None

# Callback para atualizar e sincronizar os gráficos de séries de aceleração
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
    global df_data_consolidated
    
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
        fig_empty = go.Figure()
        fig_empty.add_annotation(text="Sem dados para esta estação/evento", xref="paper", yref="paper", showarrow=False, font=dict(size=20))
        return fig_empty, fig_empty, fig_empty
    
    # Filtrar dados
    series_filtradas = df_data_consolidated[
        (df_data_consolidated["estacao"] == codigo_estacao) & 
        (df_data_consolidated["evento"] == str(evento_id).strip())
    ]
    
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
        x = pd.to_numeric(series_filtradas["Time"], errors="coerce")
        y = series_filtradas[direcao]
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
            yaxis=dict(range=[y_min, y_max], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7),
            xaxis=dict(range=[x.min(), x.max()], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7)
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

# Callback para atualizar e sincronizar os gráficos de espectro de frequência
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
    global df_freq_consolidated
    
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
    
    # Filtrar dados
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
            pass
        fig.update_layout(
            title=f"Espectro de Frequência - FFT Direção {direcao} (Evento: {data_hora_formatada})",
            xaxis_title="Frequência (Hz)",
            yaxis_title="Aceleração (mg)",
            margin=dict(l=40, r=40, t=40, b=40),
            height=300,
            plot_bgcolor='white',
            yaxis=dict(range=[y_min_freq, y_max_freq], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7),
            xaxis=dict(range=[x_freq.min(), x_freq.max()], showgrid=True, gridcolor='#e5e5e5', gridwidth=0.7)
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

# Registra os callbacks
register_map_callbacks(app)
register_home_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)