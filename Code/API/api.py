# API do Radar Solar Municipal, feita com FastAPI.
# Serve os dados de geracao distribuida por municipio que ja estao processados
# em data/processed. O app Streamlit consome essa API na pagina "API".
#
# Pra rodar a API:
#   uvicorn Code.API.api:app --reload --port 8000
# A documentacao automatica (Swagger) fica em http://localhost:8000/docs
#
# Por que uma API separada se os dados ja estao em CSV? Pra separar o acesso ao
# dado da interface. Com a API, o painel (ou qualquer outro programa, ou outra
# pessoa) pega os dados por HTTP sem precisar conhecer os arquivos. E o passo que
# prepara o projeto pro TP4, quando a parte de LLM vai responder perguntas
# consultando esses mesmos endpoints.

import os

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

app = FastAPI(
    title="Radar Solar Municipal - API",
    description=(
        "API de consulta da geração distribuída de energia por município, a "
        "partir dos dados abertos da ANEEL. Projeto de Bloco de IA Aplicada, Infnet."
    ),
    version="1.0.0 (TP3)",
)


# ---- carga dos dados (uma vez, quando a API sobe)

def carregar_municipios():
    # mesma logica do app: tenta o processado, cai pra amostra
    caminho = os.path.join(PASTA_PROCESSED, "cobertura_municipios.csv")
    if os.path.exists(caminho):
        return pd.read_csv(caminho)
    caminho_amostra = os.path.join(PASTA_AMOSTRA, "amostra_gd_municipio.csv")
    if os.path.exists(caminho_amostra):
        dados = pd.read_csv(caminho_amostra)
        return dados.rename(columns={"NomMunicipio": "municipio", "SigUF": "uf"})
    return pd.DataFrame()


MUNICIPIOS = carregar_municipios()

# os 4 municipios sem nenhum empreendimento (todos no AM) vem com regiao e
# media vazias. NaN nao vira JSON e a API dava erro 500 neles, descobri testando
# /municipios/1300060. preencho a regiao pela UF e a media com zero
if not MUNICIPIOS.empty:
    regiao_da_uf = MUNICIPIOS.dropna(subset=["NomRegiao"]).groupby("uf")["NomRegiao"].first()
    MUNICIPIOS["NomRegiao"] = MUNICIPIOS["NomRegiao"].fillna(MUNICIPIOS["uf"].map(regiao_da_uf))
    MUNICIPIOS["potencia_media_kw"] = MUNICIPIOS["potencia_media_kw"].fillna(0)


# ---- modelos (o FastAPI usa pra validar e documentar sozinho)

class Municipio(BaseModel):
    CodMunicipioIbge: int
    municipio: str
    uf: str
    NomRegiao: str | None = None
    qtd_empreendimentos: int
    potencia_total_kw: float
    potencia_media_kw: float


class PopulacaoEntrada(BaseModel):
    # o que o POST recebe: um municipio e a populacao dele, pra calcular
    # a potencia instalada por mil habitantes
    cod_ibge: int = Field(..., description="Código IBGE do município (7 dígitos)", examples=[3304557])
    populacao: int = Field(..., gt=0, description="População do município", examples=[6211000])


class PopulacaoResposta(BaseModel):
    municipio: str
    uf: str
    potencia_total_kw: float
    populacao: int
    kw_por_mil_habitantes: float


# ---- rotas

@app.get("/", tags=["info"])
def raiz():
    # rota de boas vindas, diz se os dados carregaram
    return {
        "projeto": "Radar Solar Municipal",
        "municipios_carregados": len(MUNICIPIOS),
        "documentacao": "/docs",
        "rotas": ["/municipios", "/municipios/{cod_ibge}", "/ranking", "/indicador-por-habitante"],
    }


@app.get("/municipios", tags=["consulta"])
def listar_municipios(
    uf: str | None = Query(None, description="Filtrar por UF, ex.: RJ", max_length=2),
    limite: int = Query(50, ge=1, le=500, description="Quantos municípios devolver"),
):
    # GET com filtro opcional por UF. ex: /municipios?uf=RJ&limite=10
    if MUNICIPIOS.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados. Rode o processamento.")

    dados = MUNICIPIOS
    if uf:
        dados = dados[dados["uf"].str.upper() == uf.upper()]
        if dados.empty:
            raise HTTPException(status_code=404, detail="Nenhum município para a UF %s" % uf)

    dados = dados.sort_values("potencia_total_kw", ascending=False).head(limite)
    return {
        "total": len(dados),
        "uf": uf.upper() if uf else "Brasil",
        "municipios": dados.to_dict(orient="records"),
    }


@app.get("/municipios/{cod_ibge}", response_model=Municipio, tags=["consulta"])
def municipio_por_codigo(cod_ibge: int):
    # GET de um municipio so, pelo codigo IBGE. ex: /municipios/3304557
    if MUNICIPIOS.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados.")
    linha = MUNICIPIOS[MUNICIPIOS["CodMunicipioIbge"] == cod_ibge]
    if linha.empty:
        raise HTTPException(status_code=404, detail="Município %d não encontrado" % cod_ibge)
    return linha.iloc[0].to_dict()


@app.get("/ranking", tags=["consulta"])
def ranking(
    por: str = Query("potencia", description="potencia, quantidade ou media"),
    uf: str | None = Query(None, max_length=2),
    top: int = Query(10, ge=1, le=100),
):
    # GET do ranking configuravel. ex: /ranking?por=potencia&uf=SP&top=5
    if MUNICIPIOS.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados.")

    colunas = {
        "potencia": "potencia_total_kw",
        "quantidade": "qtd_empreendimentos",
        "media": "potencia_media_kw",
    }
    if por not in colunas:
        raise HTTPException(status_code=400, detail="Use por = potencia, quantidade ou media")

    dados = MUNICIPIOS
    if uf:
        dados = dados[dados["uf"].str.upper() == uf.upper()]

    coluna = colunas[por]
    dados = dados.sort_values(coluna, ascending=False).head(top)
    return {
        "criterio": por,
        "uf": uf.upper() if uf else "Brasil",
        "ranking": dados[["municipio", "uf", coluna]].to_dict(orient="records"),
    }


@app.post("/indicador-por-habitante", response_model=PopulacaoResposta, tags=["cálculo"])
def indicador_por_habitante(entrada: PopulacaoEntrada):
    # POST: recebe um municipio e a populacao, devolve a potencia instalada
    # por mil habitantes. ex de corpo: {"cod_ibge": 3304557, "populacao": 6211000}
    if MUNICIPIOS.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados.")

    linha = MUNICIPIOS[MUNICIPIOS["CodMunicipioIbge"] == entrada.cod_ibge]
    if linha.empty:
        raise HTTPException(status_code=404, detail="Município %d não encontrado" % entrada.cod_ibge)

    linha = linha.iloc[0]
    kw_por_mil = linha["potencia_total_kw"] / entrada.populacao * 1000
    return {
        "municipio": linha["municipio"],
        "uf": linha["uf"],
        "potencia_total_kw": round(float(linha["potencia_total_kw"]), 2),
        "populacao": entrada.populacao,
        "kw_por_mil_habitantes": round(kw_por_mil, 2),
    }
