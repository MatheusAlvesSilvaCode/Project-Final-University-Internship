from dash import html, dcc, Input, Output, callback, callback_context, no_update
import base64
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import html, dcc, Input, Output, callback, callback_context, no_update, State

# Carrega a imagem SVG como base64
with open("assets/SOS-Daivoes.svg", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

# Coordenadas em porcentagem da largura/altura da imagem
station_coords = {
    "S-01-1": {"x": 51.68, "y": 45.98, "radius": 7},
    "S-07-1": {"x": 69.5, "y": 40.2, "radius": 7},
    "S-09-1": {"x": 76.0, "y": 57.8, "radius": 7},
    "S-01-02": {"x": 51.7, "y": 74.0, "radius": 7},
    "S-10-01": {"x": 22.8, "y": 58.0, "radius": 7},
    "S-06-1": {"x": 33.3, "y": 40.1, "radius": 7}
}

layout = html.Div([
    html.H1("Mapa da Barragem", style={"text-align": "center", "marginTop": "30px"}),
    html.H2("SOS Daivões", style={"text-align": "center"}),
    
    # Container responsivo
    html.Div(
        style={
            "position": "relative",
            "width": "100%",
            "height": "0",
            "paddingBottom": "60%",
            "overflow": "hidden"
        },
        children=[
            html.Img(
                src=f"data:image/svg+xml;base64,{encoded_image}",
                style={
                    "position": "absolute",
                    "width": "100%",
                    "height": "100%",
                    "objectFit": "contain"
                }
            ),
            *[
                html.Div(
                    id=f"station-{station_id}",
                    style={
                        "position": "absolute",
                        "left": f"{coords['x']}%",
                        "top": f"{coords['y']}%",
                        "width": f"{coords['radius']}%",
                        "height": f"{coords['radius']}%",
                        "transform": "translate(-50%, -50%)",
                        "borderRadius": "50%",
                        "cursor": "pointer",
                        "zIndex": "1000",
                        "opacity": "0"
                    }
                )
                for station_id, coords in station_coords.items()
            ]
        ]
    ),
    
    # Filtro de calendário
    
    
    html.Div(id='station-info', style={"margin": "30px", "text-align": "center"}),
    html.Div(id='filtered-data-output', style={"margin": "20px"})
])

def register_callbacks(app):
    @app.callback(
        Output('station-info', 'children'),
        [Input(f'station-{station_id}', 'n_clicks') for station_id in station_coords.keys()],
        prevent_initial_call=True
    )
    def show_station_info(*args):
        ctx = callback_context
        if not ctx.triggered:
            return "Clique em uma estação no mapa para ver informações."
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        station_id = triggered_id.replace('station-', '')
        
        station_data = {
            "S-01-1": {"name": "Estação S-01-1", "description": "Descrição da estação S-01-1"},
            "S-07-1": {"name": "Estação S-07-1", "description": "Descrição da estação S-07-1"},
            "S-09-1": {"name": "Estação S-09-1", "description": "Descrição da estação S-09-1"},
            "S-01-2": {"name": "Estação S-01-2", "description": "Descrição da estação S-01-2"},
            "S-10-01": {"name": "Estação S-10-01", "description": "Descrição da estação S-10-01"},
            "S-06-1": {"name": "Estação S-06-1", "description": "Descrição da estação S-06-1"},
        }
        
        data = station_data.get(station_id, {"name": station_id, "description": "Sem informações adicionais"})
        
        return html.Div([
            html.H3(f"{data['name']}"),
            html.P(data['description']),
            html.P("Você pode adicionar gráficos, tabelas ou outras informações aqui.")
        ])

    @app.callback(
        [Output('date-picker-range', 'start_date'),
         Output('date-picker-range', 'end_date')],
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
        Output('filtered-data-output', 'children'),
        Input('apply-date-filter', 'n_clicks'),
        [State('date-picker-range', 'start_date'),
         State('date-picker-range', 'end_date')],
        prevent_initial_call=True
    )
    def apply_date_filter(n_clicks, start_date, end_date):
        if n_clicks is None:
            raise PreventUpdate
        
        return html.Div([
            html.H4("Filtro Aplicado:"),
            html.P(f"Período selecionado: {start_date} até {end_date}"),
            html.P("Implemente aqui a lógica de filtragem dos seus dados.")
        ])