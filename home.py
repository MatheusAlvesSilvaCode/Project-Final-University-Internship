from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate
import pandas as pd
import os

# Layout principal da página Home
layout = html.Div([
    # Filtro por Tipo de Evento
    dbc.Card([
        dbc.CardHeader("Filtrar por Tipo de Evento", style={"fontWeight": "bold"}),
        dbc.CardBody([
            dbc.Checklist(
                id='event-type-filter',
                options=[
                    {'label': 'Todos', 'value': 'all'},
                    {'label': 'Eventos Globais', 'value': 'global'},
                    {'label': 'Eventos Locais', 'value': 'local'},
                    {'label': 'Ruídos', 'value': 'noise'}
                ],
                value=['all'],
                inline=True
            )
        ])
    ], className='mt-4 mb-4'),
    
    # Filtro por Período
    dbc.Card([
        dbc.CardHeader("Filtrar por Período", style={"fontWeight": "bold"}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Selecione o período:"),
                    dcc.DatePickerRange(
                        id='date-picker-range',
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
                        id='quick-date-filter',
                        options=[
                            {'label': 'Hoje', 'value': 'today'},
                            {'label': 'Esta Semana', 'value': 'week'},
                            {'label': 'Este Mês', 'value': 'month'},
                            {'label': 'Este Ano', 'value': 'year'},
                            {'label': 'Personalizado', 'value': 'custom'}
                        ],
                        value='month',
                        inline=True
                    )
                ], md=6)
            ])
        ])
    ], className='mb-4'),
    
    # Prévia dos Eventos
    dbc.Card([
        dbc.CardHeader("Prévia dos Eventos", style={"fontWeight": "bold"}),
        dbc.CardBody([
            html.Div(id='event-preview', style={
                'maxHeight': '300px',
                'overflowY': 'auto',
                'padding': '10px',
                'border': '1px solid #eee',
                'borderRadius': '5px'
            })
        ])
    ], className='mb-4'),
    
    # Botão para aplicar filtros e redirecionar
    dbc.Button(
        "Buscar Eventos",
        id='apply-filters-button',
        color='primary',
        className='mb-4',
        n_clicks=0
    ),
    
    # Componente para redirecionamento
    dcc.Location(id='redirect-to-reports', refresh=True),
    
    # Armazenar os filtros selecionados
    dcc.Store(id='filters-store'),
    
    # Armazenar dados dos eventos para prévia
    dcc.Store(id='events-data')
])

# Callbacks para a página Home
def register_callbacks(app):
    @app.callback(
        Output('redirect-to-reports', 'pathname'),
        Output('filters-store', 'data'),
        Input('apply-filters-button', 'n_clicks'),
        State('event-type-filter', 'value'),
        State('date-picker-range', 'start_date'),
        State('date-picker-range', 'end_date'),
        prevent_initial_call=True
    )
    def apply_filters_and_redirect(n_clicks, event_types, start_date, end_date):
        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
        
        # Armazena os filtros selecionados
        filters = {
            'event_types': event_types,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Redireciona para a página de relatórios
        return '/', filters
    
    @app.callback(
        Output('date-picker-range', 'start_date'),
        Output('date-picker-range', 'end_date'),
        Input('quick-date-filter', 'value')
    )
    def update_date_range(quick_filter):
        today = datetime.now()
        
        if quick_filter == 'today':
            return today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        elif quick_filter == 'week':
            start = today - timedelta(days=today.weekday())
            return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        elif quick_filter == 'month':
            start = today.replace(day=1)
            return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        elif quick_filter == 'year':
            start = today.replace(month=1, day=1)
            return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')
        else:
            return no_update, no_update
    
    @app.callback(
        Output('event-preview', 'children'),
        Output('events-data', 'data'),
        Input('event-type-filter', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date'),
        State('events-data', 'data')  # Manter o estado dos dados existentes
    )
    def update_event_preview(event_types, start_date, end_date, existing_data):
        # Carrega os dados reais dos eventos
        try:
            caminho_base = r'C:\Users\mathe\Desktop\Estágio\Final'
            caminho_eventos = os.path.join(caminho_base, "events", "2025", "2025")
            from consolidate_events import carregar_eventos
            df_eventos = carregar_eventos(caminho_eventos)
            
            # Converte trigger para datetime
            df_eventos['data_hora'] = pd.to_datetime(df_eventos['trigger'])
            
            # Filtra por data
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date) + timedelta(days=1)  # Para incluir todo o dia final
            df_filtrado = df_eventos[(df_eventos['data_hora'] >= start_date) & 
                                   (df_eventos['data_hora'] <= end_date)].copy()
            
            # Classifica os eventos
            def get_classification(evento):
                classificacao, _ = classificar_evento(evento, df_eventos)
                return classificacao
                
            df_filtrado['classificacao'] = df_filtrado['evento'].apply(get_classification)
            
            # Filtra por tipo de evento
            if 'all' not in event_types:
                type_mapping = {
                    'global': 'Evento Global',
                    'local': 'Evento Local',
                    'noise': 'Ruído'
                }
                selected_types = [type_mapping[t] for t in event_types]
                df_filtrado = df_filtrado[df_filtrado['classificacao'].isin(selected_types)]
            
            # Prepara os dados para exibição
            eventos_para_exibicao = []
            for _, row in df_filtrado.iterrows():
                eventos_para_exibicao.append({
                    'date': row['data_hora'].strftime('%d/%m/%Y %H:%M'),
                    'type': row['classificacao'].lower().replace(' ', '_'),
                    'classification': row['classificacao'],
                    'estacao': row['estacao'],
                    'evento': row['evento']
                })
            
            # Cria os itens de pré-visualização
            preview_items = [
                html.Div(
                    f"{event['date']} - {event['classification']} (Estação: {event['estacao']}, Evento: {event['evento']})",
                    style={
                        'padding': '8px',
                        'marginBottom': '5px',
                        'borderBottom': '1px solid #eee',
                        'fontSize': '14px'
                    }
                )
                for event in eventos_para_exibicao
            ]
            
            if not preview_items:
                preview_items = [html.Div("Nenhum evento encontrado com os filtros selecionados")]
            
            return preview_items, eventos_para_exibicao
            
        except Exception as e:
            print(f"Erro ao carregar eventos: {e}")
            return [html.Div("Erro ao carregar dados dos eventos")], None

# Função auxiliar para classificar eventos (copiada do main.py)
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