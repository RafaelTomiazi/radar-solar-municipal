# Pagina Panorama: totais do recorte e comparacao entre estados.
# era a aba 1 do TP2

import numpy as np
import streamlit as st

import comum

base, municipios, origem, colunas_usuario, INDICADORES = comum.montar_base()
filtrada, recorte = comum.aplicar_filtros(base)

st.header("Panorama: %s" % recorte)

if filtrada.empty:
    st.info("Nenhum município com esse filtro.")
    st.stop()

total_kw = filtrada["potencia_total_kw"].sum()
com_registro = int((filtrada["qtd_empreendimentos"] > 0).sum())

# concentracao: quanto os 10% maiores municipios do recorte somam
ordenado = filtrada["potencia_total_kw"].sort_values(ascending=False)
top10 = ordenado.head(max(1, int(np.ceil(len(ordenado) * 0.1)))).sum()
concentracao = top10 / total_kw * 100 if total_kw else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Potência instalada", ("%.2f GW" % (total_kw / 1e6)).replace(".", ","))
m2.metric("Empreendimentos", "{:,}".format(int(filtrada["qtd_empreendimentos"].sum())).replace(",", "."))
m3.metric("Municípios com adoção", "%d de %d" % (com_registro, len(filtrada)))
m4.metric(
    "Potência nos 10% maiores",
    ("%.1f%%" % concentracao).replace(".", ","),
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

comum.grafico_barras(por_uf["valor"], indicador, horizontal=False)

col_classe, col_fonte = st.columns(2)

with col_classe:
    st.subheader("Potência por classe de consumo")
    por_classe = comum.carregar("gd_por_classe.csv")
    if por_classe is not None:
        ufs_recorte = filtrada["uf"].unique()
        classe = (
            por_classe[por_classe["SigUF"].isin(ufs_recorte)]
            .groupby("DscClasseConsumo")["potencia_total_kw"].sum()
            .div(1000).sort_values(ascending=False)
        )
        comum.grafico_barras(classe, "MW")
    else:
        st.warning("Arquivo de classes não encontrado.")

with col_fonte:
    st.subheader("Potência por fonte (Brasil)")
    por_fonte = comum.carregar("gd_por_fonte.csv")
    if por_fonte is not None:
        st.caption("A radiação solar responde por 99,41% da potência instalada.")
        st.dataframe(por_fonte, width="stretch", hide_index=True, height=250)
    else:
        st.warning("Arquivo de fontes não encontrado.")
