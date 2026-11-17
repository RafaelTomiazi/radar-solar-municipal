# Pagina IA local (LLM): novo no TP4. O app manda texto pra API e a API roda um
# modelo de linguagem da HuggingFace na propria maquina (Qwen2.5-0.5B-Instruct).
# Toda resposta aparece marcada como gerada por IA, com os numeros originais
# do lado pra pessoa conferir.

import streamlit as st

import comum

# a primeira chamada pode levar ~1 min (carga do modelo), as outras de 8 s a
# mais de 1 min, dependendo de quanto a maquina esta ocupada. fica acima do
# tempo limite da API (180 s) pra quem avisa o estouro ser a API, com o 504
TIMEOUT_LLM = 240


def contar_consulta():
    st.session_state["consultas_api"] += 1


st.header("IA local: resumo e classificação com LLM")
st.write(
    "Aqui o painel usa um modelo de linguagem (**Qwen2.5-0.5B-Instruct**, da HuggingFace) que roda "
    "**na própria máquina**, sem mandar nada para serviço na nuvem. O app chama a API FastAPI e a API "
    "chama o modelo pela biblioteca Transformers. O código está em `Code/API/llm_local.py` e as rotas "
    "em `Code/API/api.py`."
)

if not comum.api_no_ar():
    st.error("A API não respondeu em %s. Suba ela com `uvicorn Code.API.api:app --port 8000`." % comum.API_URL)
    st.stop()

# ---- status do modelo
status, erro = comum.chamar_api("GET", "/llm/status")
if erro:
    st.error(erro)
    st.stop()

if status["carregado"]:
    st.success("Modelo **%s** carregado na memória." % status["modelo"])
elif not status["bibliotecas_instaladas"]:
    # e o que acontece no Streamlit Cloud: la nao instalo torch (pesado demais
    # pro plano gratuito). a pagina explica em vez de quebrar
    st.warning(
        "Este ambiente não tem `torch` e `transformers` instalados, então o modelo não roda aqui "
        "(é o caso da versão publicada no Streamlit Cloud). As rotas respondem **503** com a explicação. "
        "Para usar, rode o projeto localmente com `pip install -r requirements-llm.txt`."
    )
else:
    st.info("O modelo ainda não foi carregado. A primeira chamada leva cerca de 1 minuto.")
    if st.button("Carregar modelo agora", on_click=contar_consulta):
        with st.spinner("Carregando o modelo (na primeira vez ele é baixado, ~1 GB)..."):
            _, erro = comum.chamar_api("POST", "/llm/carregar", timeout=600)
        if erro:
            st.error(erro)
        else:
            st.rerun()

with st.expander("Rotas de LLM da API"):
    st.markdown(
        """
| Método | Rota | O que faz |
|---|---|---|
| GET | `/llm/status` | Diz qual modelo, se está carregado e se as bibliotecas existem |
| POST | `/llm/carregar` | Carrega o modelo na memória (aquecimento) |
| POST | `/processar_texto` | `{"texto", "tipo"}`: tipo `resumo` ou `impacto_gd` |
| POST | `/resumo-municipio` | `{"cod_ibge"}`: parágrafo sobre a GD do município para o gestor |

Erros sempre no mesmo formato: `{"codigo", "erro", "detail", "dica"}`. Códigos usados:
422 (entrada inválida), 404 (município não existe), 502 (modelo devolveu vazio),
503 (modelo indisponível), 504 (passou do tempo limite) e 500 (erro inesperado).
        """
    )

aba_noticia, aba_municipio, aba_livre = st.tabs(
    ["Notícia da ANEEL", "Ficha do município", "Texto livre"]
)


def avisar_numeros(resposta):
    # a API confere se cada numero que o modelo escreveu existe na origem
    if resposta["numeros_fora_dos_dados"]:
        st.warning(
            "⚠️ O modelo citou números que não estão nos dados de origem: %s. "
            "Desconsidere esses números." % ", ".join(resposta["numeros_fora_dos_dados"])
        )
    else:
        st.caption("✅ Todos os números do texto gerado conferem com os dados de origem.")


def mostrar_resultado(resposta):
    # mesmo bloco pras tres abas: resultado, metadados e o JSON cru
    st.markdown("**Resultado (%s):**" % resposta["tipo_analise"])
    if resposta.get("classe"):
        nomes = {
            "afeta_gd": "🟢 Afeta a geração distribuída",
            "afeta_consumidor": "🟡 Afeta o consumidor em geral",
            "nao_afeta": "⚪ Não afeta",
            "indefinida": "❔ O modelo não respondeu uma das três classes",
        }
        st.subheader(nomes[resposta["classe"]])
    st.info(resposta["resultado"])
    avisar_numeros(resposta)
    st.caption(
        "🤖 %s · %s · %s" % (
            resposta["aviso"],
            "veio do cache" if resposta["em_cache"] else "%.1f s" % resposta["tempo_segundos"],
            "%d caracteres de entrada" % resposta["tamanho_texto"],
        )
    )
    with st.expander("Resposta JSON da API"):
        st.json(resposta)


# ---- noticia da ANEEL

with aba_noticia:
    noticias = comum.carregar_noticias()
    if noticias is None:
        st.warning("Arquivo de notícias não encontrado. Rode `python Code/DataAcquisition/scraping_noticias.py`.")
        st.stop()
    titulo = st.selectbox("Notícia", noticias["titulo"].tolist(), key="llm_noticia")
    noticia = noticias[noticias["titulo"] == titulo].iloc[0]
    tipo = st.radio(
        "O que fazer", ["resumo", "impacto_gd"], horizontal=True, key="llm_tipo",
        format_func=lambda t: "Resumir em linguagem simples" if t == "resumo" else "Classificar o impacto para GD",
    )
    st.caption(
        "%s · %s · marcação por palavra-chave (TP2): %s" % (
            noticia["data"], noticia["categoria"], "fala de GD" if noticia["tema_gd"] else "não fala de GD",
        )
    )
    with st.expander("Texto original da notícia"):
        st.write(noticia["texto"])

    if st.button("Processar com o LLM", key="btn_llm_noticia", on_click=contar_consulta):
        with st.spinner("O modelo está lendo a notícia..."):
            resposta, erro = comum.chamar_api(
                "POST", "/processar_texto", timeout=TIMEOUT_LLM,
                json={"texto": noticia["texto"][:6000], "tipo": tipo},
            )
        if erro:
            st.error(erro)
        else:
            mostrar_resultado(resposta)

# ---- ficha do municipio

with aba_municipio:
    base, *_ = comum.montar_base()
    rotulos = base.sort_values("potencia_total_kw", ascending=False)[["rotulo", "CodMunicipioIbge"]]
    escolhido = st.selectbox("Município", rotulos["rotulo"].tolist(), key="llm_municipio")
    cod = int(rotulos.loc[rotulos["rotulo"] == escolhido, "CodMunicipioIbge"].iloc[0])

    if st.button("Gerar ficha em linguagem simples", key="btn_llm_municipio", on_click=contar_consulta):
        with st.spinner("O modelo está escrevendo..."):
            resposta, erro = comum.chamar_api("POST", "/resumo-municipio", timeout=TIMEOUT_LLM, json={"cod_ibge": cod})
        if erro:
            st.error(erro)
        else:
            esquerda, direita = st.columns([3, 2])
            with esquerda:
                st.markdown("**Texto gerado para o gestor:**")
                st.info(resposta["resumo"])
                avisar_numeros(resposta)
                st.caption("🤖 %s" % resposta["aviso"])
            with direita:
                # os numeros originais do lado, pra conferir se o modelo nao inventou
                d = resposta["dados_usados"]
                st.markdown("**Números enviados ao modelo:**")
                st.metric("Potência instalada", ("%.2f MW" % (d["potencia_total_kw"] / 1000)).replace(".", ","))
                st.metric("Empreendimentos", "{:,}".format(d["qtd_empreendimentos"]).replace(",", "."))
                st.metric("Posição na UF", "%dº de %d" % (d["posicao_na_uf"], d["municipios_na_uf"]))
                st.metric("Posição no Brasil", "%dº de %d" % (d["posicao_no_brasil"], d["municipios_no_brasil"]))
            with st.expander("Resposta JSON da API"):
                st.json(resposta)

# ---- texto livre (mostra tambem o tratamento de erro)

with aba_livre:
    st.write(
        "Cole qualquer texto (entre 20 e 6.000 caracteres). Vale testar um texto curto demais para "
        "ver a API recusando com erro 422 e a mensagem explicando o motivo."
    )
    with st.form("form_llm_livre"):
        texto = st.text_area("Texto", height=180, key="llm_texto_livre")
        tipo_livre = st.selectbox("Tipo de análise", ["resumo", "impacto_gd"], key="llm_tipo_livre")
        enviar = st.form_submit_button("Enviar (POST /processar_texto)", on_click=contar_consulta)
    if enviar:
        # nao valido aqui de proposito: quem valida e a API (Response/Request
        # Models), e a pagina so mostra o erro que ela devolver
        with st.spinner("Processando..."):
            resposta, erro = comum.chamar_api(
                "POST", "/processar_texto", timeout=TIMEOUT_LLM, json={"texto": texto, "tipo": tipo_livre}
            )
        if erro:
            st.error(erro)
        else:
            mostrar_resultado(resposta)
