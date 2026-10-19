# Coisas que todas as paginas usam: carga dos dados com cache, montagem da base
# com o upload do usuario, filtros e o grafico de barras.
# No TP2 isso tudo morava no app.py. No TP3 o app virou multipagina, e cada
# pagina e um arquivo separado em paginas/, entao separei o que e comum aqui pra
# nao repetir o mesmo codigo em sete arquivos.

import os
import sys
import threading

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_EXTERNAL = os.path.join(RAIZ, "data", "external")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

sys.path.append(RAIZ)  # pro "from Code.API.api import app" funcionar
sys.path.append(os.path.join(RAIZ, "Code", "DataAcquisition"))
sys.path.append(os.path.join(RAIZ, "Code", "App"))
from fonte_dados import buscar_metadados  # noqa: E402
import dados_usuario  # noqa: E402
import textos  # noqa: E402

# endereco da API do FastAPI. da pra trocar por variavel de ambiente se a API
# estiver rodando em outro lugar
API_URL = os.environ.get("RADAR_API_URL", "http://localhost:8000")


# ---- carga dos dados (tudo com cache)

@st.cache_data
def carregar(nome_arquivo, pasta=PASTA_PROCESSED):
    # sem o cache o streamlit releria os CSV do disco a cada clique
    caminho = os.path.join(pasta, nome_arquivo)
    try:
        return pd.read_csv(caminho)
    except FileNotFoundError:
        return None


def carregar_municipios():
    # se o processado nao existir cai pra amostra versionada
    dados = carregar("cobertura_municipios.csv")
    if dados is not None:
        return dados, "completo"
    dados = carregar("amostra_gd_municipio.csv", PASTA_AMOSTRA)
    if dados is not None:
        dados = dados.rename(columns={"NomMunicipio": "municipio", "SigUF": "uf"})
        return dados, "amostra"
    return None, "ausente"


@st.cache_data(ttl=3600)
def consultar_metadados():
    # a base nao muda de minuto em minuto, 1h de cache ja ta bom
    return buscar_metadados()


@st.cache_data
def carregar_noticias():
    caminho = os.path.join(PASTA_EXTERNAL, "noticias_aneel.csv")
    try:
        noticias = pd.read_csv(caminho, parse_dates=["data"])
    except FileNotFoundError:
        return None
    noticias["texto"] = noticias["texto"].fillna("")
    noticias["descricao"] = noticias["descricao"].fillna("")
    return noticias


@st.cache_data
def carregar_geracao_ons():
    # CSV gerado pelo scraping com Selenium (scraping_ons_selenium.py)
    return carregar("geracao_ons.csv", PASTA_EXTERNAL)


@st.cache_data(show_spinner="Gerando a nuvem de palavras...")
def nuvem_e_termos(lista_textos, extras):
    # recebe tupla (e nao lista) pq o cache precisa de argumento hashable
    contagem = textos.contar_termos(lista_textos, extras)
    if not contagem:
        return None, pd.DataFrame(columns=["termo", "ocorrencias"])
    imagem = textos.gerar_nuvem(dict(contagem.most_common(200)))
    termos = pd.DataFrame(contagem.most_common(20), columns=["termo", "ocorrencias"])
    return imagem, termos


def grafico_barras(serie, titulo_valor, horizontal=True):
    # o st.bar_chart ordena pelo nome, entao fiz com altair pra controlar a ordem
    tabela = serie.rename("valor").rename_axis("item").reset_index()
    eixo_item = alt.Y("item:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False, labelLimit=220)) if horizontal else alt.X("item:N", sort="-y", title=None)
    eixo_valor = alt.X("valor:Q", title=titulo_valor) if horizontal else alt.Y("valor:Q", title=titulo_valor)
    grafico = (
        alt.Chart(tabela)
        .mark_bar(color="#f59e0b")
        .encode(eixo_item, eixo_valor, tooltip=["item", alt.Tooltip("valor:Q", format=",.1f")])
    )
    altura = max(200, 26 * len(tabela)) if horizontal else 320
    st.altair_chart(grafico.properties(height=altura), width="stretch")


# ---- base com o upload do usuario

def montar_base():
    # devolve (base, municipios, origem, colunas_usuario, indicadores).
    # roda em toda pagina, mas e barato pq a leitura do CSV ta em cache
    municipios, origem = carregar_municipios()
    if municipios is None:
        return None, None, origem, [], {}

    if st.session_state.get("dados_usuario") is not None:
        base = dados_usuario.juntar(municipios, st.session_state["dados_usuario"])
        colunas_usuario = [c for c in st.session_state["dados_usuario"].columns if c != dados_usuario.COLUNA_CHAVE]
    else:
        base = municipios.copy()
        colunas_usuario = []

    base["rotulo"] = base["municipio"] + " - " + base["uf"]
    base["potencia_mw"] = base["potencia_total_kw"] / 1000

    indicadores = {
        "Potência instalada (MW)": "potencia_mw",
        "Número de empreendimentos": "qtd_empreendimentos",
        "Potência média por empreendimento (kW)": "potencia_media_kw",
    }
    for coluna in colunas_usuario:
        # coluna constante (tipo "ano" = 2026 em todas as linhas) nao vira indicador
        if pd.api.types.is_numeric_dtype(base[coluna]) and base[coluna].nunique() > 1:
            nome = "kW por mil de '%s' (seu arquivo)" % coluna
            divisor = base[coluna].replace(0, np.nan)
            base["kw_por_mil_" + coluna] = base["potencia_total_kw"] / divisor * 1000
            indicadores[nome] = "kw_por_mil_" + coluna

    return base, municipios, origem, colunas_usuario, indicadores


def aplicar_filtros(base):
    # os filtros moram na barra lateral do app.py e ficam no session_state,
    # entao qualquer pagina consegue ler sem repetir os widgets
    regioes = st.session_state.get("f_regioes", [])
    ufs = st.session_state.get("f_ufs", [])
    filtro = pd.Series(True, index=base.index)
    if regioes:
        filtro &= base["NomRegiao"].isin(regioes)
    if ufs:
        filtro &= base["uf"].isin(ufs)

    if ufs:
        recorte = ", ".join(ufs)
    elif regioes:
        recorte = ", ".join(regioes)
    else:
        recorte = "Brasil"
    return base[filtro], recorte


# ---- API do FastAPI

def api_no_ar():
    try:
        return requests.get(API_URL + "/", timeout=2).ok
    except requests.RequestException:
        return False


@st.cache_resource
def iniciar_api_local():
    # se ninguem subiu a API antes, o proprio app sobe ela numa thread separada.
    # assim quem baixar o projeto so precisa rodar o streamlit, sem abrir um
    # segundo terminal. cache_resource garante que isso acontece uma vez so,
    # e nao a cada clique
    if api_no_ar():
        return "ja estava no ar"
    if "localhost" not in API_URL and "127.0.0.1" not in API_URL:
        return "API externa fora do ar"

    import uvicorn
    from Code.API.api import app as app_api

    porta = int(API_URL.rsplit(":", 1)[-1])
    servidor = uvicorn.Server(uvicorn.Config(app_api, host="127.0.0.1", port=porta, log_level="warning"))
    threading.Thread(target=servidor.run, daemon=True).start()
    return "iniciada pelo app"


def chamar_api(metodo, rota, **kwargs):
    # devolve (json, erro). a pagina mostra o erro na tela em vez de quebrar
    try:
        resposta = requests.request(metodo, API_URL + rota, timeout=10, **kwargs)
    except requests.RequestException as erro:
        return None, "Não consegui falar com a API em %s (%s)" % (API_URL, erro.__class__.__name__)
    if not resposta.ok:
        try:
            detalhe = resposta.json().get("detail")
        except ValueError:
            detalhe = resposta.text
        return None, "A API respondeu %d: %s" % (resposta.status_code, detalhe)
    return resposta.json(), None
