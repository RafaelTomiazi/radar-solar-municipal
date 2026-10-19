# Project Charter

**Projeto:** Radar Solar Municipal
**Autor:** Rafael Celestino Tomiazi
**Disciplina:** Projeto de Bloco, Inteligência Artificial Aplicada, Instituto Infnet
**Professor:** Renan Silva Santos
**Data:** 24 de agosto de 2026 (TP1), atualizado em 21 de setembro de 2026 (TP2) e em 19 de outubro de 2026 (TP3)

## 1. Problema de negócio

A ANEEL publica a lista completa dos empreendimentos de micro e minigeração distribuída do Brasil. São 4,67 milhões de registros, 51,6 GW de potência instalada e 99,41% disso vem de energia solar.

O dado é aberto, mas vem em um arquivo Parquet de 101 MB com 31 colunas de nome técnico. Quem consegue abrir esse arquivo já trabalha com dados. O gestor municipal que precisaria da informação para justificar uma política de incentivo normalmente não tem equipe para isso.

Quando processei a base eu esperava achar municípios sem nenhuma adoção. Achei só quatro. Então o problema não é falta de adoção, é diferença de intensidade: os 10% de municípios com maior potência instalada concentram 58,7% do total do país, e o município mediano tem 3 MW contra 19,7 MW do município no percentil 90.

## 2. Objetivos

Objetivo geral: transformar a base bruta da ANEEL em um painel que mostre como a geração solar distribuída está espalhada pelo território brasileiro.

Objetivos específicos:

- Consolidar os 4,67 milhões de registros em indicadores por município, sem perder registro no caminho
- Incluir também os municípios que não têm nenhum empreendimento, usando a lista oficial do IBGE
- Mostrar os indicadores em um painel que qualquer pessoa consiga abrir e entender
- Manter o projeto reprodutível, de forma que outra pessoa consiga rodar tudo a partir do repositório
- Deixar o gestor explorar o dado sozinho, escolhendo região, UF, município e indicador, sem depender de alguém para gerar o recorte (TP2)
- Trazer o contexto regulatório para dentro do painel, com as notícias publicadas pela ANEEL (TP2)
- Permitir que o usuário complemente o painel com os dados que ele já tem, como população ou orçamento de um programa, e baixe o resultado (TP2)
- Disponibilizar os indicadores municipais por uma API, para que outro sistema, ou a própria camada de IA do TP4, consulte os dados sem depender dos arquivos (TP3)
- Colocar a GD instalada em perspectiva com o que o país está gerando, usando a geração por fonte do ONS (TP3)
- Organizar o painel em páginas separadas por assunto, com menu de navegação (TP3)

## 3. Escopo

**Está no escopo:** coleta automatizada na API da ANEEL e na API do IBGE, processamento que agrega os registros individuais em indicadores municipais, e um painel em Streamlit apresentando o resultado.

No TP2 o escopo passou a incluir também:

- extração das notícias do site da ANEEL com Beautiful Soup, com o texto completo de cada notícia salvo em CSV e TXT, e a exibição desse conteúdo no painel (nuvem de palavras, termos mais frequentes, notícias por categoria e por mês)
- interface interativa, com filtros de região e UF, busca de município, ranking configurável e comparação entre municípios
- upload de CSV pelo usuário, validado e combinado com a base pelo código IBGE, e download dos dados filtrados e combinados
- cache e estado de sessão, para o painel responder rápido e não perder as escolhas do usuário entre uma aba e outra
- estimativa de população do IBGE (API SIDRA), usada como exemplo de upload para calcular a potência por mil habitantes
- publicação do painel no Streamlit Community Cloud, com o código versionado no GitHub

No TP3 entraram:

- aplicação com múltiplas páginas e menu de navegação (`st.navigation`), com os filtros na barra lateral valendo para todas as páginas
- API com FastAPI (`Code/API/api.py`) com quatro rotas GET de consulta e uma rota POST de cálculo, documentada no Swagger em `/docs`, e uma página do app que consome essa API por HTTP
- extração da geração do Sistema Interligado Nacional por fonte na página "Energia Agora" do ONS, com Selenium, porque essa página monta os números por JavaScript
- planejamento das tarefas com LLM para o TP4, com uma página no app explicando cada uma

**Está fora do escopo:** previsão de adoção futura, dados de irradiação solar por coordenada (dependem de fonte paga), informação individual do titular do empreendimento e cálculo de retorno financeiro de instalação.

## 4. Metas

| Indicador | Meta |
|---|---|
| Municípios cobertos pelo painel | Os 5.571 do IBGE |
| Registros perdidos no processamento | Zero |
| Colunas com dado pessoal no arquivo processado | Zero |
| Tempo de carregamento do painel | Abaixo de 3 segundos |
| Data de referência do dado visível na tela | Sempre |
| Notícias da ANEEL com texto completo extraído | Todas as publicadas na listagem pública |
| Arquivo enviado pelo usuário que quebra o painel | Nenhum: arquivo inválido gera mensagem de erro, não exceção |
| Painel acessível sem instalar nada | Sim, publicado no Streamlit Community Cloud |
| Instalação do zero com `pip install -r requirements.txt` | Sem conflito de dependências |
| Rotas da API respondendo com dado válido para os 5.571 municípios | Todas (TP3). Código inexistente devolve 404, dado inválido devolve 422, nunca erro 500 |
| Passos para ver a API funcionando | Um só: `streamlit run app.py` já sobe a API junto (TP3) |
| Página que depende de dado coletado fora do ar | Mostra aviso com o comando para coletar, não quebra o app (TP3) |

## 5. Público-alvo e stakeholders

O público principal são os gestores de secretarias municipais de meio ambiente e de desenvolvimento econômico, principalmente de cidades pequenas e médias que não têm equipe de análise de dados. É quem precisa justificar uma decisão de incentivo e hoje não consegue abrir a base.

Como público secundário eu penso em cooperativas de energia e empresas integradoras, que avaliam onde vale expandir, e em pesquisadores e jornalistas que cobrem transição energética.

| Stakeholder | Papel |
|---|---|
| Secretarias municipais | Usuário principal |
| Cooperativas e integradores solares | Usuário secundário |
| Pesquisadores e jornalistas de dados | Usuário secundário |
| ANEEL e IBGE | Fornecedores dos dados (base de GD, notícias, municípios e população) |
| Instituto Infnet | Avaliador |
| Rafael Tomiazi | Desenvolvimento do projeto |

## 6. ESG e ODS

O projeto fica no pilar Ambiental, com um componente de Governança por usar dado público e tratar com cuidado as colunas de dado pessoal.

O ODS principal é o **7, Energia Limpa e Acessível**. O painel atua sobre a meta 7.2, que trata de aumentar a participação de renováveis na matriz, dando visibilidade a como essa participação está distribuída no território.

Como secundários eu vejo o **ODS 11, Cidades e Comunidades Sustentáveis**, pelo recorte municipal, o **ODS 13, Ação Contra a Mudança Global do Clima**, pela troca de fonte fóssil por renovável, e o **ODS 10, Redução das Desigualdades**, por causa da concentração de 58,7% da potência em 10% dos municípios.

## 7. Metodologia

Uso o TDSP para organizar o projeto e as pastas do repositório, e o CRISP-DM para orientar o ciclo analítico dentro da fase de dados. Os dois se encaixam bem: o TDSP diz onde cada artefato mora e o CRISP-DM diz como ir do dado bruto ao resultado.

As fases do TDSP aplicadas ao projeto:

| Fase do TDSP | Como se aplica aqui | Artefato | Situação |
|---|---|---|---|
| Business Understanding | Definição do problema, metas, público-alvo e ODS | Project Charter | Feito |
| Data Acquisition & Understanding | Coleta nas APIs da ANEEL e do IBGE, scraping das notícias da ANEEL (Beautiful Soup), geração do ONS (Selenium) e população do SIDRA | Data Summary Report | Atualizado no TP3 |
| Modeling | Engenharia dos atributos municipais a partir dos registros individuais. No TP4, prompts e uso de LLM sobre esses atributos | Model Report | Planejado (página Próximos passos: IA) |
| Deployment | Publicação do painel em Streamlit e da API com FastAPI | `app.py`, `paginas/`, `Code/API/api.py` | Terceira versão: multipágina com API |
| Customer Acceptance | Validação do painel com leitores fora da área técnica | Project Final Report | A fazer |

O CRISP-DM aparece dentro das duas fases de dados no ciclo de entender o negócio, entender o dado, preparar o dado e avaliar o resultado. Foi esse ciclo que me fez trocar a hipótese inicial do projeto: eu entrei querendo mapear vazios de adoção, olhei o dado, vi que quase não existem vazios, e voltei para redefinir a pergunta em cima da intensidade.

## 8. Riscos

A ANEEL parou de atualizar o dataset entre setembro e novembro de 2025 por causa da migração do sistema SISGD, então a fonte pode ficar parada por um tempo grande. Por isso o painel sempre mostra a data de referência do dado e de onde ele veio.

O arquivo bruto tem 101 MB e passa do limite de 100 MB por arquivo do GitHub. Deixei ele no `.gitignore` e o script de coleta reconstrói quando precisa.

Se a API da ANEEL estiver fora no momento em que alguém abrir o painel, o app cai em um cache local e avisa na tela que o dado é guardado.

O scraping depende do HTML do site da ANEEL. Se o layout mudar, o seletor para de achar as notícias. O script foi feito para parar com erro nesse caso, em vez de gravar um arquivo vazio por cima do que já existe, e o app continua funcionando com a última coleta versionada.

Durante o período eleitoral o site da ANEEL deixa públicas só as notícias recentes, e o arquivo por ano pede login. Por isso a coleta atual tem 83 notícias, a maior parte de julho a setembro de 2026, e só 5 delas falam de geração distribuída ou solar. Depois do período eleitoral vale rodar o scraping de novo para ampliar a base.

O arquivo enviado pelo usuário pode vir em formato diferente do esperado (separador, codificação, código IBGE com erro). O app valida o arquivo, descarta as linhas com código inválido ou repetido e mostra um aviso com a quantidade descartada.

O Selenium depende de ter o Chrome instalado na máquina que roda a coleta, e a página do ONS pode mudar o texto ou demorar para carregar. O script espera até 20 segundos pelos números e, se não aparecerem, para com erro sem gravar nada. O app mostra a última coleta versionada. A coleta também é uma fotografia de um momento: à noite a solar quase não gera, então o número depende da hora em que o script rodou, e a página deixa isso explícito.

A API e o app rodam juntos. Se a API não estiver no ar, o app tenta subir ela numa thread. Se mesmo assim ela não responder, só a página Consulta via API para de funcionar, com uma mensagem dizendo como subir a API, e o resto do painel segue lendo os arquivos.

Testando a API eu achei os 4 municípios do Amazonas sem nenhum empreendimento devolvendo erro 500, porque vinham com região e média vazias e valor vazio não vira JSON. Corrigi preenchendo a região pela UF e a média com zero na carga da API.

## 9. Revisão do problema no TP3

O problema de negócio continua o mesmo: o dado de geração distribuída é aberto mas inacessível para o gestor municipal, e a desigualdade está na intensidade da adoção, não na ausência. O que mudou com as ferramentas novas foi o alcance da solução.

Com a FastAPI, o painel deixou de ser a única porta de entrada para o dado. Um sistema da prefeitura, uma planilha ou um script consegue pedir a ficha de um município por HTTP. Isso também resolve um problema que eu teria no TP4: a LLM vai precisar consultar números exatos, e é mais seguro ela pedir para uma rota que devolve o valor do que eu colar a base inteira no prompt.

Com o Selenium, entrou uma pergunta que o painel não respondia: quanto da GD instalada está gerando de fato. A base da ANEEL diz quanto foi instalado, e o ONS diz quanto o país está gerando agora por fonte, com a MMGD separada. Na coleta de 19/10/2026 às 18h17 a MMGD gerava 195 MW, contra mais de 50 GW instalados, porque era fim de tarde. Uma coleta só não fecha conclusão, mas mostra que a métrica de potência instalada sozinha superestima a contribuição real da GD ao longo do dia.

Ajustei as metas na tabela da seção 4 para incluir a API e o comportamento das páginas novas quando falta dado.

## 10. Planejamento do uso de LLM (TP4)

Parti do que já está coletado para escolher as tarefas, em ordem de prioridade. O detalhe de cada uma está na página Próximos passos: IA do app.

| Tarefa | Dado de entrada | Para quê |
|---|---|---|
| Ficha do município em linguagem simples (geração de texto) | Rota `GET /municipios/{cod_ibge}` da API | Transformar posição, percentil e mediana em um parágrafo que o gestor entenda |
| Resumo das notícias da ANEEL (análise de texto) | Coluna `texto` das 83 notícias | Dizer em poucas linhas se a notícia muda algo para quem tem ou quer instalar solar |
| Classificação do impacto para GD (classificação) | As mesmas notícias | Substituir a marcação por palavra-chave, que acha só 5 de 83 notícias, por três classes: afeta GD, afeta consumidor em geral, não afeta |
| Perguntas e respostas (Q&A) | Rotas da API como ferramentas do modelo | Responder perguntas como "5 municípios do Piauí com mais potência" sem mexer em filtro. Fica por último por ser o mais arriscado |

Em todas, o número citado no texto gerado tem que vir do dado enviado ao modelo, a resposta aparece marcada como gerada por IA, a chave da API do modelo fica fora do código e as respostas ficam em cache por município e por notícia.
