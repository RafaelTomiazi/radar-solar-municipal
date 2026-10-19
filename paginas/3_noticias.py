# Pagina Noticias: o que foi extraido do site da ANEEL com Beautiful Soup.
# era a aba 3 do TP2

import streamlit as st

import comum

st.header("O que a ANEEL está publicando")
noticias = comum.carregar_noticias()

if noticias is None:
    st.warning(
        "Arquivo de notícias não encontrado. Rode "
        "`python Code/DataAcquisition/scraping_noticias.py` para coletar."
    )
    st.stop()

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
ocultar = f5.text_input("Esconder palavras da nuvem", key="n_ocultar", placeholder="separadas por vírgula")

selecao = noticias[(noticias["data"].dt.date >= periodo[0]) & (noticias["data"].dt.date <= periodo[1])]
if cat_escolhidas:
    selecao = selecao[selecao["categoria"].isin(cat_escolhidas)]
if so_gd:
    selecao = selecao[selecao["tema_gd"]]
if busca:
    alvo = (selecao["titulo"] + " " + selecao["descricao"] + " " + selecao["texto"]).str.lower()
    selecao = selecao[alvo.str.contains(busca.lower(), regex=False)]

if selecao.empty:
    st.info("Nenhuma notícia com esses filtros.")
    st.stop()

n1, n2, n3, n4 = st.columns(4)
n1.metric("Notícias", len(selecao))
n2.metric("Categorias", selecao["categoria"].nunique())
n3.metric("Palavras por notícia (média)", "%.0f" % selecao["qtd_palavras"].mean())
n4.metric("Sobre GD / solar", int(selecao["tema_gd"].sum()))

extras = tuple(p.strip() for p in ocultar.split(",") if p.strip())
corpus = tuple((selecao["titulo"] + ". " + selecao["descricao"] + " " + selecao["texto"]).tolist())
imagem, termos = comum.nuvem_e_termos(corpus, extras)

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
    comum.grafico_barras(selecao["categoria"].value_counts(), "notícias")
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
