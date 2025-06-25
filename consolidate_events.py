import os
import json
import pandas as pd

# Função que carrega os eventos a partir dos arquivos JSON dentro da pasta fornecida
def carregar_eventos(pasta_raiz):
    registros = []  # Lista onde vamos guardar todos os dados coletados dos arquivos

    # Percorre todas as pastas e subpastas dentro da pasta raiz
    for root, _, files in os.walk(pasta_raiz):
        for file in files:
            # Verifica se o arquivo termina com ".json" (ou seja, se é um arquivo JSON)
            if file.lower().endswith(".json"):
                caminho_json = os.path.join(root, file)  # Junta o caminho da pasta atual com o nome do arquivo

                try:
                    # Abre o arquivo JSON com codificação UTF-8
                    with open(caminho_json, encoding='utf-8') as f:
                        dados = json.load(f)  # Lê os dados do arquivo e transforma em um dicionário Python
                except Exception as e:
                    # Se der erro ao abrir ou ler o JSON, mostra a mensagem e pula para o próximo arquivo
                    print(f"[ERRO] Não foi possível abrir {file}: {e}")
                    continue

                # Verifica se o arquivo contém a chave "eventFiles"
                if "eventFiles" not in dados:
                    print(f"[AVISO] Ignorando JSON sem 'eventFiles': {file}")
                    continue  # Pula esse arquivo se não tiver a chave esperada

                evento_id = file.replace(".json", "")  # Usa o nome do arquivo (sem ".json") como identificador do evento

                # Percorre cada estação presente no JSON
                for estacao_id, estacao_data in dados["eventFiles"].items():
                    # Pega o nome do gravador, ou "Desconhecida" se não existir
                    nome = estacao_data.get("recorderName", "Desconhecida")
                    
                    # Pega o timestamp de início do gatilho (trigger), ou None se não existir
                    trigger_ts = estacao_data.get("triggerStart", None)
                    
                    # Pega os dados dos canais (se existirem). df = dados físicos, cf = canais físicos
                    amostras = estacao_data.get("df", {}).get("cf", [])

                    # Para cada canal, coleta os dados de interesse
                    for canal in amostras:
                        registros.append({
                            "evento": evento_id,                # Nome do arquivo = ID do evento
                            "estacao": nome,                    # Nome da estação (gravador)
                            "direcao": canal["chName"],         # Direção do canal (ex: T, R, V)
                            "peak": canal["peak"],              # Valor de pico da onda
                            "rms": canal["rms"],                # Valor RMS (média quadrática)
                            "valor": canal["value"],            # Valor geral da medição
                            "trigger": trigger_ts               # Momento em que o evento foi detectado
                        })

    # Converte a lista de dicionários para um DataFrame do pandas
    df = pd.DataFrame(registros)

    return df  # Retorna o DataFrame com todos os dados processados

# Roda a função se o script for executado diretamente
if __name__ == "__main__":
    # Caminho da pasta contendo os arquivos de eventos
    caminho = r"C:\Users\mathe\Desktop\Estágio\Final\events\2025\2025"

    # Executa a função e armazena o resultado no DataFrame df
    df = carregar_eventos(caminho)

    # Exibe as primeiras linhas do DataFrame resultante
    print(df.head())  # Você pode trocar para df.info(), df.shape, etc., se quiser visualizar de outras formas
