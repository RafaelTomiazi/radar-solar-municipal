# Dashboard do Radar Solar Municipal. pra rodar: streamlit run app.py
# TP1: painel demo com os dados da ANEEL
# TP2: filtros, exploracao por municipio, noticias da ANEEL (scraping),
#      upload/download de CSV, cache e estado de sessao

import os
import sys

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_EXTERNAL = os.path.join(RAIZ, "data", "external")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

# sem esse append o import de baixo nao acha o arquivo. achei essa solucao no
# stackoverflow, tentei fazer com pacote e __init__.py mas nao rolou
sys.path.append(os.path.join(RAIZ, "Code", "DataAcquisition"))
sys.path.append(os.path.join(RAIZ, "Code", "App"))
from fonte_dados import buscar_metadados  # noqa: E402
import dados_usuario  # noqa: E402
import textos  # noqa: E402

st.set_page_config(page_title="Radar Solar Municipal", page_icon="☀️", layout="wide")


# ---- carga dos dados (tudo com cache)

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
        # a amostra usa os nomes de coluna originais da ANEEL
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


@st.cache_data(show_spinner="Gerando a nuvem de palavras...")
def nuvem_e_termos(lista_textos, extras):
    # recebe tupla (e nao lista) pq o cache precisa de argumento hashable.
    # a nuvem e a parte mais lenta do app, entao so recalcula quando o filtro muda
    contagem = textos.contar_termos(lista_textos, extras)
    if not contagem:
        return None, pd.DataFrame(columns=["termo", "ocorrencias"])
    imagem = textos.gerar_nuvem(dict(contagem.most_common(200)))
    termos = pd.DataFrame(contagem.most_common(20), columns=["termo", "ocorrencias"])
    return imagem, termos


def grafico_barras(serie, titulo_valor, horizontal=True):
    # o st.bar_chart ordena pelo nome e na horizontal desenhava o eixo com
    # valor negativo, entao fiz com altair pra controlar a ordem das barras
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


# ---- estado de sessao

# tudo que precisa sobreviver entre um clique e outro fica no session_state.
# o setdefault so cria a chave na primeira execucao da sessao
st.session_state.setdefault("dados_usuario", None)
st.session_state.setdefault("arquivo_enviado", None)
st.session_state.setdefault("avisos_upload", [])
st.session_state.setdefault("historico", [])


def limpar_filtros():
    st.session_state["f_regioes"] = []
    st.session_state["f_ufs"] = []


def registrar_consulta():
    # guarda os municipios que a pessoa ja olhou nessa sessao
    escolhido = st.session_state.get("municipio_escolhido")
    historico = st.session_state["historico"]
    if escolhido and escolhido not in historico:
        historico.insert(0, escolhido)
        del historico[8:]


def remover_upload():
    st.session_state["dados_usuario"] = None
    st.session_state["arquivo_enviado"] = None
    st.session_state["avisos_upload"] = []


# ---- dados base

municipios, origem = carregar_municipios()

if municipios is None:
    st.error(
        "Não encontrei os dados processados nem a amostra. "
        "Rode `python Code/DataAcquisition/coleta_dados.py` e depois "
        "`python Code/DataPreparation/processa_dados.py`."
    )
    st.stop()

# se o usuario subiu um CSV, as colunas dele entram na base daqui pra frente
if st.session_state["dados_usuario"] is not None:
    base = dados_usuario.juntar(municipios, st.session_state["dados_usuario"])
    colunas_usuario = [c for c in st.session_state["dados_usuario"].columns if c != dados_usuario.COLUNA_CHAVE]
else:
    base = municipios.copy()
    colunas_usuario = []

base["rotulo"] = base["municipio"] + " - " + base["uf"]
base["potencia_mw"] = base["potencia_total_kw"] / 1000

# indicadores que aparecem nos seletores. os do upload entram no fim
INDICADORES = {
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
        INDICADORES[nome] = "kw_por_mil_" + coluna


# ---- barra lateral: filtros

with st.sidebar:
    st.header("☀️ Filtros")
    st.caption("Os filtros valem para as abas Panorama e Municípios e ficam guardados enquanto a sessão estiver aberta.")

    regioes = sorted(base["NomRegiao"].dropna().unique())
    st.multiselect("Região", regioes, key="f_regioes", placeholder="Todas")

    if st.session_state["f_regioes"]:
        ufs_possiveis = sorted(base.loc[base["NomRegiao"].isin(st.session_state["f_regioes"]), "uf"].unique())
    else:
        ufs_possiveis = sorted(base["uf"].dropna().unique())

    # se a pessoa tira uma regiao, as UFs dela precisam sair da selecao senao o
    # multiselect reclama de valor que nao esta nas opcoes
    st.session_state["f_ufs"] = [u for u in st.session_state.get("f_ufs", []) if u in ufs_possiveis]
    st.multiselect("UF", ufs_possiveis, key="f_ufs", placeholder="Todas")

    st.button("Limpar filtros", on_click=limpar_filtros, width="stretch")

    st.divider()
    st.subheader("Sua sessão")
    if st.session_state["arquivo_enviado"]:
        st.write("📎 Arquivo carregado: **%s**" % st.session_state["arquivo_enviado"])
    else:
        st.write("Nenhum arquivo enviado.")
    if st.session_state["historico"]:
        st.write("Municípios consultados:")
        for item in st.session_state["historico"]:
            st.caption("• " + item)

filtro = pd.Series(True, index=base.index)
if st.session_state["f_regioes"]:
    filtro &= base["NomRegiao"].isin(st.session_state["f_regioes"])
if st.session_state["f_ufs"]:
    filtro &= base["uf"].isin(st.session_state["f_ufs"])
filtrada = base[filtro]

if st.session_state["f_ufs"]:
    recorte = ", ".join(st.session_state["f_ufs"])
elif st.session_state["f_regioes"]:
    recorte = ", ".join(st.session_state["f_regioes"])
else:
    recorte = "Brasil"


# ---- cabecalho

st.title("☀️ Radar Solar Municipal")
st.markdown(
    "Geração distribuída de energia no Brasil por município · "
    "**Projeto de Bloco: IA Aplicada**, Instituto Infnet · Rafael Celestino Tomiazi"
)

data_referencia, origem_dado = consultar_metadados()
if origem_dado.startswith("API"):
    st.success("Base da ANEEL atualizada em %s. Fonte: %s." % (data_referencia, origem_dado))
elif data_referencia:
    st.warning("Base da ANEEL de %s. Fonte: %s." % (data_referencia, origem_dado))
else:
    st.error("Não consegui confirmar a data da base. Motivo: %s." % origem_dado)

if origem == "amostra":
    st.warning(
        "Exibindo a amostra versionada. Para o painel completo, rode os scripts "
        "de coleta e processamento descritos no README."
    )

aba_panorama, aba_municipios, aba_noticias, aba_dados, aba_sobre = st.tabs(
    ["📊 Panorama", "🏙️ Municípios", "📰 Notícias ANEEL", "📁 Seus dados", "ℹ️ Sobre o projeto"]
)


# ---- aba 1: panorama

with aba_panorama:
    st.header("Panorama: %s" % recorte)

    if filtrada.empty:
        st.info("Nenhum município com esse filtro.")
    else:
        total_kw = filtrada["potencia_total_kw"].sum()
        com_registro = int((filtrada["qtd_empreendimentos"] > 0).sum())

        # concentracao: quanto os 10% maiores municipios do recorte somam
        ordenado = filtrada["potencia_total_kw"].sort_values(ascending=False)
        top10 = ordenado.head(max(1, int(np.ceil(len(ordenado) * 0.1)))).sum()
        concentracao = top10 / total_kw * 100 if total_kw else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Potência instalada", "%.2f GW" % (total_kw / 1e6))
        m2.metric("Empreendimentos", "{:,}".format(int(filtrada["qtd_empreendimentos"].sum())).replace(",", "."))
        m3.metric("Municípios com adoção", "%d de %d" % (com_registro, len(filtrada)))
        m4.metric(
            "Potência nos 10% maiores",
            "%.1f%%" % concentracao,
            help="Participação dos 10% de municípios com mais potência no total do recorte.",
        )

        st.subheader("Comparação entre estados")
        indicador = st.selectbox("Indicador", list(INDICADORES), key="indicador_panorama")
        coluna = INDICADORES[indicador]

        # soma nao funciona pra media e pra indicador por habitante, entao
        # recalculo a razao no nivel da UF
        por_uf = filtrada.groupby("uf").agg(
            potencia_total_kw=("potencia_total_kw", "sum"),
            qtd_empreendimentos=("qtd_empreendimentos", "sum"),
        )
        if coluna == "potencia_mw":
            por_uf["valor"] = por_uf["potencia_total_kw"] / 1000
        elif coluna == "qtd_empreendimentos":
            por_uf["valor"] = por_uf["qtd_empreendimentos"]
        elif coluna == "potencia_media_kw":
            por_uf["valor"] = por_uf["potencia_total_kw"] / por_uf["qtd_empreendimentos"]
        else:
            coluna_original = coluna.replace("kw_por_mil_", "", 1)
            soma = filtrada.groupby("uf")[coluna_original].sum().replace(0, np.nan)
            por_uf["valor"] = por_uf["potencia_total_kw"] / soma * 1000

        grafico_barras(por_uf["valor"], indicador, horizontal=False)

        col_classe, col_fonte = st.columns(2)

        with col_classe:
            st.subheader("Potência por classe de consumo")
            por_classe = carregar("gd_por_classe.csv")
            if por_classe is not None:
                ufs_recorte = filtrada["uf"].unique()
                classe = (
                    por_classe[por_classe["SigUF"].isin(ufs_recorte)]
                    .groupby("DscClasseConsumo")["potencia_total_kw"].sum()
                    .div(1000).sort_values(ascending=False)
                )
                grafico_barras(classe, "MW")
            else:
                st.warning("Arquivo de classes não encontrado.")

        with col_fonte:
            st.subheader("Potência por fonte (Brasil)")
            por_fonte = carregar("gd_por_fonte.csv")
            if por_fonte is not None:
                st.caption("A radiação solar responde por 99,41% da potência instalada.")
                st.dataframe(por_fonte, width="stretch", hide_index=True, height=250)
            else:
                st.warning("Arquivo de fontes não encontrado.")


# ---- aba 2: municipios

with aba_municipios:
    st.header("Explorar municípios: %s" % recorte)

    if filtrada.empty:
        st.info("Nenhum município com esse filtro.")
    else:
        opcoes = filtrada.sort_values("potencia_total_kw", ascending=False)["rotulo"].tolist()
        # se o municipio escolhido antes saiu do filtro, volto pro primeiro da lista
        if st.session_state.get("municipio_escolhido") not in opcoes:
            st.session_state["municipio_escolhido"] = opcoes[0]

        escolhido = st.selectbox(
            "Município (digite para buscar)",
            opcoes,
            key="municipio_escolhido",
            on_change=registrar_consulta,
        )
        linha = base[base["rotulo"] == escolhido].iloc[0]

        mesma_uf = base[base["uf"] == linha["uf"]]
        pos_uf = int((mesma_uf["potencia_total_kw"] > linha["potencia_total_kw"]).sum()) + 1
        pos_br = int((base["potencia_total_kw"] > linha["potencia_total_kw"]).sum()) + 1
        percentil = (base["potencia_total_kw"] < linha["potencia_total_kw"]).mean() * 100
        mediana_uf = mesma_uf["potencia_total_kw"].median()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Potência instalada",
            "%.2f MW" % (linha["potencia_total_kw"] / 1000),
            delta="%.1f MW vs mediana da UF" % ((linha["potencia_total_kw"] - mediana_uf) / 1000),
        )
        c2.metric("Empreendimentos", "{:,}".format(int(linha["qtd_empreendimentos"])).replace(",", "."))
        c3.metric("Posição na UF", "%dº de %d" % (pos_uf, len(mesma_uf)))
        c4.metric("Posição no Brasil", "%dº" % pos_br, help="Percentil %.0f na potência instalada" % percentil)

        if colunas_usuario:
            st.caption("Dados do seu arquivo para este município:")
            st.dataframe(linha[colunas_usuario].to_frame().T, hide_index=True, width="stretch")

        st.divider()
        st.subheader("Ranking")

        r1, r2, r3 = st.columns([2, 1, 1])
        indicador_rank = r1.selectbox("Ordenar por", list(INDICADORES), key="indicador_ranking")
        ordem = r2.radio("Mostrar", ["Maiores", "Menores"], horizontal=True, key="ordem_ranking")
        quantidade = r3.slider("Quantidade", 5, 100, 20, step=5, key="qtd_ranking")

        coluna_rank = INDICADORES[indicador_rank]
        colunas_tabela = ["municipio", "uf", "NomRegiao", "qtd_empreendimentos", "potencia_mw", "potencia_media_kw"]
        if coluna_rank not in colunas_tabela:
            colunas_tabela.append(coluna_rank)

        ranking = (
            filtrada.dropna(subset=[coluna_rank])
            .sort_values(coluna_rank, ascending=(ordem == "Menores"))
            .head(quantidade)[colunas_tabela]
        )
        st.dataframe(
            ranking,
            width="stretch",
            hide_index=True,
            column_config={
                "municipio": "Município",
                "uf": "UF",
                "NomRegiao": "Região",
                "qtd_empreendimentos": st.column_config.NumberColumn("Empreendimentos", format="%d"),
                "potencia_mw": st.column_config.NumberColumn("Potência (MW)", format="%.2f"),
                "potencia_media_kw": st.column_config.NumberColumn("Média (kW)", format="%.1f"),
            },
        )
        st.download_button(
            "⬇️ Baixar ranking (CSV)",
            ranking.to_csv(index=False).encode("utf-8"),
            file_name="ranking_%s.csv" % recorte.replace(", ", "_").lower(),
            mime="text/csv",
        )

        st.divider()
        st.subheader("Comparar municípios")
        comparar = st.multiselect(
            "Escolha até 6 municípios",
            base["rotulo"].sort_values().tolist(),
            max_selections=6,
            key="comparar",
            placeholder="Ex.: Brasília - DF",
        )
        if comparar:
            indicador_comp = st.selectbox("Indicador da comparação", list(INDICADORES), key="indicador_comparacao")
            tabela_comp = base[base["rotulo"].isin(comparar)].set_index("rotulo")[INDICADORES[indicador_comp]]
            grafico_barras(tabela_comp, indicador_comp)


# ---- aba 3: noticias da ANEEL (scraping)

with aba_noticias:
    st.header("O que a ANEEL está publicando")
    noticias = carregar_noticias()

    if noticias is None:
        st.warning(
            "Arquivo de notícias não encontrado. Rode "
            "`python Code/DataAcquisition/scraping_noticias.py` para coletar."
        )
    else:
        st.caption(
            "Notícias extraídas do site da ANEEL com Beautiful Soup em %s "
            "(arquivo `data/external/noticias_aneel.csv`)." % noticias["coletado_em"].iloc[0]
        )

        f1, f2 = st.columns([2, 2])
        categorias = sorted(noticias["categoria"].unique())
        cat_escolhidas = f1.multiselect("Categoria", categorias, key="n_categorias", placeholder="Todas")
        busca = f2.text_input("Buscar no texto", key="n_busca", placeholder="Ex.: tarifa, solar, bandeira")

        f3, f4, f5 = st.columns([2, 1, 2])
        menor, maior = noticias["data"].min().date(), noticias["data"].max().date()
        periodo = f3.slider(
            "Período", min_value=menor, max_value=maior, value=(menor, maior), format="DD/MM/YYYY", key="n_periodo"
        )
        so_gd = f4.toggle("Só geração distribuída / solar", key="n_so_gd")
        ocultar = f5.text_input(
            "Esconder palavras da nuvem", key="n_ocultar", placeholder="separadas por vírgula"
        )

        selecao = noticias[
            (noticias["data"].dt.date >= periodo[0]) & (noticias["data"].dt.date <= periodo[1])
        ]
        if cat_escolhidas:
            selecao = selecao[selecao["categoria"].isin(cat_escolhidas)]
        if so_gd:
            selecao = selecao[selecao["tema_gd"]]
        if busca:
            alvo = (selecao["titulo"] + " " + selecao["descricao"] + " " + selecao["texto"]).str.lower()
            selecao = selecao[alvo.str.contains(busca.lower(), regex=False)]

        if selecao.empty:
            st.info("Nenhuma notícia com esses filtros.")
        else:
            n1, n2, n3, n4 = st.columns(4)
            n1.metric("Notícias", len(selecao))
            n2.metric("Categorias", selecao["categoria"].nunique())
            n3.metric("Palavras por notícia (média)", "%.0f" % selecao["qtd_palavras"].mean())
            n4.metric("Sobre GD / solar", int(selecao["tema_gd"].sum()))

            extras = tuple(p.strip() for p in ocultar.split(",") if p.strip())
            corpus = tuple((selecao["titulo"] + ". " + selecao["descricao"] + " " + selecao["texto"]).tolist())
            imagem, termos = nuvem_e_termos(corpus, extras)

            col_nuvem, col_termos = st.columns([3, 1])
            with col_nuvem:
                st.subheader("Nuvem de palavras")
                if imagem is not None:
                    st.image(imagem, width="stretch")
            with col_termos:
                st.subheader("Termos mais frequentes")
                st.dataframe(termos, hide_index=True, width="stretch", height=420)

            e1, e2 = st.columns(2)
            with e1:
                st.subheader("Notícias por categoria")
                grafico_barras(selecao["categoria"].value_counts(), "notícias")
            with e2:
                st.subheader("Notícias por mês")
                # so os meses que tem noticia, senao o grafico fica cheio de mes vazio
                por_mes = selecao.groupby(selecao["data"].dt.strftime("%Y-%m")).size().sort_index()
                st.bar_chart(por_mes, x_label="mês", y_label="notícias", color="#f59e0b")

            st.subheader("Últimas notícias")
            for _, noticia in selecao.sort_values("data", ascending=False).head(10).iterrows():
                with st.container(border=True):
                    st.markdown("**[%s](%s)**" % (noticia["titulo"], noticia["url"]))
                    st.caption("%s · %s" % (noticia["data"].strftime("%d/%m/%Y"), noticia["categoria"]))
                    st.write(noticia["descricao"])

            st.download_button(
                "⬇️ Baixar notícias filtradas (CSV)",
                selecao.drop(columns=["texto"]).to_csv(index=False).encode("utf-8"),
                file_name="noticias_aneel_filtradas.csv",
                mime="text/csv",
            )


# ---- aba 4: upload e download

with aba_dados:
    st.header("Complemente o painel com os seus dados")
    st.write(
        "Envie um CSV com o **código IBGE do município** e uma ou mais colunas numéricas "
        "(população, número de escolas, orçamento de um programa de incentivo...). "
        "As colunas entram no painel: viram indicadores como *kW por mil habitantes* nas abas "
        "Panorama e Municípios, e aparecem na ficha de cada município."
    )

    d1, d2 = st.columns(2)
    d1.download_button(
        "⬇️ Baixar modelo de CSV",
        dados_usuario.modelo_csv(),
        file_name="modelo_radar_solar.csv",
        mime="text/csv",
        width="stretch",
    )
    caminho_exemplo = os.path.join(PASTA_AMOSTRA, "exemplo_upload_populacao.csv")
    if os.path.exists(caminho_exemplo):
        with open(caminho_exemplo, "rb") as arquivo:
            d2.download_button(
                "⬇️ Baixar exemplo pronto: população 2026 (IBGE)",
                arquivo.read(),
                file_name="exemplo_upload_populacao.csv",
                mime="text/csv",
                width="stretch",
            )

    enviado = st.file_uploader("Enviar CSV", type=["csv"], key="upload_csv")

    # o file_uploader roda de novo a cada clique, entao so processo quando o
    # arquivo muda. o resultado fica no session_state e as outras abas usam de la
    if enviado is not None:
        assinatura = "%s (%d bytes)" % (enviado.name, enviado.size)
        if assinatura != st.session_state["arquivo_enviado"]:
            try:
                tabela, numericas, avisos = dados_usuario.validar(dados_usuario.ler_csv(enviado.getvalue()))
            except ValueError as erro:
                st.error(str(erro))
            else:
                st.session_state["dados_usuario"] = tabela
                st.session_state["arquivo_enviado"] = assinatura
                st.session_state["avisos_upload"] = avisos
                st.rerun()

    if st.session_state["dados_usuario"] is not None:
        enviados = st.session_state["dados_usuario"]
        casados = enviados[dados_usuario.COLUNA_CHAVE].isin(municipios[dados_usuario.COLUNA_CHAVE]).sum()

        st.success(
            "**%s** carregado: %d linhas, %d municípios encontrados na base da ANEEL. "
            "Novas colunas: %s." % (
                st.session_state["arquivo_enviado"], len(enviados), casados, ", ".join(colunas_usuario)
            )
        )
        for aviso in st.session_state["avisos_upload"]:
            st.warning(aviso)

        st.subheader("Base combinada")
        combinada = filtrada.drop(columns=["rotulo"])
        st.dataframe(combinada.head(200), width="stretch", hide_index=True)
        st.caption("Mostrando até 200 linhas do recorte atual (%s). O download traz todas." % recorte)

        b1, b2 = st.columns(2)
        b1.download_button(
            "⬇️ Baixar base combinada (CSV)",
            combinada.to_csv(index=False).encode("utf-8"),
            file_name="radar_solar_combinado.csv",
            mime="text/csv",
            width="stretch",
        )
        b2.button("🗑️ Remover arquivo enviado", on_click=remover_upload, width="stretch")
    else:
        st.info("Nenhum arquivo carregado nesta sessão. Os indicadores extras aparecem depois do envio.")

    st.divider()
    st.subheader("Baixar os dados do projeto")
    p1, p2, p3 = st.columns(3)
    p1.download_button(
        "Municípios (ANEEL + IBGE)",
        municipios.to_csv(index=False).encode("utf-8"),
        file_name="cobertura_municipios.csv",
        mime="text/csv",
        width="stretch",
    )
    classe_csv = carregar("gd_por_classe.csv")
    if classe_csv is not None:
        p2.download_button(
            "Por UF e classe de consumo",
            classe_csv.to_csv(index=False).encode("utf-8"),
            file_name="gd_por_classe.csv",
            mime="text/csv",
            width="stretch",
        )
    noticias_csv = carregar_noticias()
    if noticias_csv is not None:
        p3.download_button(
            "Notícias da ANEEL (scraping)",
            noticias_csv.to_csv(index=False).encode("utf-8"),
            file_name="noticias_aneel.csv",
            mime="text/csv",
            width="stretch",
        )


# ---- aba 5: sobre (conteudo do TP1)

with aba_sobre:
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
    esq, dir_ = st.columns(2)

    with esq:
        st.subheader("Fontes de dados")
        st.markdown(
            """
            - [Portal de Dados Abertos da ANEEL](https://dadosabertos.aneel.gov.br/)
            - [Relação de empreendimentos de geração distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)
            - [Notícias da ANEEL (scraping)](https://www.gov.br/aneel/pt-br/assuntos/noticias)
            - [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
            - [API SIDRA do IBGE, estimativas de população](https://apisidra.ibge.gov.br/)
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
    "Dados: ANEEL, licença ODbL, referência de 21/08/2026. Municípios e população: IBGE. "
    "Notícias: gov.br/aneel. TP2 da disciplina."
)
