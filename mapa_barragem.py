from dash import html, dcc, Input, Output, callback, callback_context
import base64

# Carrega a imagem SVG como base64
with open("assets/SOS-Daivoes.svg", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

# Coordenadas em porcentagem da largura/altura da imagem
station_coords = {
    "S-01-1": {"x": 51.68, "y": 45.98, "radius": 5.71},  # Já existente e funcional
    "S-07-1": {"x": 69.03, "y": 39.78, "radius": 5.71},
    "S-09-1": {"x": 75.68, "y": 57.39, "radius": 5.71},
    "S-01-02": {"x": 51.68, "y": 73.81, "radius": 5.71},
    "S-10-01": {"x": 22.52, "y": 57.78, "radius": 5.71},
    "S-06-1": {"x": 33.05, "y": 39.79, "radius": 5.71}
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
            "paddingBottom": "60%",  # Proporção da imagem (ajuste conforme necessário)
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
            # Áreas clicáveis com posicionamento relativo
            *[
                html.Div(
                    id=f"station-{station_id}",
                    style={
                        "position": "absolute",
                        "left": f"{coords['x']}%",
                        "top": f"{coords['y']}%",
                        "width": f"{coords['radius']}%",
                        "height": f"{coords['radius']}%",
                        "transform": "translate(-50%, -50%)",  # Centraliza no ponto
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
    
    html.Div(id='station-info', style={"margin": "30px", "text-align": "center"})
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