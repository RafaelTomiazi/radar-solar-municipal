# Dashboard do TP1. pra rodar: streamlit run app.py

import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

# sem esse append o import de baixo nao acha o arquivo. achei essa solucao no
# stackoverflow, tentei fazer com pacote e __init__.py mas nao rolou
sys.path.append(os.path.join(RAIZ, "Code", "DataAcquisition"))
from fonte_dados import buscar_metadados  # noqa: E402

st.set_page_config(page_title="Radar Solar Municipal", page_icon="☀️", layout="wide")


@st.cache_data
def carregar(nome_arquivo, pasta=PASTA_PROCESSED):
    # sem o cache o streamlit releria os CSV do disco a cada clique
    caminho = os.path.join(pasta, nome_arquivo)
    try:
        return pd.read_csv(caminho)
    except FileNotFoundError:
        return None


# se o processado nao existir cai pra amostra versionada, que e o fallback
# que o professor cobrou na aula
def carregar_municipios():
    dados = carregar("cobertura_municipios.csv")
    if dados is not None:
        return dados, "completo"

    dados = carregar("amostra_gd_municipio.csv", PASTA_AMOSTRA)
    if dados is not None:
        return dados, "amostra"

    return None, "ausente"


@st.cache_data(ttl=3600)
def consultar_metadados():
    # a base nao muda de minuto em minuto, 1h de cache ja ta bom
    return buscar_metadados()


# ---- cabecalho

st.title("☀️ Radar Solar Municipal")
st.subheader("Acompanhamento da geração distribuída de energia no Brasil por município")

st.markdown(
    """
    **Projeto de Bloco: Inteligência Artificial Aplicada**, Instituto Infnet

    Aluno: Rafael Celestino Tomiazi
    """
)

st.divider()

# ---- problema e objetivo

col_esquerda, col_direita = st.columns([3, 2])

with col_esquerda:
    st.header("O problema de negócio")
    st.write(
        """
        A ANEEL publica a relação completa dos empreendimentos de micro e minigeração
        distribuída do país. São 4,67 milhões de registros em um arquivo Parquet de
        101 MB com 31 colunas de nomenclatura técnica.

        O dado é aberto, mas na prática só é utilizável por quem trabalha com
        processamento de dados. O gestor municipal que precisaria dessa informação
        para justificar uma política de incentivo à energia solar normalmente não
        tem equipe para abrir esse arquivo.

        Ao processar a base eu esperava encontrar municípios sem nenhuma adoção.
        Encontrei apenas quatro. O problema não é ausência, é intensidade: os 10%
        de municípios com maior potência instalada concentram 58,7% de todo o
        parque nacional, e o município mediano tem seis vezes menos potência que o
        município no percentil 90.
        """
    )

with col_direita:
    st.header("Objetivos")
    st.write(
        """
        - Consolidar os 4,67 milhões de registros em indicadores municipais
        - Incluir também os municípios sem nenhum empreendimento, usando a lista do IBGE
        - Situar cada município em relação à sua região e ao país
        - Manter o fluxo inteiro reprodutível a partir do repositório
        """
    )

    st.info(
        "**ODS 7 — Energia Limpa e Acessível.** Secundários: ODS 11, ODS 13 e ODS 10, "
        "este último pela concentração observada na distribuição da potência."
    )

st.divider()

# ---- indicadores

st.header("Panorama nacional")

# chamo a API ao vivo so pra pegar a data de referencia da base. se ela
# estiver fora entra o cache e eu aviso na tela de onde veio o dado
data_referencia, origem_dado = consultar_metadados()

if origem_dado.startswith("API"):
    st.success("Base da ANEEL atualizada em %s. Fonte: %s." % (data_referencia, origem_dado))
elif data_referencia:
    st.warning("Base da ANEEL de %s. Fonte: %s." % (data_referencia, origem_dado))
else:
    st.error("Não consegui confirmar a data da base. Motivo: %s." % origem_dado)

municipios, origem = carregar_municipios()
por_fonte = carregar("gd_por_fonte.csv")

if municipios is None:
    st.error(
        "Não encontrei os dados processados nem a amostra. "
        "Rode `python Code/DataAcquisition/coleta_dados.py` e depois "
        "`python Code/DataPreparation/processa_dados.py`."
    )
    st.stop()

if origem == "amostra":
    st.warning(
        "Exibindo a amostra versionada. Para o painel completo, rode os scripts "
        "de coleta e processamento descritos no README."
    )

col_pot = "potencia_total_kw"
total_mw = municipios[col_pot].sum() / 1000
com_registro = int((municipios["qtd_empreendimentos"] > 0).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Potência instalada", "%.1f GW" % (total_mw / 1000))
m2.metric("Empreendimentos", "%.2f milhões" % (municipios["qtd_empreendimentos"].sum() / 1e6))
m3.metric("Municípios com adoção", "%d" % com_registro)
m4.metric("Participação solar", "99,41%")

if por_fonte is not None:
    st.caption(
        "A radiação solar responde por 99,41% da potência instalada. "
        "As demais 16 fontes somam menos de 0,6%."
    )

st.divider()

# ---- amostra dos dados

st.header("Amostra dos dados")

aba_municipio, aba_bruto, aba_fonte = st.tabs(
    ["Agregado por município", "Registro bruto da ANEEL", "Por fonte de geração"]
)

with aba_municipio:
    st.write(
        "Resultado do pipeline de processamento. Uma linha por município, "
        "com quantidade de empreendimentos e potência instalada."
    )
    st.dataframe(
        municipios.sort_values(col_pot, ascending=False).head(50),
        width='stretch',
        hide_index=True,
    )

with aba_bruto:
    st.write(
        "Amostra do arquivo original da ANEEL, antes de qualquer transformação. "
        "As colunas com nome e documento do titular não são carregadas por decisão "
        "de privacidade."
    )
    dados2 = carregar("amostra_gd_bruto.csv", PASTA_AMOSTRA)
    if dados2 is not None:
        st.dataframe(dados2.head(50), width='stretch', hide_index=True)
    else:
        st.warning("Amostra do dado bruto não encontrada em Sample_Data.")

with aba_fonte:
    if por_fonte is not None:
        st.dataframe(por_fonte, width='stretch', hide_index=True)
        st.bar_chart(por_fonte.set_index("DscFonteGeracao")["potencia_total_kw"].head(6))
    else:
        st.warning("Arquivo de fontes não encontrado.")

st.divider()

# ---- links

st.header("Links úteis e fontes de inspiração")

esq, dir_ = st.columns(2)

with esq:
    st.subheader("Fontes de dados")
    st.markdown(
        """
        - [Portal de Dados Abertos da ANEEL](https://dadosabertos.aneel.gov.br/)
        - [Relação de empreendimentos de geração distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)
        - [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
        - [Painel de Micro e Minigeração Distribuída da EPE](https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/painel-de-dados-de-micro-e-minigeracao-distribuida-pdgd-)
        """
    )

with dir_:
    st.subheader("Iniciativas e inspiração")
    st.markdown(
        """
        - [Conecta Brasil](https://conectabrasil.org/home)
        - [Observatório do Terceiro Setor, projetos sociais](https://observatorio3setor.org.br/lista-conheca-projetos-sociais-de-15-causas-diferentes/)
        - [Objetivos de Desenvolvimento Sustentável, ONU Brasil](https://brasil.un.org/pt-br/sdgs)
        - [ABSOLAR, Associação Brasileira de Energia Solar Fotovoltaica](https://www.absolar.org.br/)
        """
    )

st.divider()
st.caption(
    "Dados: ANEEL, licença ODbL, referência de 21/08/2026. Municípios: IBGE. "
    "Demo desenvolvida para o TP1 da disciplina."
)
