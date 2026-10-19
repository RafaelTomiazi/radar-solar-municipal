# Pagina Sobre: problema, objetivos, ODS e links. era a aba 5 do TP2

import streamlit as st

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
        - Disponibilizar os dados por uma API, para outros sistemas consultarem (TP3)
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
        - [Notícias da ANEEL (Beautiful Soup)](https://www.gov.br/aneel/pt-br/assuntos/noticias)
        - [ONS, Energia Agora: carga e geração (Selenium)](https://www.ons.org.br/paginas/energia-agora/carga-e-geracao)
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
