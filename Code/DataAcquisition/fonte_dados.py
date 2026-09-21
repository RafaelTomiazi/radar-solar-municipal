# Aqui ficam as chamadas pra API externa.
# o app so chama buscar_metadados, nao precisa saber como funciona por dentro

import json
import os
from datetime import datetime

import requests
import pandas as pd  # acho que nem uso isso aqui, deixei de um teste antigo

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(RAIZ, "Sample_Data", "cache_metadados.json")

API_ANEEL = "https://dadosabertos.aneel.gov.br/api/3/action/package_show"
PACOTE = "relacao-de-empreendimentos-de-geracao-distribuida"


def buscar_metadados():
    # retorna (data, origem) pq mostro os dois no dashboard
    try:
        resp = requests.get(API_ANEEL, params={"id": PACOTE}, timeout=8)
        resp.raise_for_status()
        dados = resp.json()
        # print(dados)  # deixei aqui pra quando precisar ver a resposta inteira

        if not dados.get("success"):
            raise ValueError("A API respondeu mas indicou falha")

        atualizado = dados["result"]["metadata_modified"][:10]
        salvar_cache(atualizado)
        return atualizado, "API da ANEEL ao vivo"

    # peguei um Exception generico mesmo, nao precisa separar timeout de
    # connection error aqui, o fallback e o mesmo pros dois casos
    except Exception as erro:
        return ler_cache("a API retornou um erro: %s" % erro)


def salvar_cache(data_referencia):
    # guarda a ultima resposta boa pra usar quando a API cair
    try:
        with open(CACHE, "w", encoding="utf-8") as arquivo:
            json.dump(
                {
                    "data_referencia": data_referencia,
                    "gravado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
                },
                arquivo,
                ensure_ascii=False,
            )
    except OSError:
        # cache e so um extra, se nao der pra salvar o app continua igual
        pass


def ler_cache(motivo):
    # se nem o cache existir devolve None e a tela mostra o problema
    try:
        with open(CACHE, encoding="utf-8") as arquivo:
            guardado = json.load(arquivo)
        return guardado["data_referencia"], "cache local, %s" % motivo
    except (OSError, KeyError, json.JSONDecodeError):
        return None, "sem dado disponivel, %s" % motivo
