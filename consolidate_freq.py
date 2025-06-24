import os
import pandas as pd

# Caminho base onde estão os arquivos
base_path = "events"

# Lista para guardar todos os DataFrames
dfs = []

# Varre os diretórios recursivamente
for root, dirs, files in os.walk(base_path):
    for file in files:
        if file.endswith("_freq.csv"):
            file_path = os.path.join(root, file)

            try:
                # Lê o CSV
                df = pd.read_csv(file_path)

                # Extrai nome do evento e estação do nome do arquivo
                nome_arquivo = os.path.basename(file)
                partes = nome_arquivo.split("_")
                nome_evento = partes[0]  # Ex: 12h03m42s
                estacao = partes[1].replace("_freq.csv", "")  # Ex: 20160003

                # Adiciona colunas extras
                df["evento"] = nome_evento
                df["estacao"] = estacao

                # Guarda no conjunto de dataframes
                dfs.append(df)
            except Exception as e:
                print(f"Erro ao processar {file_path}: {e}")

# Junta tudo em um único DataFrame
if dfs:
    df_geral_freq = pd.concat(dfs, ignore_index=True)
    #print(f"Total de linhas consolidadas: {len(df_geral_freq)}")

    # Salvar como CSV, se quiser
    df_geral_freq.to_csv("freq_consolidado.csv", index=False)
else:
    print("Nenhum arquivo '_freq.csv' encontrado.")
