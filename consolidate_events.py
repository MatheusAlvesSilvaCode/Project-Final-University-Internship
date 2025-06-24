import os
import json
import pandas as pd

def carregar_eventos(pasta_raiz):
    registros = []

    for root, _, files in os.walk(pasta_raiz):
        for file in files:
            if file.lower().endswith(".json"):  # verifica se é JSON mesmo
                caminho_json = os.path.join(root, file)
                try:
                    with open(caminho_json, encoding='utf-8') as f:
                        dados = json.load(f)
                except Exception as e:
                    print(f"[ERRO] Não foi possível abrir {file}: {e}")
                    continue

                if "eventFiles" not in dados:
                    print(f"[AVISO] Ignorando JSON sem 'eventFiles': {file}")
                    continue

                evento_id = file.replace(".json", "")
                for estacao_id, estacao_data in dados["eventFiles"].items():
                    nome = estacao_data.get("recorderName", "Desconhecida")
                    trigger_ts = estacao_data.get("triggerStart", None)
                    amostras = estacao_data.get("df", {}).get("cf", [])

                    for canal in amostras:
                        registros.append({
                            "evento": evento_id,
                            "estacao": nome,
                            "direcao": canal["chName"],
                            "peak": canal["peak"],
                            "rms": canal["rms"],
                            "valor": canal["value"],
                            "trigger": trigger_ts
                        })

                #print(f"[OK] Processado: {file}")

    df = pd.DataFrame(registros)
    return df

# Roda a função e imprime o resultado
if __name__ == "__main__":
    # 👇 Caminho direto para a pasta que contém os eventos
    caminho = r"C:\Users\mathe\Desktop\Estágio\Final\events\2025\2025"
    
    df = carregar_eventos(caminho)
    
    # Mostra o DataFrame inteiro (ou as primeiras linhas)

