# Importa componentes do Dash para criar interface e callbacks
from dash import html, dcc, Input, Output, callback, callback_context, no_update, State
# Importa módulo para codificação de arquivos em base64
import base64
# Importa classe para manipulação de datas
from datetime import datetime
# Importa componentes de Bootstrap para Dash
import dash_bootstrap_components as dbc
# Importa exceção para evitar atualizações desnecessárias
from dash.exceptions import PreventUpdate

# Carrega a imagem SVG do mapa da barragem e converte para base64 para exibição no Dash
with open("assets/SOS-Daivoes.svg", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

# Dicionário com as coordenadas (em porcentagem) de cada estação sobre a imagem
station_coords = {
    "S-01-1": {"x": 51.68, "y": 45.98, "radius": 7},
    "S-07-1": {"x": 69.5, "y": 40.2, "radius": 7},
    "S-09-1": {"x": 76.0, "y": 57.8, "radius": 7},
    "S-01-02": {"x": 51.7, "y": 74.0, "radius": 7},
    "S-10-01": {"x": 22.8, "y": 58.0, "radius": 7},
    "S-06-1": {"x": 33.3, "y": 40.1, "radius": 7}
}

# Layout da página do mapa da barragem
layout = html.Div([
    html.H1("Mapa da Barragem", style={"text-align": "center", "marginTop": "30px"}),  # Título principal
    html.H2("SOS Daivões", style={"text-align": "center"}),  # Subtítulo
    
    # Container responsivo para a imagem do mapa
    html.Div(
        style={
            "position": "relative",
            "width": "100%",
            "height": "0",
            "paddingBottom": "60%",
            "overflow": "hidden"
        },
        children=[
            # Exibe a imagem SVG do mapa
            html.Img(
                src=f"data:image/svg+xml;base64,{encoded_image}",
                style={
                    "position": "absolute",
                    "width": "100%",
                    "height": "100%",
                    "objectFit": "contain"
                }
            ),
            # Cria áreas clicáveis (invisíveis) para cada estação
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
                        "opacity": "0"  # Invisível, mas clicável
                    }
                )
                for station_id, coords in station_coords.items()
            ]
        ]
    ),
    
    html.Div(id='station-info', style={"margin": "30px", "text-align": "center"})  # Área para mostrar info da estação
])

# Função para registrar os callbacks do mapa
# Exibe informações da estação quando o usuário clica em uma área do mapa

def register_callbacks(app):
    @app.callback(
        Output('station-info', 'children'),
        [Input(f'station-{station_id}', 'n_clicks') for station_id in station_coords.keys()],
        prevent_initial_call=True
    )
    def show_station_info(*args):
        ctx = callback_context  # Contexto do callback para saber o que disparou
        if not ctx.triggered:
            return "Clique em uma estação no mapa para ver informações."
        
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]  # Identifica qual estação foi clicada
        station_id = triggered_id.replace('station-', '')  # Extrai o id da estação
        
        # Dicionário com informações de cada estação
        station_data = {
            "S-01-1": {"name": "Estação S-01-1", "description": "Descrição da estação S-01-1"},
            "S-07-1": {"name": "Estação S-07-1", "description": "Descrição da estação S-07-1"},
            "S-09-1": {"name": "Estação S-09-1", "description": "Descrição da estação S-09-1"},
            "S-01-2": {"name": "Estação S-01-2", "description": "Descrição da estação S-01-2"},
            "S-10-01": {"name": "Estação S-10-01", "description": "Descrição da estação S-10-01"},
            "S-06-1": {"name": "Estação S-06-1", "description": "Descrição da estação S-06-1"},
        }
        
        data = station_data.get(station_id, {"name": station_id, "description": "Sem informações adicionais"})  # Busca info
        
        return html.Div([
            html.H3(f"{data['name']}"),  # Nome da estação
            html.P(data['description']),  # Descrição
            html.P("Você pode adicionar gráficos, tabelas ou outras informações aqui.")  # Espaço para mais info
        ])