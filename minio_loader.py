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
    """Consolida todos os freq.csv, data.csv e JSONs em DataFrames"""
    arquivos = listar_objetos()
    freq_dfs = []
    data_dfs = []
    eventos = []

    for arquivo in arquivos:
        if arquivo.endswith("freq.csv"):
            try:
                freq_dfs.append(carregar_csv_minio(arquivo))
            except Exception as e:
                print(f"Erro ao carregar freq: {arquivo} - {e}")

        elif arquivo.endswith("data.csv"):
            try:
                data_dfs.append(carregar_csv_minio(arquivo))
            except Exception as e:
                print(f"Erro ao carregar data: {arquivo} - {e}")

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

            except Exception as e:
                print(f"Erro ao carregar JSON: {arquivo} - {e}")

    df_freq = pd.concat(freq_dfs, ignore_index=True) if freq_dfs else pd.DataFrame()
    df_data = pd.concat(data_dfs, ignore_index=True) if data_dfs else pd.DataFrame()
    df_eventos = pd.DataFrame(eventos) if eventos else pd.DataFrame()

    return df_freq, df_data, df_eventos
