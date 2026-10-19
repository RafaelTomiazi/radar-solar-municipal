# Pagina Municipios: ficha de um municipio, ranking e comparacao.
# era a aba 2 do TP2

import streamlit as st

import comum

base, municipios, origem, colunas_usuario, INDICADORES = comum.montar_base()
filtrada, recorte = comum.aplicar_filtros(base)


def registrar_consulta():
    # guarda os municipios que a pessoa ja olhou nessa sessao
    escolhido = st.session_state.get("municipio_escolhido")
    historico = st.session_state["historico"]
    if escolhido and escolhido not in historico:
        historico.insert(0, escolhido)
        del historico[8:]


st.header("Explorar municípios: %s" % recorte)

if filtrada.empty:
    st.info("Nenhum município com esse filtro.")
    st.stop()

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
    ("%.2f MW" % (linha["potencia_total_kw"] / 1000)).replace(".", ","),
    delta=("%.1f MW vs mediana da UF" % ((linha["potencia_total_kw"] - mediana_uf) / 1000)).replace(".", ","),
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
    comum.grafico_barras(tabela_comp, indicador_comp)
