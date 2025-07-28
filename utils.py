# Função para classificar um evento com base nos dados do DataFrame
# Recebe o identificador do evento e o DataFrame com os dados dos eventos
# Retorna a classificação do evento (Ruído, Evento Local, Evento Global) e a proporção de estações acionadas

def classificar_evento(evento, df):
    dados_evento = df[df["evento"] == evento]  # Filtra apenas os dados do evento informado
    estacoes_acionadas = dados_evento[dados_evento["valor"] > 10]["estacao"].nunique()  # Conta estações com valor > 10
    total_estacoes = dados_evento["estacao"].nunique()  # Conta o total de estações no evento
    if total_estacoes == 0:
        return "Sem dados", 0  # Se não há estações, retorna sem dados
    proporcao = estacoes_acionadas / total_estacoes  # Calcula a proporção de estações acionadas
    if proporcao < 0.10:
        classificacao = "Ruído"  # Menos de 10% das estações: Ruído
    elif proporcao <= 0.75:
        classificacao = "Evento Local"  # Até 75%: Evento Local
    else:
        classificacao = "Evento Global"  # Mais de 75%: Evento Global
    return classificacao, proporcao  # Retorna classificação e proporção 