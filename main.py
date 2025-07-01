import os
from dash import Dash, html, dcc, dash_table, callback, Output, Input, State
import pandas as pd
import dash_bootstrap_components as dbc
from consolidate_events import carregar_eventos
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
from dash import callback_context
import pdfkit
from dash import no_update
import tempfile
from dash.dcc import Download
from dash.exceptions import PreventUpdate
from functools import lru_cache
from mapa_barragem import layout as layout_mapa_barragem
from mapa_barragem import layout as layout_mapa_barragem, register_callbacks
from home import layout as layout_home, register_callbacks as register_home_callbacks 

# Inicializa o aplicativo Dash
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)

# Configuração dos caminhos dos arquivos
caminho_base = r'C:\Users\mathe\Desktop\Estágio\Final'
caminho_freq = os.path.join(caminho_base, 'freq_consolidado.csv')
caminho_dados = os.path.join(caminho_base, 'data_consolidado.csv')

# Mapeamento entre códigos de estação
MAPEAMENTO_ESTACOES = {
    'S-01-1': '20160005', # Nome estações e ID
    'S-06-1': '20160004', # Nome estações e ID
    'S-01-2': '20160008', # Nome estações e ID
    'S-07-1': '20160003', # Nome estações e ID
    'S-09-1': '20160007', # Nome estações e ID
    'S-10-1': '20160006' # Nome estações e ID
}

# Carrega os dados com tratamento de erros
try: # Tenta executar o código dentro deste bloco
    df_freq_consolidado = pd.read_csv(caminho_freq) # df_freq_consolidado recebe, a leitura do csv, caminho_freq.
    print("Dados de frequência carregados. Colunas:", df_freq_consolidado.columns.tolist()) # Se der certo, mostra as colunas carregadas
except Exception as erro: # Caso dê erro: 
    print(f"Erro ao carregar freq_consolidado.csv: {erro}") # Mostra qual foi o erro
    df_freq_consolidado = pd.DataFrame() # Cria um DataFrame vazio para evitar que o resto do código quebre

try: # Tente
    df_dados_consolidado = pd.read_csv(caminho_dados) # df_consolidado recebe o caminho lido 
    print("Dados temporais carregados. Colunas:", df_dados_consolidado.columns.tolist()) # Se der certo, mostra as colunas carregadas
except Exception as erro: # Caso dê erro:
    print(f"Erro ao carregar data_consolidado.csv: {erro}") # Me mostra o erro.
    df_dados_consolidado = pd.DataFrame() # Cria um DataFrame vazio para evitar que o resto do código quebre

# Carrega os dados dos eventos
try: # Tente 
    caminho_eventos = os.path.join(caminho_base, "events", "2025", "2025") # abre o caminho json, usando o caminho_base e acessando subpastas 'events','2025','2025' 
    df_eventos = carregar_eventos(caminho_eventos)
    estacoes_unicas = df_eventos["estacao"].unique()
    eventos_unicos = df_eventos["evento"].unique()
    print("Estações carregadas:", estacoes_unicas)
    print("Eventos carregados:", eventos_unicos)
except Exception as erro:
    print(f"Erro ao carregar eventos: {erro}")
    df_eventos = pd.DataFrame()
    estacoes_unicas = []
    eventos_unicos = []

# Função para classificar o evento conforme a lógica explicada
def classificar_evento(evento, df):
    # Filtra os dados apenas para o evento em questão
    dados_evento = df[df["evento"] == evento]
    
    # Conta quantas estações tiveram fator de pico > 10
    estacoes_com_trigger = dados_evento[dados_evento["valor"] > 10]["estacao"].nunique()
    
    # Total de estações que registraram o evento
    total_estacoes = dados_evento["estacao"].nunique()
    
    if total_estacoes == 0:
        return "Sem dados", 0
    
    # Calcula o rácio
    racio = estacoes_com_trigger / total_estacoes
    
    # Classifica conforme os limiares
    if racio < 0.10:
        classificacao = "Ruído"
    elif racio <= 0.75:
        classificacao = "Evento Local"
    else:
        classificacao = "Evento Global"
    
    return classificacao, racio

# Cache para melhorar performance da classificação
@lru_cache(maxsize=None)
def get_classificacao(evento):
    return classificar_evento(evento, df_eventos)[0]

# Função para encontrar os 5 maiores picos em um espectro de frequência
def encontrar_picos(serie_frequencia, serie_amplitude, num_picos=5):
    # Encontra os índices dos picos
    picos_indices = np.argsort(serie_amplitude)[-num_picos:]
    # Ordena por frequência para manter a ordem na tabela
    picos_indices_ordenados = picos_indices[np.argsort(serie_frequencia[picos_indices])]
    # Retorna os pares (frequência, amplitude)
    return [(serie_frequencia[i], serie_amplitude[i]) for i in picos_indices_ordenados]

#--------------------------LAYOUT--------------------------

# Layout da página de relatórios
layout_relatorios = html.Div([
    # Menu flutuante (mantido da versão original)
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
    
    # Componente para download do PDF
    dcc.Download(id="download-pdf"),
    
    #Aqui vai o texto
    html.H3('RELATÓRIO SOS DA BARRAGEM DE DAIVÕES', style={"textAlign": "center", "marginTop": "30px"}),
    #html.H3('SOS DA BARRAGEM DE DAIVÕES', style={"textAlign": "center"}),

    dbc.Tabs(
        id="abas-estacoes",
        active_tab=estacoes_unicas[0] if len(estacoes_unicas) > 0 else None,
        children=[dbc.Tab(label=estacao, tab_id=estacao) for estacao in estacoes_unicas]
    ),
    html.Div(id="conteudo-aba", style={"padding": "20px"})
])

# Layout do aplicativo
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Layout principal com menu lateral e conteúdo
    dbc.Row([
        # Menu Lateral (coluna esquerda) - AGORA FIXO
        dbc.Col([
            html.Div([
                html.H4("Menu Principal", style={"padding": "10px", "borderBottom": "1px solid #ddd", "marginBottom": "10px"}),
                
                # Grupo de opções 1
                html.Div([
                    html.H6("OPÇÕES PRINCIPAIS", style={"color": "#555", "padding": "5px 10px", "marginTop": "15px"}),
                    dbc.Nav([
                        dbc.NavLink("Home", href="/home", active="exact", style={"padding": "8px 15px"}),
                        dbc.NavLink("Relatórios", href="/", active="exact", style={"padding": "8px 15px"}),
                        dbc.NavLink("Mapa Barragem", href="/mapa-barragem", active="exact", style={"padding": "8px 15px"}),
                        
                    ], vertical=True, pills=True),
                ]),
                
                # Grupo de opções 2
                html.Div([
                    html.H6("OUTRAS OPÇÕES", style={"color": "#555", "padding": "5px 10px", "marginTop": "20px"}),
                    dbc.Nav([
                        dbc.NavLink("Opção 4", href="#", style={"padding": "8px 15px"}),
                        dbc.NavLink("Opção 5", href="#", style={"padding": "8px 15px"}),
                    ], vertical=True, pills=True),
                ]),
                
                # Grupo de opções 3
                html.Div([
                    html.H6("OUTRAS OPÇÕES 2", style={"color": "#555", "padding": "5px 10px", "marginTop": "20px"}),
                    dbc.Nav([
                        dbc.NavLink("Opção 6", href="#", style={"padding": "8px 15px"}),
                        dbc.NavLink("Opção 7", href="#", style={"padding": "8px 15px"}),
                    ], vertical=True, pills=True),
                ]),
            ], style={
                "position": "fixed",  # TORNA O MENU FIXO
                "width": "16.666%",    # LARGURA EQUIVALENTE A 2 COLUNAS (12 colunas no total)
                "height": "100vh",     # ALTURA TOTAL DA VIEWPORT
                "overflowY": "auto",   # PERMITE SCROLL INTERNO SE NECESSÁRIO
                "backgroundColor": "#f8f9fa",
                "borderRight": "1px solid #dee2e6",
                "padding": "10px",
                "zIndex": "100"       # GARANTE QUE FIQUE ACIMA DE OUTROS ELEMENTOS
            })
        ], width=2, style={"padding": "0"}),
        
        # Conteúdo principal (coluna direita)
        dbc.Col([
            html.Div(id='page-content')
        ], width=10, style={"marginLeft": "16.666%"})  # ADICIONA MARGEM PARA COMPENSAR O MENU FIXO
    ])
])

# Callback para rolagem suave
@app.callback(
    Output('dummy-div', 'children'),
    [Input("botao-topo", "n_clicks"),
     Input("botao-series", "n_clicks"),
     Input("botao-espectros", "n_clicks")]
)
def scroll_to_section(botao_topo_clicks, botao_series_clicks, botao_espectros_clicks):
    ctx = callback_context
    
    if not ctx.triggered:
        return ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == "botao-topo":
        return dcc.Location(id="scroll-top", href="#topo")
    elif button_id == "botao-series":
        return dcc.Location(id="scroll-series", href="#series-aceleracao")
    elif button_id == "botao-espectros":
        return dcc.Location(id="scroll-espectros", href="#espectros-frequencia")
    
    return ""

# Callback para gerar PDF
@app.callback(
    Output("download-pdf", "data"),
    Input("btn-gerar-pdf", "n_clicks"),
    State("conteudo-aba", "children"),
    State("abas-estacoes", "active_tab"),
    prevent_initial_call=True
)
def gerar_pdf(n_clicks, conteudo_aba, estacao_selecionada):
    if n_clicks is None:
        raise PreventUpdate
    
    # Cria um nome de arquivo baseado na estação
    nome_arquivo = f"relatorio_{estacao_selecionada}.pdf"
    
    # Cria um HTML temporário com o conteúdo do relatório
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Sísmico - Estação {estacao_selecionada}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3, h4, h5 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .section {{ margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Relatório de Registros Sísmicos</h1>
            <h2>MONITORAMENTO DA BARRAGEM</h2>
            <h2>RELATÓRIO SÍSMICO</h2>
            <h3>Estação: {estacao_selecionada}</h3>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
    """
    
    # Adiciona o conteúdo principal (simplificado para o PDF)
    html_content += """
    <div class="content">
        <p>Relatório gerado a partir do sistema de monitoramento sísmico.</p>
        <p>Para visualizar o relatório completo com gráficos interativos, acesse o sistema.</p>
    </div>
    """
    
    html_content += "</body></html>"
    
    # Configurações para o PDF
    options = {
        'encoding': 'UTF-8',
        'page-size': 'A4',
        'margin-top': '15mm',
        'margin-right': '15mm',
        'margin-bottom': '15mm',
        'margin-left': '15mm',
        'quiet': ''
    }
    
    # Gera o PDF em um arquivo temporário
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        try:
            pdfkit.from_string(html_content, tmp_file.name, options=options)
            return dcc.send_file(tmp_file.name, filename=nome_arquivo)
        except Exception as e:
            print(f"Erro ao gerar PDF: {e}")
            return no_update

# Callback principal
@app.callback(
    Output("conteudo-aba", "children"),
    [Input("abas-estacoes", "active_tab")]
)
def mostrar_conteudo_estacao(estacao_selecionada):
    if estacao_selecionada is None:
        return html.P("Nenhuma estação selecionada.")

    # Filtra os dados da estação selecionada
    dados_estacao = df_eventos[df_eventos["estacao"] == estacao_selecionada].copy()
    
    if dados_estacao.empty:
        return html.P("Sem dados para esta estação.")

    trigger = dados_estacao["trigger"].iloc[0]
    evento_atual = dados_estacao["evento"].iloc[0]
    
    # Classifica o evento corretamente
    classificacao, racio = classificar_evento(evento_atual, df_eventos)
    
    # Processamento dos dados
    estacoes_ativas = df_eventos[df_eventos["evento"] == evento_atual]["estacao"].unique()
    
    estacoes_com_evento = df_eventos[
        (df_eventos["evento"] == evento_atual) & 
        (df_eventos["valor"] > 10)
    ]["estacao"].unique()
    
    # Dados de aceleração máxima
    pico_maximo = dados_estacao.loc[dados_estacao["peak"].idxmax()]
    aceleracao_maxima = {
        "estacao": pico_maximo["estacao"],
        "direcao": pico_maximo["direcao"],
        "magnitude": f"{pico_maximo['peak']:.3f}".replace(".", ",") + " mg",
        "fator_pico": f"{pico_maximo['valor']:.3f}".replace(".", ",") + " mg/mg"
    }

    # Tabelas de picos e fatores
    dados_agrupados = dados_estacao.groupby("direcao").agg({"peak": "max", "valor": "max"}).reindex(["T", "R", "V"])

    # Gráficos de séries temporais
    if not df_dados_consolidado.empty:
        codigo_estacao = MAPEAMENTO_ESTACOES.get(estacao_selecionada, '')
        
        if codigo_estacao:
            df_dados_consolidado['estacao'] = df_dados_consolidado['estacao'].astype(str).str.strip()
            df_dados_consolidado['evento'] = df_dados_consolidado['evento'].astype(str).str.strip()
            
            series_filtradas = df_dados_consolidado[
                (df_dados_consolidado["estacao"] == codigo_estacao) & 
                (df_dados_consolidado["evento"] == str(evento_atual).strip())
            ]
            
            if series_filtradas.empty:
                graficos_series = html.Div([
                    html.P("Dados temporais não encontrados para:"),
                    html.P(f"Estação: {estacao_selecionada} (Código: {codigo_estacao})"),
                    html.P(f"Evento: {evento_atual}"),
                    html.P(f"Valores encontrados em dados_consolidado:"),
                    html.P(f"Estações: {df_dados_consolidado['estacao'].unique()}"),
                    html.P(f"Eventos: {df_dados_consolidado['evento'].unique()}")
                ])
            else:
                y_min = min(series_filtradas["T"].min(), 
                           series_filtradas["R"].min(), 
                           series_filtradas["V"].min()) * 1.1
                y_max = max(series_filtradas["T"].max(), 
                           series_filtradas["R"].max(), 
                           series_filtradas["V"].max()) * 1.1
                
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
                        title=f"Série Temporal - Direção {direcao} (Evento: {evento_atual})",
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
            graficos_series = html.P(f"Não foi encontrado mapeamento para a estação {estacao_selecionada}")
    else:
        graficos_series = html.P("Dados temporais não carregados.")

    # Gráficos de espectros de frequência
    if not df_freq_consolidado.empty:
        codigo_estacao = MAPEAMENTO_ESTACOES.get(estacao_selecionada, '')
        
        if codigo_estacao:
            df_freq_consolidado['estacao'] = df_freq_consolidado['estacao'].astype(str).str.strip()
            df_freq_consolidado['evento'] = df_freq_consolidado['evento'].astype(str).str.strip()
            
            freq_filtradas = df_freq_consolidado[
                (df_freq_consolidado["estacao"] == codigo_estacao) & 
                (df_freq_consolidado["evento"] == str(evento_atual).strip())
            ]
            
            if freq_filtradas.empty:
                graficos_freq = html.Div([
                    html.P("Dados de frequência não encontrados para:"),
                    html.P(f"Estação: {estacao_selecionada} (Código: {codigo_estacao})"),
                    html.P(f"Evento: {evento_atual}"),
                    html.P(f"Valores encontrados em freq_consolidado:"),
                    html.P(f"Estações: {df_freq_consolidado['estacao'].unique()}"),
                    html.P(f"Eventos: {df_freq_consolidado['evento'].unique()}")
                ])
            else:
                y_min_freq = 0
                y_max_freq = max(freq_filtradas["T"].max(), 
                                freq_filtradas["R"].max(), 
                                freq_filtradas["V"].max()) * 1.1
                
                def criar_grafico_freq(direcao):
                    # Encontra os 5 maiores picos para a direção atual
                    picos = encontrar_picos(
                        freq_filtradas["Freq."].values,
                        freq_filtradas[direcao].values
                    )
                    
                    figura = go.Figure()
                    figura.add_trace(go.Scatter(
                        x=freq_filtradas["Freq."],
                        y=freq_filtradas[direcao],
                        mode='lines',
                        line=dict(color='black', width=1),
                        name=direcao
                    ))
                    
                    # Adiciona marcadores para os picos
                    for i, (freq, ampl) in enumerate(picos, 1):
                        figura.add_trace(go.Scatter(
                            x=[freq],
                            y=[ampl],
                            mode='markers+text',
                            marker=dict(size=10, color='red'),
                            text=f"{i}",
                            textposition="top center",
                            showlegend=False
                        ))
                    
                    figura.update_layout(
                        title=f"Espectro de Frequência - FFT Direção  {direcao} (Evento: {evento_atual})",
                        xaxis_title="Frequência (Hz)",
                        yaxis_title="Aceleração (mg)",
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=300,
                        plot_bgcolor='white',
                        yaxis=dict(range=[y_min_freq, y_max_freq])
                    )
                    return dcc.Graph(figure=figura, style={'margin-bottom': '20px'})
                
                # Cria a tabela de máximos de frequência
                tabela_maximos = []
                for direcao in ['T', 'R', 'V']:
                    picos = encontrar_picos(
                        freq_filtradas["Freq."].values,
                        freq_filtradas[direcao].values
                    )
                    # Extrai apenas as frequências (ignora as amplitudes)
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
                    dbc.Table.from_dataframe(
                        df_tabela_maximos,
                        striped=True,
                        bordered=True,
                        hover=True,
                        style={
                            'width': '80%',
                            'margin-left': 'auto',
                            'margin-right': 'auto',
                            'margin-bottom': '30px'
                        }
                    ),
                    criar_grafico_freq("T"),
                    criar_grafico_freq("R"),
                    criar_grafico_freq("V")
                ])
        else:
            graficos_freq = html.P(f"Não foi encontrado mapeamento para a estação {estacao_selecionada}")
    else:
        graficos_freq = html.P("Dados de frequência não carregados.")

    # Layout da página
    return html.Div([
        
        
        #html.H4(f"Estação: {estacao_selecionada}", style={"textAlign": "center"}),
        #html.P(f"Trigger: {trigger}", style={"textAlign": "center"}),
        #html.P(f"Evento selecionado: {evento_atual}", style={"textAlign": "center", "fontWeight": "bold"}),

        html.Div([
            #html.H5('Resumo', style={"fontWeight": "bold", "marginTop": "20px"}),
            # html.Div([ # Resumo do relatório
            #     html.P(f"Data/Hora do Evento: {trigger.split('T')[0]}, {trigger.split('T')[1][:8]}"),
            #     html.P(f"Processado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"),
            #     html.P(f"Estações que registraram o evento: {', '.join(estacoes_ativas)}"),
            #     html.P(f"Estações com fator de pico > 10: {', '.join(estacoes_com_evento) if len(estacoes_com_evento) > 0 else 'Nenhuma'}"),
            #     html.P(f"Classificação: {classificacao}"),
            #     html.P(f"Rácio: {racio:.2f}".replace(".", ",")),
            # ], style={"marginLeft": "15px"}),
            
            html.H5("Aceleração Máxima:", style={"fontWeight": "bold", "marginTop": "15px"}),
            dbc.Table([
                html.Tbody([
                    html.Tr([html.Td("Estação:"), html.Td(aceleracao_maxima['estacao'])]),
                    html.Tr([html.Td("Direção:"), html.Td(aceleracao_maxima['direcao'])]),
                    html.Tr([html.Td("Magnitude:"), html.Td(aceleracao_maxima['magnitude'])]),
                    html.Tr([html.Td("Fator de Pico:"), html.Td(aceleracao_maxima['fator_pico'])])
                ])
            ], style={"marginBottom": "20px"})
        ], style={"marginLeft": "15px"}),

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

# ------------- Navegar entre as paginas do menu lateral. -----------------------

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def render_page_content(pathname):
    if pathname == "/mapa-barragem":
        return layout_mapa_barragem
    elif pathname == "/home":
        return layout_home
    else:
        return layout_relatorios
    
# Para a Pagina de Mapa_barragem.py
register_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True)