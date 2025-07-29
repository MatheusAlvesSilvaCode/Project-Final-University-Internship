from minio import Minio
from urllib3 import PoolManager
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import pandas as pd
from io import BytesIO
import json

# Ignora alertas de certificado SSL autoassinado
urllib3.disable_warnings(InsecureRequestWarning)

# Cliente HTTP que ignora verificação de certificados
http_client = PoolManager(cert_reqs='CERT_NONE')

# Conexão com o MinIO via HTTPS na porta correta
client = Minio(
    "localhost:9000",
    access_key="dbadmin",
    secret_key="sosdbadmin",
    secure=True,
    http_client=http_client
)

BUCKET = "daivoes"
BASE_PATH = "events/2025"

def listar_objetos():
    """Lista todos os objetos (arquivos) dentro do bucket/prefixo"""
    objetos = client.list_objects(BUCKET, prefix=BASE_PATH, recursive=True)
    return [obj.object_name for obj in objetos]

def carregar_csv_minio(objeto):
    """Carrega um CSV do MinIO e transforma em DataFrame"""
    response = client.get_object(BUCKET, objeto)
    conteudo = response.read()
    response.close()
    response.release_conn()
    return pd.read_csv(BytesIO(conteudo))

def carregar_json_minio(objeto):
    """Carrega um JSON do MinIO e transforma em dict"""
    response = client.get_object(BUCKET, objeto)
    conteudo = response.read()
    response.close()
    response.release_conn()
    return json.loads(conteudo.decode("utf-8"))

def consolidar_dados():
    """Consolida todos os freq.csv, data.csv e JSONs em DataFrames - Versão MinIO"""
    arquivos = listar_objetos()
    freq_dfs = []
    data_dfs = []
    eventos = []

    print(f"Encontrados {len(arquivos)} arquivos no MinIO")
    
    # Contadores para debug
    freq_count = 0
    data_count = 0
    json_count = 0

    for arquivo in arquivos:
        # Processar arquivos de frequência (_freq.csv)
        if arquivo.endswith("_freq.csv"):
            try:
                df_freq = carregar_csv_minio(arquivo)
                
                # Extrair nome do evento e estação do nome do arquivo (igual ao consolidate_freq.py)
                nome_arquivo = arquivo.split('/')[-1]  # Pega apenas o nome do arquivo
                partes = nome_arquivo.split("_")
                nome_evento = partes[0]  # Ex: 11h52m12s
                estacao = partes[1]  # Ex: 20160003

                # Adiciona colunas extras ao DataFrame (igual ao consolidate_freq.py)
                df_freq["evento"] = nome_evento
                df_freq["estacao"] = estacao

                freq_dfs.append(df_freq)
                freq_count += 1
                
            except Exception as e:
                print(f"Erro ao processar freq {arquivo}: {e}")

        # Processar arquivos de dados (_data.csv)
        elif arquivo.endswith("_data.csv"):
            try:
                df_data = carregar_csv_minio(arquivo)
                
                # Extrair nome do evento e estação do nome do arquivo (igual ao consolidate_data.py)
                nome_arquivo = arquivo.split('/')[-1]  # Pega apenas o nome do arquivo
                partes = nome_arquivo.split("_")
                nome_evento = partes[0]  # Ex: 11h52m12s
                estacao = partes[1]  # Ex: 20160003

                # Adiciona colunas extras ao DataFrame (igual ao consolidate_data.py)
                df_data["evento"] = nome_evento
                df_data["estacao"] = estacao

                data_dfs.append(df_data)
                data_count += 1
                
            except Exception as e:
                print(f"Erro ao processar data {arquivo}: {e}")

        # Processar arquivos JSON
        elif arquivo.endswith(".json"):
            try:
                json_data = carregar_json_minio(arquivo)
                # Extrair o ID do evento do nome do arquivo
                evento_id = arquivo.split('/')[-1].replace('.json', '')

                # Caso seja estrutura de dict com "eventFiles"
                if isinstance(json_data, dict) and "eventFiles" in json_data:
                    for uid, evento in json_data["eventFiles"].items():
                        # Pega os dados dos canais (se existirem)
                        amostras = evento.get("df", {}).get("cf", [])
                        
                        # Para cada canal, coleta os dados de interesse
                        for canal in amostras:
                            eventos.append({
                                "evento": evento_id,                # Nome do arquivo = ID do evento
                                "estacao": evento.get("recorderName", "Desconhecido"),
                                "direcao": canal.get("chName", ""),         # Direção do canal (ex: T, R, V)
                                "peak": canal.get("peak", 0),              # Valor de pico da onda
                                "rms": canal.get("rms", 0),                # Valor RMS (média quadrática)
                                "valor": canal.get("value", 0),            # Valor geral da medição
                                "trigger": evento.get("triggerStart"),     # Momento em que o evento foi detectado
                                "recorderUid": evento.get("recorderUid"),
                                "duracao": evento.get("duration"),
                                "amplitudeMax": evento.get("maxAmplitude"),
                                "tipo": evento.get("eventType"),
                            })

                # Caso seja lista de eventos simples
                elif isinstance(json_data, list):
                    for item in json_data:
                        item["evento"] = evento_id
                        eventos.append(item)

                # Caso seja um único dict direto
                elif isinstance(json_data, dict):
                    json_data["evento"] = evento_id
                    eventos.append(json_data)

                json_count += 1
            except Exception as e:
                print(f"Erro ao carregar JSON: {arquivo} - {e}")

    print(f"Processados: {freq_count} arquivos freq, {data_count} arquivos data, {json_count} arquivos JSON")

    # Junta todos os DataFrames em um único DataFrame geral (igual aos scripts consolidate)
    if freq_dfs:
        df_freq = pd.concat(freq_dfs, ignore_index=True)
        print(f"Total de linhas de frequência consolidadas: {len(df_freq)}")
    else:
        df_freq = pd.DataFrame()
        print("Nenhum arquivo '_freq.csv' encontrado.")

    if data_dfs:
        df_data = pd.concat(data_dfs, ignore_index=True)
        print(f"Total de linhas de dados consolidadas: {len(df_data)}")
    else:
        df_data = pd.DataFrame()
        print("Nenhum arquivo '_data.csv' encontrado.")

    df_eventos = pd.DataFrame(eventos) if eventos else pd.DataFrame()
    if not df_eventos.empty:
        print(f"Total de eventos processados: {len(df_eventos)}")

    return df_freq, df_data, df_eventos
