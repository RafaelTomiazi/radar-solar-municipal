# Project Charter

**Projeto:** Radar Solar Municipal
**Autor:** Rafael Celestino Tomiazi
**Disciplina:** Projeto de Bloco, Inteligência Artificial Aplicada, Instituto Infnet
**Professor:** Renan Silva Santos
**Data:** 24 de agosto de 2026 (TP1), atualizado em 21 de setembro de 2026 (TP2)

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

## 3. Escopo

**Está no escopo:** coleta automatizada na API da ANEEL e na API do IBGE, processamento que agrega os registros individuais em indicadores municipais, e um painel em Streamlit apresentando o resultado.

No TP2 o escopo passou a incluir também:

- extração das notícias do site da ANEEL com Beautiful Soup, com o texto completo de cada notícia salvo em CSV e TXT, e a exibição desse conteúdo no painel (nuvem de palavras, termos mais frequentes, notícias por categoria e por mês)
- interface interativa, com filtros de região e UF, busca de município, ranking configurável e comparação entre municípios
- upload de CSV pelo usuário, validado e combinado com a base pelo código IBGE, e download dos dados filtrados e combinados
- cache e estado de sessão, para o painel responder rápido e não perder as escolhas do usuário entre uma aba e outra
- estimativa de população do IBGE (API SIDRA), usada como exemplo de upload para calcular a potência por mil habitantes
- publicação do painel no Streamlit Community Cloud, com o código versionado no GitHub

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
| Data Acquisition & Understanding | Coleta nas APIs da ANEEL e do IBGE, scraping das notícias da ANEEL e população do SIDRA | Data Summary Report | Atualizado no TP2 |
| Modeling | Engenharia dos atributos municipais a partir dos registros individuais | Model Report | A fazer |
| Deployment | Publicação do painel em Streamlit | `app.py` | Segunda versão publicada no Streamlit Community Cloud |
| Customer Acceptance | Validação do painel com leitores fora da área técnica | Project Final Report | A fazer |

O CRISP-DM aparece dentro das duas fases de dados no ciclo de entender o negócio, entender o dado, preparar o dado e avaliar o resultado. Foi esse ciclo que me fez trocar a hipótese inicial do projeto: eu entrei querendo mapear vazios de adoção, olhei o dado, vi que quase não existem vazios, e voltei para redefinir a pergunta em cima da intensidade.

## 8. Riscos

A ANEEL parou de atualizar o dataset entre setembro e novembro de 2025 por causa da migração do sistema SISGD, então a fonte pode ficar parada por um tempo grande. Por isso o painel sempre mostra a data de referência do dado e de onde ele veio.

O arquivo bruto tem 101 MB e passa do limite de 100 MB por arquivo do GitHub. Deixei ele no `.gitignore` e o script de coleta reconstrói quando precisa.

Se a API da ANEEL estiver fora no momento em que alguém abrir o painel, o app cai em um cache local e avisa na tela que o dado é guardado.

O scraping depende do HTML do site da ANEEL. Se o layout mudar, o seletor para de achar as notícias. O script foi feito para parar com erro nesse caso, em vez de gravar um arquivo vazio por cima do que já existe, e o app continua funcionando com a última coleta versionada.

Durante o período eleitoral o site da ANEEL deixa públicas só as notícias recentes, e o arquivo por ano pede login. Por isso a coleta atual tem 83 notícias, a maior parte de julho a setembro de 2026, e só 5 delas falam de geração distribuída ou solar. Depois do período eleitoral vale rodar o scraping de novo para ampliar a base.

O arquivo enviado pelo usuário pode vir em formato diferente do esperado (separador, codificação, código IBGE com erro). O app valida o arquivo, descarta as linhas com código inválido ou repetido e mostra um aviso com a quantidade descartada.
