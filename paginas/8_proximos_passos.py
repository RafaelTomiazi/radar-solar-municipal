# Pagina Proximos passos: o planejamento do uso de LLM no TP4 (novo no TP3).
# Ainda nao tem LLM rodando aqui. A ideia e deixar claro, com os dados que eu ja
# tenho, onde cada tarefa de LLM entra e o que falta preparar.

import streamlit as st

import comum

st.header("Próximos passos: IA com LLM")
st.write(
    "No TP4 o painel ganha recursos de LLM. Em vez de escolher a tarefa primeiro e "
    "procurar dado depois, partir do que já está coletado e ver onde um modelo de "
    "linguagem resolve algo que hoje o painel não resolve."
)

noticias = comum.carregar_noticias()
geracao = comum.carregar_geracao_ons()
base, *_ = comum.montar_base()

d1, d2, d3 = st.columns(3)
d1.metric("Municípios com indicadores", "{:,}".format(len(base)).replace(",", "."))
d2.metric("Notícias com texto completo", len(noticias) if noticias is not None else 0)
d3.metric("Fontes do ONS coletadas", len(geracao) if geracao is not None else 0)

st.subheader("Onde cada tarefa de LLM entra")

planos = [
    (
        "1. Ficha do município em linguagem simples (geração de texto)",
        "Prioridade 1",
        "Indicadores do município pela rota `GET /municipios/{cod_ibge}` da API: potência, "
        "empreendimentos, posição na UF e no Brasil, comparação com a mediana.",
        "O gestor municipal, que é o público principal, não lê ranking e percentil. A LLM "
        "transforma os números em um parágrafo do tipo *seu município está entre os 20% com "
        "menos potência do estado, com média de X kW por instalação*.",
        "Nova rota `POST /resumo-municipio` na API, que monta o prompt com os números e "
        "devolve o texto. O prompt vai ter instrução de não inventar número: todo valor "
        "citado tem que vir do JSON enviado.",
    ),
    (
        "2. Resumo das notícias da ANEEL (análise de texto)",
        "Prioridade 2",
        "Coluna `texto` de `noticias_aneel.csv`, com média de 264 palavras por notícia.",
        "Hoje a página de notícias mostra a nuvem de palavras e o resumo oficial. A LLM pode "
        "gerar um resumo focado na pergunta *isso muda alguma coisa para quem tem ou quer "
        "instalar solar?*, que é o que interessa ao público do painel.",
        "Resumir uma vez por notícia e salvar o resultado em CSV, para não chamar o modelo a "
        "cada visita na página. Mesmo esquema de cache que já uso nos outros dados.",
    ),
    (
        "3. Classificação do impacto da notícia para GD (classificação)",
        "Prioridade 3",
        "As mesmas notícias. Hoje a marcação `tema_gd` é feita por palavra-chave e acha "
        "só 5 de 83 notícias.",
        "Palavra-chave perde notícia de tarifa que afeta a compensação de quem tem solar sem "
        "citar a palavra *solar*. Em vez de sentimento positivo/negativo, que não diz muito "
        "aqui, a classe seria: *afeta GD*, *afeta consumidor em geral* ou *não afeta*.",
        "Comparar a classificação da LLM com a de palavra-chave em uma amostra que eu mesmo "
        "rotular, para ver se a LLM acerta mais.",
    ),
    (
        "4. Perguntas e respostas sobre os dados (Q&A)",
        "Se der tempo",
        "As rotas da API (`/ranking`, `/municipios`) como ferramentas que o modelo chama.",
        "Deixar o usuário perguntar *quais os 5 municípios do Piauí com mais potência?* em "
        "texto, sem mexer em filtro.",
        "É o mais arriscado dos quatro: o modelo precisa escolher a rota e os parâmetros "
        "certos. Por isso fica por último, depois que as rotas estiverem estáveis.",
    ),
]

for titulo, prioridade, dado, por_que, como in planos:
    with st.container(border=True):
        st.markdown("**%s** · `%s`" % (titulo, prioridade))
        st.markdown("**Dado usado:** %s" % dado)
        st.markdown("**Por que:** %s" % por_que)
        st.markdown("**Como:** %s" % como)

st.subheader("Cuidados")
st.write(
    "A chave da API do modelo vai em `.env` ou `.streamlit/secrets.toml`, os dois já "
    "estão no `.gitignore`, nunca no código. Toda resposta gerada vai aparecer marcada "
    "como texto gerado por IA, com os números originais do lado para conferência. E as "
    "chamadas ficam em cache por município e por notícia, porque o dado de origem muda "
    "pouco e não faz sentido pagar a mesma chamada várias vezes."
)
