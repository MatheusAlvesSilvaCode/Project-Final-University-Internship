from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate
import pandas as pd
import os
import json
from functools import lru_cache

# Layout principal (mantido exatamente igual)
layout = html.Div([
    dbc.Card([
        dbc.CardHeader("Filtrar por Tipo de Evento", style={"fontWeight": "bold"}),
        dbc.CardBody([
            dbc.Checklist(
                id='filtro-tipo-evento',
                options=[
                    {'label': 'Todos', 'value': 'todos'},
                    {'label': 'Eventos Globais', 'value': 'global'},
                    {'label': 'Eventos Locais', 'value': 'local'},
                    {'label': 'Ruídos', 'value': 'ruido'}
                ],
                value=['todos'],
                inline=True
            )
        ])
    ], className='mt-4 mb-4'),
    
    dbc.Card([
        dbc.CardHeader("Filtrar por Período", style={"fontWeight": "bold"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Selecione o período:"),
                    dcc.DatePickerRange(
                        id='seletor-data',
                        min_date_allowed=datetime(2020, 1, 1),
                        max_date_allowed=datetime(2025, 12, 31),
                        initial_visible_month=datetime.now(),
                        start_date=datetime.now().replace(day=1),
                        end_date=datetime.now(),
                        display_format='DD/MM/YYYY',
                        month_format='MMMM YYYY',
                        style={
                            'width': '100%',
                            'border': '1px solid #ddd',
                            'borderRadius': '5px',
                            'padding': '10px',
                            'backgroundColor': '#f8f9fa'
                        }
                    )
                ], md=6),
                dbc.Col([
                    dbc.Label("Filtro Rápido:"),
                    dbc.RadioItems(
                        id='filtro-rapido-data',
                        options=[
                            {'label': 'Hoje', 'value': 'hoje'},
                            {'label': 'Esta Semana', 'value': 'semana'},
                            {'label': 'Este Mês', 'value': 'mes'},
                            {'label': 'Este Ano', 'value': 'ano'},
                            {'label': 'Personalizado', 'value': 'personalizado'}
                        ],
                        value='mes',
                        inline=True
                    )
                ], md=6)
            ])
        ])
    ], className='mb-4'),
    
    dbc.Card([
        dbc.CardHeader("Prévia dos Eventos", style={"fontWeight": "bold"}),
        dbc.CardBody([
            html.Div(id='previa-eventos', style={
                'maxHeight': '400px',
                'overflowY': 'auto',
                'padding': '10px',
                'border': '1px solid #eee',
                'borderRadius': '5px'
            })
        ])
    ], className='mb-4'),
    
    dbc.Button(
        "Buscar Eventos",
        id='botao-buscar-eventos',
        color='primary',
        className='mb-4',
        n_clicks=0
    ),
    
    dcc.Location(id='redirecionar-relatorios', refresh=True),
    dcc.Store(id='armazenar-filtros'),
    dcc.Store(id='armazenar-dados-eventos')
])

def registrar_callbacks(app):
    @app.callback(
        Output('redirecionar-relatorios', 'pathname'),
        Output('armazenar-filtros', 'data'),
        Input('botao-buscar-eventos', 'n_clicks'),
        State('filtro-tipo-evento', 'value'),
        State('seletor-data', 'start_date'),
        State('seletor-data', 'end_date'),
        prevent_initial_call=True
    )
    def aplicar_filtros_redirecionar(n_clicks, tipos_evento, data_inicio, data_fim):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
        
        return '/reports', {
            'tipos_evento': tipos_evento,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }

    @app.callback(
        Output('seletor-data', 'start_date'),
        Output('seletor-data', 'end_date'),
        Input('filtro-rapido-data', 'value')
    )
    def atualizar_periodo(filtro_rapido):
        hoje = datetime.now()
        
        if filtro_rapido == 'hoje':
            return hoje.strftime('%Y-%m-%d'), hoje.strftime('%Y-%m-%d')
        elif filtro_rapido == 'semana':
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            return inicio_semana.strftime('%Y-%m-%d'), hoje.strftime('%Y-%m-%d')
        elif filtro_rapido == 'mes':
            inicio_mes = hoje.replace(day=1)
            return inicio_mes.strftime('%Y-%m-%d'), hoje.strftime('%Y-%m-%d')
        elif filtro_rapido == 'ano':
            inicio_ano = hoje.replace(month=1, day=1)
            return inicio_ano.strftime('%Y-%m-%d'), hoje.strftime('%Y-%m-%d')
        return None, None

    @app.callback(
        Output('previa-eventos', 'children'),
        Output('armazenar-dados-eventos', 'data'),
        Input('filtro-tipo-evento', 'value'),
        Input('seletor-data', 'start_date'),
        Input('seletor-data', 'end_date'),
        prevent_initial_call=True
    )
    def atualizar_previa_eventos(tipos_evento, data_inicio, data_fim):
        try:
            base_path = r'C:\Users\mathe\Desktop\Estágio\Final\events\2025'
            eventos = []
            
            # Percorre todos os subdiretórios para encontrar os JSONs
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(root, file), 'r') as f:
                                data = json.load(f)
                                event_id = file.replace('.json', '')
                                
                                # Processa cada estação no arquivo JSON
                                for station, info in data.get('eventFiles', {}).items():
                                    try:
                                        trigger_time = pd.to_datetime(info.get('triggerStart'))
                                        peak_value = max([ch.get('value', 0) for ch in info.get('df', {}).get('cf', [])])
                                        
                                        eventos.append({
                                            'evento': event_id,
                                            'estacao': station,
                                            'data_hora': trigger_time,
                                            'valor': peak_value,
                                            'trigger': info.get('triggerStart', '')
                                        })
                                    except Exception as e:
                                        print(f"Erro ao processar estação {station} no arquivo {file}: {str(e)}")
                        except Exception as e:
                            print(f"Erro ao ler arquivo {file}: {str(e)}")
            
            if not eventos:
                return [html.Div("Nenhum evento encontrado nos arquivos JSON")], None
            
            df_eventos = pd.DataFrame(eventos)
            
            # Processamento das datas
            data_inicio = pd.to_datetime(data_inicio)
            data_fim = pd.to_datetime(data_fim) + timedelta(days=1)
            
            df_filtrado = df_eventos[
                (df_eventos['data_hora'] >= data_inicio) & 
                (df_eventos['data_hora'] <= data_fim)
            ].copy()
            
            # Pré-processamento para classificação
            df_classificacao = df_filtrado.groupby('evento').agg({
                'estacao': 'nunique',
                'valor': lambda x: (x > 10).sum()
            }).reset_index()
            
            # Aplicar classificação
            df_classificacao['classificacao'] = df_classificacao.apply(
                lambda x: classificar_evento(x['valor'], x['estacao']), axis=1)
            
            # Juntar a classificação ao DataFrame principal
            df_filtrado = df_filtrado.merge(
                df_classificacao[['evento', 'classificacao']],
                on='evento',
                how='left'
            )
            
            # Filtro por tipo de evento
            if 'todos' not in tipos_evento:
                mapeamento_tipos = {
                    'global': 'Evento Global',
                    'local': 'Evento Local',
                    'ruido': 'Ruído'
                }
                tipos_selecionados = [mapeamento_tipos[t] for t in tipos_evento if t in mapeamento_tipos]
                df_filtrado = df_filtrado[df_filtrado['classificacao'].isin(tipos_selecionados)]
            
            # Agrupamento e ordenação
            eventos_agrupados = df_filtrado.groupby('evento').agg({
                'data_hora': 'first',
                'classificacao': 'first',
                'estacao': lambda x: ', '.join(sorted(set(x))),
                'valor': 'max',
                'trigger': 'first'
            }).reset_index().sort_values('data_hora', ascending=False)
            
            # Criação dos cards de pré-visualização
            itens_previa = []
            for _, linha in eventos_agrupados.iterrows():
                cor = {
                    'Evento Global': '#dc3545',
                    'Evento Local': '#fd7e14',
                    'Ruído': '#6c757d'
                }.get(linha['classificacao'], '#6c757d')
                
                item = dbc.Card(
                    [
                        dbc.CardHeader(
                            html.Div([
                                html.Span(
                                    linha['data_hora'].strftime('%d/%m/%Y %H:%M:%S'),
                                    style={"fontWeight": "bold", "marginRight": "10px"}
                                ),
                                dbc.Badge(
                                    linha['classificacao'],
                                    color={
                                        'Evento Global': 'danger',
                                        'Evento Local': 'warning',
                                        'Ruído': 'secondary'
                                    }.get(linha['classificacao'], 'secondary'),
                                    className="me-1"
                                )
                            ], style={"display": "flex", "alignItems": "center"})
                        ),
                        dbc.CardBody([
                            html.P([
                                html.Strong("Evento: "),
                                linha['evento']
                            ]),
                            html.P([
                                html.Strong("Estações: "),
                                linha['estacao']
                            ]),
                            html.P([
                                html.Strong("Pico: "),
                                f"{linha['valor']:.2f}",
                                html.Span(" m/s²", style={"color": "#6c757d"})
                            ]),
                            html.P([
                                html.Small(linha['trigger'], style={"color": "#6c757d"})
                            ])
                        ])
                    ],
                    style={
                        'marginBottom': '10px',
                        'borderLeft': f'4px solid {cor}'
                    }
                )
                itens_previa.append(item)
            
            if not itens_previa:
                return [html.Div("Nenhum evento encontrado com os critérios selecionados")], None
            
            return itens_previa, eventos_agrupados.to_dict('records')
            
        except Exception as erro:
            print(f"Erro ao processar eventos: {str(erro)}")
            return [html.Div("Erro ao carregar dados dos eventos")], None

@lru_cache(maxsize=None)
def classificar_evento(estacoes_acionadas, total_estacoes):
    try:
        if total_estacoes == 0:
            return "Sem dados"
        
        proporcao = estacoes_acionadas / total_estacoes
        
        if proporcao < 0.10:
            classificacao = "Ruído"
        elif proporcao <= 0.75:
            classificacao = "Evento Local"
        else:
            classificacao = "Evento Global"
        
        return classificacao
    except Exception as erro:
        print(f"Erro na classificação: {str(erro)}")
        return "Não classificado"