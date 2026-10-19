# Pagina Geracao agora: dado do ONS coletado com Selenium (novo no TP3).
# O painel mostra a GD instalada por municipio. Essa pagina coloca isso em
# perspectiva com o que o pais inteiro esta gerando naquele momento.

import streamlit as st

import comum

st.header("Geração do Sistema Interligado Nacional")
st.write(
    "Quanto cada fonte estava gerando no país no momento da coleta, segundo o "
    "Operador Nacional do Sistema Elétrico (ONS). A **MMGD** é a micro e minigeração "
    "distribuída, o mesmo tipo de empreendimento que o resto do painel mostra por município."
)

geracao = comum.carregar_geracao_ons()

if geracao is None or geracao.empty:
    st.warning(
        "Arquivo `data/external/geracao_ons.csv` não encontrado. Rode "
        "`python Code/DataAcquisition/scraping_ons_selenium.py` para coletar."
    )
    st.stop()

st.caption(
    "Coletado com **Selenium** em %s (atualização do ONS: %s). A página do ONS monta "
    "esses números com JavaScript depois de abrir, por isso o Beautiful Soup sozinho "
    "não enxerga os valores." % (geracao["coletado_em"].iloc[0], geracao["atualizacao_ons"].iloc[0])
)

total = geracao["geracao_mw"].sum()
renovavel = geracao[geracao["fonte"].isin(["Hidráulica", "Eólica", "Solar", "MMGD"])]["geracao_mw"].sum()
mmgd = geracao.loc[geracao["fonte"] == "MMGD", "geracao_mw"].sum()
solar = geracao.loc[geracao["fonte"] == "Solar", "geracao_mw"].sum()

g1, g2, g3, g4 = st.columns(4)
g1.metric("Geração total", ("%.1f GW" % (total / 1000)).replace(".", ","))
g2.metric("Renovável", ("%.1f%%" % (renovavel / total * 100)).replace(".", ","))
g3.metric("MMGD (distribuída)", ("%.1f MW" % mmgd).replace(".", ","))
g4.metric("Solar centralizada", ("%.1f MW" % solar).replace(".", ","))

st.subheader("Geração por fonte (MW)")
comum.grafico_barras(geracao.set_index("fonte")["geracao_mw"], "MW")

st.dataframe(
    geracao[["fonte", "geracao_mw", "participacao_pct"]],
    hide_index=True,
    width="stretch",
    column_config={
        "fonte": "Fonte",
        "geracao_mw": st.column_config.NumberColumn("Geração (MW)", format="%.1f"),
        "participacao_pct": st.column_config.NumberColumn("Participação (%)", format="%.2f"),
    },
)

# comparacao que liga as duas fontes do projeto: o que esta instalado (ANEEL)
# contra o que esta gerando agora (ONS)
base, *_ = comum.montar_base()
instalada_mw = base["potencia_total_kw"].sum() / 1000
st.subheader("Instalado x gerando agora")
st.write(
    "A base da ANEEL soma **%s MW** de GD instalada. No momento da coleta, a MMGD gerava "
    "**%s MW**, ou %s da capacidade. A diferença vem da hora do dia: painel solar só gera "
    "com sol, e uma coleta feita à noite mostra a MMGD quase zerada. Para o TP4 a ideia é "
    "coletar várias vezes ao longo do dia e ver essa curva."
    % (
        "{:,.0f}".format(instalada_mw).replace(",", "."),
        ("%.1f" % mmgd).replace(".", ","),
        ("%.1f%%" % (mmgd / instalada_mw * 100)).replace(".", ","),
    )
)

st.download_button(
    "⬇️ Baixar geração do ONS (CSV)",
    geracao.to_csv(index=False).encode("utf-8"),
    file_name="geracao_ons.csv",
    mime="text/csv",
)
