# Importa módulo para manipulação de arquivos e diretórios
import os
# Importa pandas para manipulação de dados em DataFrame
import pandas as pd

# Caminho base onde estão os arquivos de eventos
base_path = "events"

# Lista para guardar todos os DataFrames lidos
dfs = []

# Varre os diretórios recursivamente a partir do base_path
for root, dirs, files in os.walk(base_path):
    for file in files:
        # Verifica se o arquivo termina com '_freq.csv'
        if file.endswith("_freq.csv"):
            file_path = os.path.join(root, file)  # Monta o caminho completo do arquivo

            try:
                # Lê o arquivo CSV em um DataFrame
                df = pd.read_csv(file_path)

                # Extrai nome do evento e estação do nome do arquivo
                nome_arquivo = os.path.basename(file)
                partes = nome_arquivo.split("_")
                nome_evento = partes[0]  # Ex: 12h03m42s
                estacao = partes[1].replace("_freq.csv", "")  # Ex: 20160003

                # Adiciona colunas extras ao DataFrame
                df["evento"] = nome_evento
                df["estacao"] = estacao

                # Adiciona o DataFrame à lista
                dfs.append(df)
            except Exception as e:
                print(f"Erro ao processar {file_path}: {e}")  # Mostra erro se não conseguir ler/processar

# Junta todos os DataFrames em um único DataFrame geral
if dfs:
    df_geral_freq = pd.concat(dfs, ignore_index=True)
    #print(f"Total de linhas consolidadas: {len(df_geral_freq)}")

    # Salva o DataFrame consolidado em um novo arquivo CSV
    df_geral_freq.to_csv("freq_consolidado.csv", index=False)
else:
    print("Nenhum arquivo '_freq.csv' encontrado.")  # Mensagem se não encontrar arquivos
