def classificar_evento(evento, df):
    dados_evento = df[df["evento"] == evento]
    estacoes_acionadas = dados_evento[dados_evento["valor"] > 10]["estacao"].nunique()
    total_estacoes = dados_evento["estacao"].nunique()
    if total_estacoes == 0:
        return "Sem dados", 0
    proporcao = estacoes_acionadas / total_estacoes
    if proporcao < 0.10:
        classificacao = "Ruído"
    elif proporcao <= 0.75:
        classificacao = "Evento Local"
    else:
        classificacao = "Evento Global"
    return classificacao, proporcao 