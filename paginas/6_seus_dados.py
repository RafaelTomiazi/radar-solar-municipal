# Pagina Seus dados: upload de CSV do usuario e downloads.
# era a aba 4 do TP2

import os

import streamlit as st

import comum
import dados_usuario

base, municipios, origem, colunas_usuario, INDICADORES = comum.montar_base()
filtrada, recorte = comum.aplicar_filtros(base)


def remover_upload():
    st.session_state["dados_usuario"] = None
    st.session_state["arquivo_enviado"] = None
    st.session_state["avisos_upload"] = []


st.header("Complemente o painel com os seus dados")
st.write(
    "Envie um CSV com o **código IBGE do município** e uma ou mais colunas numéricas "
    "(população, número de escolas, orçamento de um programa de incentivo...). "
    "As colunas entram no painel: viram indicadores como *kW por mil habitantes* nas páginas "
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
caminho_exemplo = os.path.join(comum.PASTA_AMOSTRA, "exemplo_upload_populacao.csv")
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
# arquivo muda. o resultado fica no session_state e as outras paginas usam de la
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
p1, p2, p3, p4 = st.columns(4)
p1.download_button(
    "Municípios (ANEEL + IBGE)",
    municipios.to_csv(index=False).encode("utf-8"),
    file_name="cobertura_municipios.csv",
    mime="text/csv",
    width="stretch",
)
classe_csv = comum.carregar("gd_por_classe.csv")
if classe_csv is not None:
    p2.download_button(
        "Por UF e classe de consumo",
        classe_csv.to_csv(index=False).encode("utf-8"),
        file_name="gd_por_classe.csv",
        mime="text/csv",
        width="stretch",
    )
noticias_csv = comum.carregar_noticias()
if noticias_csv is not None:
    p3.download_button(
        "Notícias da ANEEL (scraping)",
        noticias_csv.to_csv(index=False).encode("utf-8"),
        file_name="noticias_aneel.csv",
        mime="text/csv",
        width="stretch",
    )
geracao_csv = comum.carregar_geracao_ons()
if geracao_csv is not None:
    p4.download_button(
        "Geração do ONS (Selenium)",
        geracao_csv.to_csv(index=False).encode("utf-8"),
        file_name="geracao_ons.csv",
        mime="text/csv",
        width="stretch",
    )
