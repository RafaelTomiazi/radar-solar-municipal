# Teste das rotas de LLM da API (TP4). Roda tudo pelo TestClient do FastAPI,
# sem precisar subir o uvicorn, e salva cada chamada (corpo enviado, codigo
# HTTP e resposta) em Docs/LLM/testes_api_llm.json, que vira evidencia no PDF.
#
# pra rodar, da raiz do projeto:
#   python Code/API/testa_api_llm.py

import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

import pandas as pd  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from Code.API import llm_local  # noqa: E402
from Code.API.api import app  # noqa: E402

cliente = TestClient(app, raise_server_exceptions=False)
noticias = pd.read_csv(os.path.join(RAIZ, "data", "external", "noticias_aneel.csv"))
# uma noticia marcada como GD pela palavra-chave e uma de tarifa
noticia_gd = noticias[noticias["tema_gd"]].iloc[0]
noticia_tarifa = noticias.iloc[0]

resultados = []


def chamar(nome, metodo, rota, esperado, corpo=None):
    inicio = time.time()
    resposta = cliente.request(metodo, rota, json=corpo)
    segundos = round(time.time() - inicio, 2)
    ok = resposta.status_code == esperado
    print("%-45s %s %d (esperado %d) %.1fs" % (nome, "OK " if ok else "ERRO", resposta.status_code, esperado, segundos))
    resultados.append({
        "teste": nome, "metodo": metodo, "rota": rota, "corpo": corpo,
        "codigo_esperado": esperado, "codigo_recebido": resposta.status_code,
        "passou": ok, "segundos": segundos, "resposta": resposta.json(),
    })


# ---- caminho feliz
chamar("status antes de carregar", "GET", "/llm/status", 200)
chamar("carregar o modelo", "POST", "/llm/carregar", 200)
chamar("resumo de notícia (GD)", "POST", "/processar_texto", 200,
       {"texto": noticia_gd["texto"], "tipo": "resumo"})
chamar("mesmo resumo de novo (cache)", "POST", "/processar_texto", 200,
       {"texto": noticia_gd["texto"], "tipo": "resumo"})
chamar("impacto para GD (notícia GD)", "POST", "/processar_texto", 200,
       {"texto": noticia_gd["texto"], "tipo": "impacto_gd"})
chamar("impacto para GD (notícia de tarifa)", "POST", "/processar_texto", 200,
       {"texto": noticia_tarifa["texto"], "tipo": "impacto_gd"})
chamar("resumo do município (Rio de Janeiro)", "POST", "/resumo-municipio", 200, {"cod_ibge": 3304557})
chamar("resumo do município (Brasília)", "POST", "/resumo-municipio", 200, {"cod_ibge": 5300108})

# ---- erros de entrada (422)
chamar("texto curto demais", "POST", "/processar_texto", 422, {"texto": "oi", "tipo": "resumo"})
chamar("texto só com espaços", "POST", "/processar_texto", 422, {"texto": " " * 30, "tipo": "resumo"})
chamar("texto longo demais", "POST", "/processar_texto", 422, {"texto": "a" * 7000, "tipo": "resumo"})
chamar("tipo de análise que não existe", "POST", "/processar_texto", 422, {"texto": noticia_gd["texto"], "tipo": "traducao"})
chamar("corpo sem o campo texto", "POST", "/processar_texto", 422, {"tipo": "resumo"})
chamar("código IBGE com 3 dígitos", "POST", "/resumo-municipio", 422, {"cod_ibge": 123})

# ---- erros de recurso (404 / 405)
chamar("município que não existe", "POST", "/resumo-municipio", 404, {"cod_ibge": 9999999})
chamar("GET numa rota que só aceita POST", "GET", "/processar_texto", 405)

# ---- modelo indisponivel (503): simulo descarregando e desativando o modelo
modelo_salvo, tokenizador_salvo = llm_local._modelo, llm_local._tokenizador
llm_local._modelo, llm_local._tokenizador = None, None
os.environ["RADAR_LLM_DESATIVADO"] = "1"
llm_local_cache = __import__("Code.API.api", fromlist=["processar_com_cache"]).processar_com_cache
llm_local_cache.cache_clear()
chamar("modelo indisponível", "POST", "/processar_texto", 503, {"texto": noticia_tarifa["texto"], "tipo": "resumo"})
del os.environ["RADAR_LLM_DESATIVADO"]
llm_local._modelo, llm_local._tokenizador = modelo_salvo, tokenizador_salvo

# ---- tempo esgotado (504): baixo o limite pra 1 segundo
limite_salvo = llm_local.TEMPO_LIMITE
llm_local.TEMPO_LIMITE = 1
chamar("tempo limite estourado", "POST", "/processar_texto", 504,
       {"texto": noticias.iloc[5]["texto"], "tipo": "resumo"})
llm_local.TEMPO_LIMITE = limite_salvo

passaram = sum(r["passou"] for r in resultados)
print("\n%d de %d testes passaram" % (passaram, len(resultados)))

pasta = os.path.join(RAIZ, "Docs", "LLM")
os.makedirs(pasta, exist_ok=True)
with open(os.path.join(pasta, "testes_api_llm.json"), "w", encoding="utf-8") as arquivo:
    json.dump(resultados, arquivo, ensure_ascii=False, indent=2)
