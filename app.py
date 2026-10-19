# Dashboard do Radar Solar Municipal. pra rodar: streamlit run app.py
# TP1: painel demo com os dados da ANEEL
# TP2: filtros, exploracao por municipio, noticias da ANEEL (scraping),
#      upload/download de CSV, cache e estado de sessao
# TP3: virou app multipagina (pasta paginas/), com menu de navegacao, pagina de
#      geracao do ONS coletada com Selenium e pagina que consome a API FastAPI
#
# Esse arquivo agora e so a "casca": configura a pagina, monta a barra lateral
# com os filtros (que valem pra todas as paginas) e chama a pagina escolhida.
# O conteudo de cada pagina fica em paginas/, e o codigo comum em Code/App/comum.py

import os
import sys

import streamlit as st

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(RAIZ, "Code", "App"))
import comum  # noqa: E402

st.set_page_config(page_title="Radar Solar Municipal", page_icon="☀️", layout="wide")


# ---- estado de sessao

# tudo que precisa sobreviver entre um clique e outro, e entre uma pagina e
# outra, fica no session_state. o setdefault so cria na primeira execucao
st.session_state.setdefault("dados_usuario", None)
st.session_state.setdefault("arquivo_enviado", None)
st.session_state.setdefault("avisos_upload", [])
st.session_state.setdefault("historico", [])
st.session_state.setdefault("f_regioes", [])
st.session_state.setdefault("f_ufs", [])
st.session_state.setdefault("consultas_api", 0)


def limpar_filtros():
    st.session_state["f_regioes"] = []
    st.session_state["f_ufs"] = []


# sobe a API do FastAPI junto com o app se ela ainda nao estiver rodando
comum.iniciar_api_local()


# ---- menu de navegacao

# st.navigation monta o menu na barra lateral. separei as paginas em secoes
# pra ficar claro o que e analise, o que e coleta e o que e o projeto
paginas = {
    "Análise": [
        st.Page("paginas/1_panorama.py", title="Panorama", icon="📊", default=True),
        st.Page("paginas/2_municipios.py", title="Municípios", icon="🏙️"),
    ],
    "Dados coletados": [
        st.Page("paginas/3_noticias.py", title="Notícias ANEEL", icon="📰"),
        st.Page("paginas/4_geracao_ons.py", title="Geração agora (ONS)", icon="⚡"),
        st.Page("paginas/5_api.py", title="Consulta via API", icon="🔌"),
        st.Page("paginas/6_seus_dados.py", title="Seus dados", icon="📁"),
    ],
    "Projeto": [
        st.Page("paginas/7_sobre.py", title="Sobre o projeto", icon="ℹ️"),
        st.Page("paginas/8_proximos_passos.py", title="Próximos passos: IA", icon=":material/smart_toy:"),
    ],
}
navegacao = st.navigation(paginas)


# ---- barra lateral: filtros (aparecem em todas as paginas)

base, municipios, origem, _, _ = comum.montar_base()

with st.sidebar:
    st.header("☀️ Filtros")
    st.caption("Valem para Panorama e Municípios e ficam guardados enquanto a sessão estiver aberta.")

    if base is not None:
        regioes = sorted(base["NomRegiao"].dropna().unique())
        st.multiselect("Região", regioes, key="f_regioes", placeholder="Todas")

        if st.session_state["f_regioes"]:
            ufs_possiveis = sorted(base.loc[base["NomRegiao"].isin(st.session_state["f_regioes"]), "uf"].unique())
        else:
            ufs_possiveis = sorted(base["uf"].dropna().unique())

        # se a pessoa tira uma regiao, as UFs dela saem da selecao senao o
        # multiselect reclama de valor que nao esta nas opcoes
        st.session_state["f_ufs"] = [u for u in st.session_state["f_ufs"] if u in ufs_possiveis]
        st.multiselect("UF", ufs_possiveis, key="f_ufs", placeholder="Todas")

        st.button("Limpar filtros", on_click=limpar_filtros, width="stretch")

    st.divider()
    st.subheader("Sua sessão")
    if st.session_state["arquivo_enviado"]:
        st.write("📎 Arquivo carregado: **%s**" % st.session_state["arquivo_enviado"])
    else:
        st.write("Nenhum arquivo enviado.")
    if st.session_state["consultas_api"]:
        st.write("🔌 Consultas feitas à API: %d" % st.session_state["consultas_api"])
    if st.session_state["historico"]:
        st.write("Municípios consultados:")
        for item in st.session_state["historico"]:
            st.caption("• " + item)


# ---- cabecalho comum

st.title("☀️ Radar Solar Municipal")
st.markdown(
    "Geração distribuída de energia no Brasil por município · "
    "**Projeto de Bloco: IA Aplicada**, Instituto Infnet · Rafael Celestino Tomiazi"
)

if base is None:
    st.error(
        "Não encontrei os dados processados nem a amostra. "
        "Rode `python Code/DataAcquisition/coleta_dados.py` e depois "
        "`python Code/DataPreparation/processa_dados.py`."
    )
    st.stop()

data_referencia, origem_dado = comum.consultar_metadados()
if origem_dado.startswith("API"):
    st.success("Base da ANEEL atualizada em %s. Fonte: %s." % (data_referencia, origem_dado))
elif data_referencia:
    st.warning("Base da ANEEL de %s. Fonte: %s." % (data_referencia, origem_dado))
else:
    st.error("Não consegui confirmar a data da base. Motivo: %s." % origem_dado)

if origem == "amostra":
    st.warning("Exibindo a amostra versionada. Para o painel completo, rode os scripts do README.")

navegacao.run()

st.divider()
st.caption(
    "Dados: ANEEL (licença ODbL), IBGE e ONS. Notícias: gov.br/aneel. "
    "Ferramenta de IA usada no desenvolvimento: Claude (Anthropic). TP3 da disciplina."
)
