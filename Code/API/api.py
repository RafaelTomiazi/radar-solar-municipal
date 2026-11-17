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

#
# TP4: entrou o LLM local (Code/API/llm_local.py) com as rotas /processar_texto,
# /resumo-municipio e /llm/status, todas com response_model, e um tratamento de
# erro padronizado: toda resposta de erro tem o mesmo formato (ErroResposta).

import json
import os
import re
from enum import Enum
from functools import lru_cache
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

try:
    # import relativo quando sobe com "uvicorn Code.API.api:app" ou pelo app
    from Code.API import llm_local
except ImportError:  # rodando de dentro da pasta Code/API
    import llm_local

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

AVISO_IA = (
    "Texto gerado por IA (modelo local %s). Pode conter erros: confira sempre "
    "com os números originais que vão junto nesta resposta." % llm_local.NOME_MODELO
)

app = FastAPI(
    title="Radar Solar Municipal - API",
    description=(
        "API de consulta da geração distribuída de energia por município, a "
        "partir dos dados abertos da ANEEL. Projeto de Bloco de IA Aplicada, Infnet. "
        "No TP4 ganhou rotas com um LLM rodando localmente (HuggingFace Transformers)."
    ),
    version="2.0.0 (TP4)",
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


# ---- modelos do TP4 (LLM)

class TipoAnalise(str, Enum):
    # Enum faz o FastAPI recusar sozinho (422) qualquer tipo fora da lista
    resumo = "resumo"
    impacto_gd = "impacto_gd"


class ProcessarTextoEntrada(BaseModel):
    texto: str = Field(
        ...,
        min_length=20,
        max_length=6000,
        description="Texto a processar (ex.: uma notícia da ANEEL). Entre 20 e 6.000 caracteres.",
        examples=["A ANEEL aprovou nesta terça-feira novas regras para a micro e minigeração distribuída..."],
    )
    tipo: TipoAnalise = Field(
        TipoAnalise.resumo,
        description="resumo = resumo em linguagem simples; impacto_gd = classifica o impacto para quem tem ou quer solar",
    )

    @field_validator("texto")
    @classmethod
    def texto_nao_vazio(cls, valor):
        # 20 espacos em branco passariam no min_length, por isso confiro de novo
        # depois de tirar os espacos
        valor = valor.strip()
        if len(valor) < 20:
            raise ValueError("o texto precisa ter pelo menos 20 caracteres além de espaços")
        return valor


class ProcessarTextoResposta(BaseModel):
    tipo_analise: TipoAnalise
    texto_original: str
    tamanho_texto: int = Field(..., description="Quantidade de caracteres do texto recebido")
    resultado: str = Field(..., description="O que o modelo escreveu")
    classe: Literal["afeta_gd", "afeta_consumidor", "nao_afeta", "indefinida"] | None = Field(
        None, description="Só no tipo impacto_gd. 'indefinida' se o modelo não respondeu uma das três classes"
    )
    numeros_fora_dos_dados: list[str] = Field(
        ..., description="Números que o modelo escreveu e que não estão no texto de origem (possível invenção)"
    )
    modelo: str
    tempo_segundos: float
    em_cache: bool = Field(..., description="True se a resposta veio do cache, sem rodar o modelo de novo")
    gerado_por_ia: bool = True
    aviso: str


class ResumoMunicipioEntrada(BaseModel):
    cod_ibge: int = Field(..., ge=1000000, le=9999999, description="Código IBGE (7 dígitos)", examples=[3304557])


class DadosUsados(BaseModel):
    # os numeros que foram pro prompt. vao junto na resposta pra pessoa conferir
    potencia_total_kw: float
    qtd_empreendimentos: int
    potencia_media_kw: float
    posicao_na_uf: int
    municipios_na_uf: int
    posicao_no_brasil: int
    municipios_no_brasil: int
    mediana_potencia_uf_kw: float


class ResumoMunicipioResposta(BaseModel):
    cod_ibge: int
    municipio: str
    uf: str
    resumo: str
    dados_usados: DadosUsados
    numeros_fora_dos_dados: list[str] = Field(
        ..., description="Números do resumo que não estão nos dados enviados ao modelo. Vazio = todos conferem"
    )
    modelo: str
    tempo_segundos: float
    em_cache: bool
    gerado_por_ia: bool = True
    aviso: str


class LLMStatus(BaseModel):
    modelo: str
    carregado: bool
    bibliotecas_instaladas: bool
    erro_carga: str | None
    tempo_limite_s: int


class ErroResposta(BaseModel):
    # formato unico de erro da API. "detail" fica com o mesmo nome que o
    # FastAPI usa, assim o app (comum.chamar_api) continua lendo igual
    codigo: int
    erro: str = Field(..., description="Nome curto do erro, ex.: modelo_indisponivel")
    detail: str = Field(..., description="Explicação para quem chamou a API")
    dica: str | None = Field(None, description="O que fazer para resolver")


# respostas de erro documentadas no Swagger das rotas de LLM
ERROS_LLM = {
    422: {"model": ErroResposta, "description": "Entrada inválida (texto vazio, curto, longo ou tipo errado)"},
    500: {"model": ErroResposta, "description": "Erro inesperado ao gerar o texto"},
    503: {"model": ErroResposta, "description": "Modelo não carregado ou bibliotecas ausentes"},
    504: {"model": ErroResposta, "description": "O modelo passou do tempo limite"},
}


# ---- tratamento de erros (TP4)
# em vez de cada rota montar o erro do seu jeito, as excecoes caem aqui e
# viram sempre o mesmo JSON (ErroResposta), com uma dica do que fazer

def resposta_erro(codigo, erro, detalhe, dica=None):
    corpo = ErroResposta(codigo=codigo, erro=erro, detail=detalhe, dica=dica)
    return JSONResponse(status_code=codigo, content=corpo.model_dump())


@app.exception_handler(StarletteHTTPException)
def erro_http(request: Request, exc: StarletteHTTPException):
    nomes = {400: "requisicao_invalida", 404: "nao_encontrado", 405: "metodo_nao_permitido", 503: "servico_indisponivel"}
    return resposta_erro(exc.status_code, nomes.get(exc.status_code, "erro_http"), str(exc.detail))


@app.exception_handler(RequestValidationError)
def erro_validacao(request: Request, exc: RequestValidationError):
    # o erro padrao do FastAPI e uma lista tecnica em ingles. aqui junto num
    # texto so, em portugues, dizendo qual campo esta errado
    partes = []
    for item in exc.errors():
        campo = ".".join(str(p) for p in item["loc"] if p != "body")
        partes.append("%s: %s" % (campo or "corpo", item["msg"]))
    return resposta_erro(
        422, "entrada_invalida", "; ".join(partes),
        "Confira o formato do corpo no /docs. Ex.: {\"texto\": \"...\", \"tipo\": \"resumo\"}",
    )


@app.exception_handler(llm_local.ModeloIndisponivel)
def erro_modelo(request: Request, exc: llm_local.ModeloIndisponivel):
    return resposta_erro(
        503, "modelo_indisponivel", str(exc),
        "Rode a API na máquina local com requirements-llm.txt instalado. "
        "Na primeira vez é preciso internet para baixar o modelo (~1 GB).",
    )


@app.exception_handler(llm_local.TempoLimiteModelo)
def erro_tempo(request: Request, exc: llm_local.TempoLimiteModelo):
    return resposta_erro(
        504, "tempo_esgotado", str(exc),
        "Tente um texto menor ou aumente RADAR_LLM_TIMEOUT. Na CPU o modelo leva de 8 a 26 s com a máquina livre e pode passar de 1 minuto com ela ocupada.",
    )


@app.exception_handler(Exception)
def erro_inesperado(request: Request, exc: Exception):
    # ultima rede de seguranca: nada sai como traceback cru pro usuario
    return resposta_erro(
        500, "erro_interno", "Erro inesperado: %s" % exc.__class__.__name__,
        "Veja o terminal da API para o detalhe completo.",
    )


# ---- rotas

@app.get("/", tags=["info"])
def raiz():
    # rota de boas vindas, diz se os dados carregaram
    return {
        "projeto": "Radar Solar Municipal",
        "municipios_carregados": len(MUNICIPIOS),
        "documentacao": "/docs",
        "rotas": [
            "/municipios", "/municipios/{cod_ibge}", "/ranking", "/indicador-por-habitante",
            "/llm/status", "/processar_texto", "/resumo-municipio",
        ],
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


# ---- rotas com LLM local (TP4)

INSTRUCAO_RESUMO = (
    "Você explica notícias do setor elétrico para gestores de prefeituras. "
    "Resuma a notícia em um parágrafo corrido de no máximo 3 frases curtas, em "
    "português simples, sem tópicos e sem título. Na última frase diga se a notícia "
    "muda algo para quem tem ou quer instalar energia solar (geração distribuída). "
    "Use só informações que estão no texto."
)

INSTRUCAO_IMPACTO = (
    "Classifique a notícia em exatamente uma destas classes:\n"
    "afeta_gd = muda algo para a micro e minigeração distribuída (energia solar no telhado, "
    "compensação de créditos, conexão de geradores);\n"
    "afeta_consumidor = afeta os consumidores de energia em geral (tarifas, bandeiras, "
    "conta de luz), mas não a geração distribuída especificamente;\n"
    "nao_afeta = não afeta nenhum dos dois.\n"
    "Responda exatamente neste formato, em português:\n"
    "CLASSE: <classe>\nMOTIVO: <uma frase>"
)

# primeira versao pedia "3 a 4 frases sobre o municipio" e o modelo de 0,5B
# inventava coisa (botou o Rio "na regiao metropolitana de Sao Paulo" e uma
# porcentagem da populacao que nao existe). fechei o roteiro frase por frase e
# mandei a comparacao com a mediana ja calculada, pra ele so redigir
INSTRUCAO_MUNICIPIO = (
    "Você escreve para gestores de prefeituras que não são da área de energia. "
    "Escreva exatamente 3 frases curtas em português, num parágrafo só, usando os dados "
    "em JSON que o usuário enviar:\n"
    "Frase 1: a potência instalada de geração distribuída e o número de empreendimentos.\n"
    "Frase 2: a posição do município no estado e no Brasil.\n"
    "Frase 3: o que diz o campo comparacao_com_mediana_do_estado, em linguagem simples.\n"
    "Regras: copie os números exatamente como estão no JSON; não escreva nenhum outro "
    "número; não cite outras cidades, estados, porcentagens nem datas."
)


def numeros_do_texto(texto):
    # pega "384,69", "40.363", "12" etc. tiro ponto e virgula do fim pq o
    # numero pode estar colado no ponto final da frase
    return [n.rstrip(".,") for n in re.findall(r"\d[\d.,]*", texto)]


def conferir_numeros(saida, fonte):
    # validacao da resposta do LLM: todo numero que o modelo escreveu tem que
    # aparecer no texto de origem. devolve os que nao aparecem (provavel
    # invencao). nao bloqueia a resposta, mas vai junto pra pessoa ver
    permitidos = set(numeros_do_texto(fonte))
    # aceito tambem o numero sem separador de milhar (40363 = 40.363)
    permitidos |= {n.replace(".", "") for n in permitidos}
    return sorted({n for n in numeros_do_texto(saida) if n not in permitidos and n.replace(".", "") not in permitidos})


def extrair_classe(resposta):
    # o modelo pequeno nem sempre segue o formato a risca, entao procuro qual
    # das classes aparece primeiro no texto que ele devolveu
    texto = resposta.lower().replace("não afeta", "nao_afeta").replace("nao afeta", "nao_afeta")
    posicoes = {}
    for classe in ("afeta_gd", "afeta_consumidor", "nao_afeta"):
        achou = texto.find(classe)
        if achou >= 0:
            posicoes[classe] = achou
    if not posicoes:
        return "indefinida"
    return min(posicoes, key=posicoes.get)


@lru_cache(maxsize=256)
def processar_com_cache(tipo, texto):
    # cache em memoria: o mesmo texto com o mesmo tipo nao roda o modelo de
    # novo. lru_cache nao guarda excecao, entao erro nunca fica preso no cache
    if tipo == TipoAnalise.impacto_gd.value:
        return llm_local.gerar(INSTRUCAO_IMPACTO, texto, max_tokens=80)
    return llm_local.gerar(INSTRUCAO_RESUMO, texto, max_tokens=160)


@lru_cache(maxsize=1024)
def resumo_municipio_com_cache(cod_ibge, dados_json):
    return llm_local.gerar(INSTRUCAO_MUNICIPIO, dados_json, max_tokens=140)


def formata_br(numero, casas=1):
    # 12345.6 -> "12.345,6" (o modelo copia melhor o numero ja no formato
    # que vai aparecer no texto)
    return ("{:,.%df}" % casas).format(numero).replace(",", "X").replace(".", ",").replace("X", ".")


def comparar_com_mediana(dados):
    # a conta fica no codigo, nao no modelo: modelo pequeno erra divisao
    if dados["municipios_na_uf"] == 1:
        return "é o único município da sua unidade da federação"
    if dados["mediana_potencia_uf_kw"] <= 0:
        return "a mediana do estado é zero"
    vezes = dados["potencia_total_kw"] / dados["mediana_potencia_uf_kw"]
    if vezes >= 1.1:
        return "tem %s vezes a potência do município típico do estado (mediana)" % formata_br(vezes, 1)
    if vezes <= 0.9:
        return "está abaixo do município típico do estado (mediana)"
    return "está na média do município típico do estado (mediana)"


@app.get("/llm/status", response_model=LLMStatus, tags=["LLM local"])
def llm_status():
    # diz se o modelo ja esta na memoria, sem forcar a carga
    return llm_local.status()


@app.post("/llm/carregar", response_model=LLMStatus, responses=ERROS_LLM, tags=["LLM local"])
def llm_carregar():
    # forca a carga do modelo (o app chama isso pra "aquecer" antes do usuario
    # pedir o primeiro texto). se falhar, o handler devolve 503
    llm_local.carregar_modelo()
    return llm_local.status()


@app.post("/processar_texto", response_model=ProcessarTextoResposta, responses=ERROS_LLM, tags=["LLM local"])
def processar_texto(entrada: ProcessarTextoEntrada):
    # POST: recebe um texto (ex.: noticia da ANEEL) e devolve o resumo em
    # linguagem simples ou a classificacao do impacto para a GD
    ja_tinha = processar_com_cache.cache_info().hits
    resultado, segundos = processar_com_cache(entrada.tipo.value, entrada.texto)
    em_cache = processar_com_cache.cache_info().hits > ja_tinha

    if not resultado:
        # o modelo devolveu vazio: e falha do modelo, nao do usuario
        raise HTTPException(status_code=502, detail="O modelo devolveu uma resposta vazia. Tente de novo.")

    classe = extrair_classe(resultado) if entrada.tipo == TipoAnalise.impacto_gd else None
    return {
        "tipo_analise": entrada.tipo,
        "texto_original": entrada.texto,
        "tamanho_texto": len(entrada.texto),
        "resultado": resultado,
        "classe": classe,
        "numeros_fora_dos_dados": conferir_numeros(resultado, entrada.texto),
        "modelo": llm_local.NOME_MODELO,
        "tempo_segundos": 0.0 if em_cache else segundos,
        "em_cache": em_cache,
        "aviso": AVISO_IA,
    }


@app.post("/resumo-municipio", response_model=ResumoMunicipioResposta, responses={**ERROS_LLM, 404: {"model": ErroResposta}}, tags=["LLM local"])
def resumo_municipio(entrada: ResumoMunicipioEntrada):
    # POST: monta o prompt com os numeros do municipio (os mesmos de
    # /municipios/{cod_ibge} + posicao no ranking) e pede um paragrafo pro gestor
    if MUNICIPIOS.empty:
        raise HTTPException(status_code=503, detail="Dados não carregados.")
    linha = MUNICIPIOS[MUNICIPIOS["CodMunicipioIbge"] == entrada.cod_ibge]
    if linha.empty:
        raise HTTPException(status_code=404, detail="Município %d não encontrado" % entrada.cod_ibge)
    linha = linha.iloc[0]

    # posicao = quantos municipios tem mais potencia que ele, mais um
    da_uf = MUNICIPIOS[MUNICIPIOS["uf"] == linha["uf"]]
    dados = {
        "potencia_total_kw": round(float(linha["potencia_total_kw"]), 2),
        "qtd_empreendimentos": int(linha["qtd_empreendimentos"]),
        "potencia_media_kw": round(float(linha["potencia_media_kw"]), 2),
        "posicao_na_uf": int((da_uf["potencia_total_kw"] > linha["potencia_total_kw"]).sum()) + 1,
        "municipios_na_uf": len(da_uf),
        "posicao_no_brasil": int((MUNICIPIOS["potencia_total_kw"] > linha["potencia_total_kw"]).sum()) + 1,
        "municipios_no_brasil": len(MUNICIPIOS),
        "mediana_potencia_uf_kw": round(float(da_uf["potencia_total_kw"].median()), 2),
    }

    # o que vai pro prompt: os mesmos numeros, ja formatados em portugues
    para_prompt = {
        "municipio": "%s (%s)" % (linha["municipio"], linha["uf"]),
        "potencia_instalada": "%s MW" % formata_br(dados["potencia_total_kw"] / 1000, 2),
        "empreendimentos": formata_br(dados["qtd_empreendimentos"], 0),
        "potencia_media_por_empreendimento": "%s kW" % formata_br(dados["potencia_media_kw"], 1),
        "posicao_no_estado": "%dº de %d municípios" % (dados["posicao_na_uf"], dados["municipios_na_uf"]),
        "posicao_no_brasil": "%sº de %s municípios" % (formata_br(dados["posicao_no_brasil"], 0), formata_br(dados["municipios_no_brasil"], 0)),
        "mediana_do_estado": "%s MW" % formata_br(dados["mediana_potencia_uf_kw"] / 1000, 2),
        "comparacao_com_mediana_do_estado": comparar_com_mediana(dados),
    }
    dados_json = json.dumps(para_prompt, ensure_ascii=False, indent=1)

    ja_tinha = resumo_municipio_com_cache.cache_info().hits
    resumo, segundos = resumo_municipio_com_cache(entrada.cod_ibge, dados_json)
    em_cache = resumo_municipio_com_cache.cache_info().hits > ja_tinha
    if not resumo:
        raise HTTPException(status_code=502, detail="O modelo devolveu uma resposta vazia. Tente de novo.")

    return {
        "cod_ibge": entrada.cod_ibge,
        "municipio": linha["municipio"],
        "uf": linha["uf"],
        # tira espaco duplo e quebra de linha que o modelo as vezes deixa
        "resumo": re.sub(r"\s+", " ", resumo),
        "dados_usados": dados,
        "numeros_fora_dos_dados": conferir_numeros(resumo, dados_json),
        "modelo": llm_local.NOME_MODELO,
        "tempo_segundos": 0.0 if em_cache else segundos,
        "em_cache": em_cache,
        "aviso": AVISO_IA,
    }
