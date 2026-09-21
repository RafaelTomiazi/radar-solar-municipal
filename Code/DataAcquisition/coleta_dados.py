# Coleta dos dados brutos das duas fontes do projeto.
# Rodo esse script uma vez so pra popular data/raw. Nao entra no fluxo do
# Streamlit pq o parquet da ANEEL tem mais de 100 MB, ninguem quer baixar
# isso toda vez que abre o dashboard

import json
import os
import sys
import time

import requests

# uso a raiz pra funcionar independente de onde eu chamo o script
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_RAW = os.path.join(RAIZ, "data", "raw")

# esse id foi tirado do portal de dados abertos da ANEEL, usando a API do CKAN
# pra achar em vez de fixar a url do arquivo (o link direto muda toda hora)
PACOTE_ANEEL = "relacao-de-empreendimentos-de-geracao-distribuida"
API_ANEEL = "https://dadosabertos.aneel.gov.br/api/3/action/package_show"
API_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def buscar_url_do_parquet():
    # pergunta pra API da ANEEL qual e a url atual do parquet
    resposta = requests.get(API_ANEEL, params={"id": PACOTE_ANEEL}, timeout=60)
    resposta.raise_for_status()
    dados = resposta.json()

    if not dados.get("success"):
        raise RuntimeError("A API da ANEEL respondeu mas indicou falha na consulta")

    # o pacote tem uns 12 recursos entre PDF, ZIP, CSV e PARQUET, eu quero
    # so o parquet principal (unico com esse nome)
    for recurso in dados["result"]["resources"]:
        if recurso.get("format") == "PARQUET" and "informacoes-tecnicas" not in recurso["name"]:
            return recurso["url"], dados["result"]["metadata_modified"]

    raise RuntimeError("Nao encontrei o recurso parquet no pacote da ANEEL")


def baixar_arquivo(url, destino):
    # baixa em pedacos pra nao ter que carregar 100 MB na memoria de uma vez
    with requests.get(url, stream=True, timeout=900) as resposta:
        resposta.raise_for_status()
        with open(destino, "wb") as arquivo:
            for pedaco in resposta.iter_content(chunk_size=1024 * 1024):
                # print(len(pedaco))  # usei isso pra debugar o tamanho dos chunks
                arquivo.write(pedaco)


def coletar_aneel():
    destino = os.path.join(PASTA_RAW, "empreendimento-geracao-distribuida.parquet")
    url, atualizado_em = buscar_url_do_parquet()
    print("Dataset da ANEEL atualizado em:", atualizado_em)

    inicio = time.time()
    baixar_arquivo(url, destino)
    tamanho = os.path.getsize(destino) / 1e6
    print("Baixei %.1f MB em %.0f segundos" % (tamanho, time.time() - inicio))
    return destino


def coletar_ibge():
    # traz os municipios do IBGE pra ter o nome oficial e a regiao certinha
    destino = os.path.join(PASTA_RAW, "municipios_ibge.json")
    resposta = requests.get(API_IBGE, params={"orderBy": "nome"}, timeout=120)
    resposta.raise_for_status()

    municipios = resposta.json()
    with open(destino, "w", encoding="utf-8") as arquivo:
        json.dump(municipios, arquivo, ensure_ascii=False)

    print("Salvei %d municipios do IBGE" % len(municipios))
    return destino


if __name__ == "__main__":
    os.makedirs(PASTA_RAW, exist_ok=True)

    # try separado pra nao derrubar o script inteiro se so uma fonte cair
    try:
        coletar_aneel()
    except Exception as erro:
        print("Falhou a coleta da ANEEL:", erro)

    try:
        coletar_ibge()
    except Exception as erro:
        print("Falhou a coleta do IBGE:", erro)

    print("Coleta encerrada, agora roda o processa_dados.py")
