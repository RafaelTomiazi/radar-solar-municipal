# Pagina Consulta via API: o app conversando com a API FastAPI (novo no TP3).
# Aqui o painel nao le o CSV direto, ele pede os dados pra API por HTTP, do
# mesmo jeito que qualquer outro programa faria.

import pandas as pd
import streamlit as st

import comum


def contar_consulta():
    st.session_state["consultas_api"] += 1


st.header("Consulta via API")
st.write(
    "Esta página não lê os arquivos do projeto: ela pede os dados para a API do Radar "
    "Solar, feita com **FastAPI**. O código da API está em `Code/API/api.py` e a "
    "documentação interativa fica em `/docs` no endereço da API."
)

if comum.api_no_ar():
    st.success("API no ar em %s · [abrir documentação (Swagger)](%s/docs)" % (comum.API_URL, comum.API_URL))
else:
    st.error(
        "A API não respondeu em %s. Suba ela com "
        "`uvicorn Code.API.api:app --port 8000` e recarregue a página." % comum.API_URL
    )
    st.stop()

with st.expander("Rotas disponíveis"):
    st.markdown(
        """
| Método | Rota | O que faz |
|---|---|---|
| GET | `/` | Status da API e quantos municípios foram carregados |
| GET | `/municipios?uf=RJ&limite=50` | Lista municípios, com filtro opcional por UF |
| GET | `/municipios/{cod_ibge}` | Ficha de um município pelo código IBGE |
| GET | `/ranking?por=potencia&uf=SP&top=10` | Ranking por potência, quantidade ou potência média |
| POST | `/indicador-por-habitante` | Recebe código IBGE e população, devolve kW por mil habitantes |
        """
    )

aba_ranking, aba_ficha, aba_post = st.tabs(["GET /ranking", "GET /municipios/{cod_ibge}", "POST /indicador-por-habitante"])

# ---- GET ranking

with aba_ranking:
    c1, c2, c3 = st.columns(3)
    criterio = c1.selectbox("Critério", ["potencia", "quantidade", "media"], key="api_criterio")
    uf = c2.text_input("UF (vazio = Brasil)", max_chars=2, key="api_uf").strip().upper()
    top = c3.slider("Top", 3, 30, 10, key="api_top")

    parametros = {"por": criterio, "top": top}
    if uf:
        parametros["uf"] = uf

    if st.button("Consultar ranking", key="btn_ranking", on_click=contar_consulta):
        resposta, erro = comum.chamar_api("GET", "/ranking", params=parametros)
        if erro:
            st.error(erro)
        else:
            tabela = pd.DataFrame(resposta["ranking"])
            st.write("Ranking por **%s** · %s" % (resposta["criterio"], resposta["uf"]))
            coluna_valor = [c for c in tabela.columns if c not in ("municipio", "uf")][0]
            comum.grafico_barras(tabela.set_index("municipio")[coluna_valor], coluna_valor)
            with st.expander("Resposta JSON da API"):
                st.json(resposta)

# ---- GET municipio

with aba_ficha:
    base, *_ = comum.montar_base()
    rotulos = base.sort_values("potencia_total_kw", ascending=False)[["rotulo", "CodMunicipioIbge"]]
    escolhido = st.selectbox("Município", rotulos["rotulo"].tolist(), key="api_municipio")
    cod = int(rotulos.loc[rotulos["rotulo"] == escolhido, "CodMunicipioIbge"].iloc[0])
    st.caption("Chamada: `GET %s/municipios/%d`" % (comum.API_URL, cod))

    if st.button("Buscar ficha", key="btn_ficha", on_click=contar_consulta):
        resposta, erro = comum.chamar_api("GET", "/municipios/%d" % cod)
        if erro:
            st.error(erro)
        else:
            f1, f2, f3 = st.columns(3)
            f1.metric("Potência instalada", ("%.2f MW" % (resposta["potencia_total_kw"] / 1000)).replace(".", ","))
            f2.metric("Empreendimentos", "{:,}".format(resposta["qtd_empreendimentos"]).replace(",", "."))
            f3.metric("Média por empreendimento", ("%.1f kW" % resposta["potencia_media_kw"]).replace(".", ","))
            st.json(resposta)

# ---- POST indicador por habitante

with aba_post:
    st.write(
        "Envia para a API o código IBGE de um município e a população, e a API devolve a "
        "potência instalada por mil habitantes. É o mesmo cálculo da página *Seus dados*, "
        "só que feito do lado da API."
    )
    # st.form junta os campos e so manda quando clica, senao cada digito
    # disparava uma chamada
    with st.form("form_post"):
        p1, p2 = st.columns(2)
        cod_post = p1.number_input("Código IBGE", min_value=1000000, max_value=9999999, value=3304557, step=1)
        populacao = p2.number_input("População", min_value=1, value=6211000, step=1000)
        # o contador vai no on_click pq a barra lateral e desenhada antes da
        # pagina. contando aqui dentro o numero aparecia atrasado em um
        enviar = st.form_submit_button("Enviar (POST)", on_click=contar_consulta)

    if enviar:
        corpo = {"cod_ibge": int(cod_post), "populacao": int(populacao)}
        st.caption("Corpo enviado: `%s`" % corpo)
        resposta, erro = comum.chamar_api("POST", "/indicador-por-habitante", json=corpo)
        if erro:
            st.error(erro)
        else:
            st.metric(
                "%s - %s" % (resposta["municipio"], resposta["uf"]),
                ("%.1f kW por mil habitantes" % resposta["kw_por_mil_habitantes"]).replace(".", ","),
            )
            st.json(resposta)
