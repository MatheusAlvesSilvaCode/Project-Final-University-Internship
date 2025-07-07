from dash import html, dcc, Input, Output, State, callback, ALL, callback_context, no_update
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate
import pandas as pd
import os
import json
from functools import lru_cache
import numpy as np
import dash
from utils import classificar_evento

# Layout principal
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
                        initial_visible_month=datetime.now().strftime('%Y-%m-%d'),
                        start_date=datetime.now().replace(day=1).strftime('%Y-%m-%d'),
                        end_date=datetime.now().strftime('%Y-%m-%d'),
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

def serializar_evento(evento):
    # Garante que todos os campos são serializáveis
    return {
        k: (str(v) if isinstance(v, (pd.Timestamp, datetime)) else v)
        for k, v in evento.items()
    }

def registrar_callbacks(app):
    @app.callback(
        Output('armazenar-filtros', 'data'),
        Output('event-data-store', 'data'),
        Output('selected-event-store', 'data'),
        Input('botao-buscar-eventos', 'n_clicks'),
        Input({'type': 'card-previa-evento', 'index': ALL}, 'n_clicks_timestamp'),
        State('filtro-tipo-evento', 'value'),
        State('seletor-data', 'start_date'),
        State('seletor-data', 'end_date'),
        State('armazenar-dados-eventos', 'data'),
        prevent_initial_call=True
    )
    def redirecionar_e_selecionar(n_clicks_buscar, n_clicks_previas_ts, tipos_evento, data_inicio, data_fim, eventos_filtrados):
        ctx = callback_context
        print('DEBUG callback trigger:', ctx.triggered)
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id']
        # Se foi o botão de buscar eventos
        if trigger_id == 'botao-buscar-eventos.n_clicks':
            return (
                {
                    'tipos_evento': tipos_evento,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim
                },
                eventos_filtrados if eventos_filtrados else [],
                no_update
            )
        # Se foi um card de prévia clicado
        if 'card-previa-evento' in trigger_id:
            if not eventos_filtrados:
                raise PreventUpdate
            idx = None
            print('DEBUG n_clicks_previas_ts:', n_clicks_previas_ts)
            print('DEBUG eventos_filtrados:', eventos_filtrados)
            if n_clicks_previas_ts and any(n_clicks_previas_ts):
                max_ts = max([ts if ts is not None else 0 for ts in n_clicks_previas_ts])
                if max_ts > 0:
                    idx = n_clicks_previas_ts.index(max_ts)
            print('DEBUG idx:', idx)
            if idx is not None and eventos_filtrados:
                evento_id = ctx.inputs_list[1][idx]['id']['index']
                print('DEBUG evento_id:', evento_id)
                evento = next(
                    (e for e in eventos_filtrados 
                     if str(e.get('evento', '')) == str(evento_id)),
                    None
                )
                print('DEBUG evento selecionado:', evento)
                if evento:
                    estacoes = evento.get('estacao', '')
                    if isinstance(estacoes, str):
                        if ',' in estacoes:
                            estacoes = [e.strip() for e in estacoes.split(',')]
                        else:
                            estacoes = [estacoes.strip()]
                    elif not isinstance(estacoes, list):
                        estacoes = [str(estacoes)]
                    evento['estacao'] = estacoes
                    evento_serializado = serializar_evento(evento)
                    return (
                        no_update,
                        eventos_filtrados,
                        evento_serializado
                    )
        raise PreventUpdate

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
                                        print(f"Erro ao processar evento {event_id} estação {station}: {e}")
                        except Exception as e:
                            print(f"Erro ao ler arquivo {file}: {e}")
            
            print(f"Total de eventos carregados: {len(eventos)}")
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
            if isinstance(df_classificacao, pd.DataFrame) and not df_classificacao.empty:
                df_classificacao['classificacao'] = df_classificacao['evento'].apply(lambda evento: classificar_evento(evento, df_filtrado)[0])
                df_filtrado = df_filtrado.merge(
                    df_classificacao[['evento', 'classificacao']],
                    on='evento',
                    how='left'
                )
            else:
                df_filtrado['classificacao'] = ''
            # Antes de usar .isin e .groupby, converta para DataFrame se necessário
            if not isinstance(df_filtrado, pd.DataFrame):
                df_filtrado = pd.DataFrame(df_filtrado)
            # Filtro por tipo de evento
            if 'todos' not in tipos_evento:
                mapeamento_tipos = {
                    'global': 'Evento Global',
                    'local': 'Evento Local',
                    'ruido': 'Ruído'
                }
                tipos_selecionados = [mapeamento_tipos[t] for t in tipos_evento if t in mapeamento_tipos]
                if hasattr(df_filtrado, 'isin'):
                    df_filtrado = df_filtrado[df_filtrado['classificacao'].isin(tipos_selecionados)]
            # Agrupamento e ordenação
            if not isinstance(df_filtrado, pd.DataFrame):
                df_filtrado = pd.DataFrame(df_filtrado)
            eventos_agrupados = df_filtrado.groupby('evento').agg({
                'data_hora': 'first',
                'classificacao': 'first',
                'estacao': lambda x: ', '.join(sorted(set(x))),
                'valor': 'max',
                'trigger': 'first'
            }).reset_index().sort_values('data_hora', ascending=False)
            if not isinstance(eventos_agrupados, pd.DataFrame):
                eventos_agrupados = pd.DataFrame(eventos_agrupados)
            # Função auxiliar para garantir string escalar
            def to_scalar(val):
                if isinstance(val, pd.Series) and len(val) == 1:
                    return val.item()
                if isinstance(val, (pd.Index, np.ndarray, list, tuple, set)):
                    return ', '.join(map(str, list(val)))
                return str(val)
            # Criação dos cards de pré-visualização
            itens_previa = []
            for _, linha in eventos_agrupados.iterrows():
                cor = {
                    'Evento Global': '#dc3545',
                    'Evento Local': '#fd7e14',
                    'Ruído': '#6c757d'
                }.get(to_scalar(linha['classificacao']), '#6c757d')
                try:
                    data_hora_str = pd.to_datetime(to_scalar(linha['data_hora'])).strftime('%d/%m/%Y %H:%M:%S')
                except Exception:
                    data_hora_str = to_scalar(linha['data_hora'])
                evento_str = to_scalar(linha['evento'])
                estacao_str = to_scalar(linha['estacao'])
                classificacao_str = to_scalar(linha['classificacao'])
                valor_str = to_scalar(linha['valor'])
                trigger_str = to_scalar(linha['trigger'])
                item = html.Div(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.Div([
                                    html.Span(
                                        data_hora_str,
                                        style={"fontWeight": "bold", "marginRight": "10px"}
                                    ),
                                    dbc.Badge(
                                        classificacao_str,
                                        color={
                                            'Evento Global': 'danger',
                                            'Evento Local': 'warning',
                                            'Ruído': 'secondary'
                                        }.get(classificacao_str, 'secondary'),
                                        className="me-1"
                                    )
                                ], style={"display": "flex", "alignItems": "center"})
                            ),
                            dbc.CardBody([
                                html.P("Evento: " + evento_str),
                                html.P("Estações: " + estacao_str),
                                html.P("Pico: " + valor_str + " m/s²"),
                                html.P(trigger_str),
                            ])
                        ],
                        style={
                            'marginBottom': '10px',
                            'borderLeft': f'4px solid {cor}'
                        }
                    ),
                    id={"type": "card-previa-evento", "index": evento_str},
                    style={'cursor': 'pointer'}
                )
                itens_previa.append(item)
            if not itens_previa:
                return [html.Div("Nenhum evento encontrado com os critérios selecionados")], None
            if not isinstance(df_filtrado, pd.DataFrame):
                df_filtrado = pd.DataFrame(df_filtrado)
            return itens_previa, df_filtrado.to_dict('records')
        except Exception as erro:
            print(f"Erro ao processar eventos: {str(erro)}")
            return [html.Div("Erro ao carregar dados dos eventos")], None
