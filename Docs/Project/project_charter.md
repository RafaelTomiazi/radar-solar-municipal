# Project Charter

**Projeto:** Radar Solar Municipal
**Autor:** Rafael Celestino Tomiazi
**Disciplina:** Projeto de Bloco, Inteligência Artificial Aplicada, Instituto Infnet
**Professor:** Renan Silva Santos
**Data:** 24 de agosto de 2026

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

## 3. Escopo

**Está no escopo:** coleta automatizada na API da ANEEL e na API do IBGE, processamento que agrega os registros individuais em indicadores municipais, e um painel em Streamlit apresentando o resultado.

**Está fora do escopo:** previsão de adoção futura, dados de irradiação solar por coordenada (dependem de fonte paga), informação individual do titular do empreendimento e cálculo de retorno financeiro de instalação.

## 4. Metas

| Indicador | Meta |
|---|---|
| Municípios cobertos pelo painel | Os 5.571 do IBGE |
| Registros perdidos no processamento | Zero |
| Colunas com dado pessoal no arquivo processado | Zero |
| Tempo de carregamento do painel | Abaixo de 3 segundos |
| Data de referência do dado visível na tela | Sempre |

## 5. Público-alvo e stakeholders

O público principal são os gestores de secretarias municipais de meio ambiente e de desenvolvimento econômico, principalmente de cidades pequenas e médias que não têm equipe de análise de dados. É quem precisa justificar uma decisão de incentivo e hoje não consegue abrir a base.

Como público secundário eu penso em cooperativas de energia e empresas integradoras, que avaliam onde vale expandir, e em pesquisadores e jornalistas que cobrem transição energética.

| Stakeholder | Papel |
|---|---|
| Secretarias municipais | Usuário principal |
| Cooperativas e integradores solares | Usuário secundário |
| Pesquisadores e jornalistas de dados | Usuário secundário |
| ANEEL e IBGE | Fornecedores dos dados |
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
| Data Acquisition & Understanding | Coleta nas APIs da ANEEL e do IBGE e inspeção do schema | Data Summary Report | Feito |
| Modeling | Engenharia dos atributos municipais a partir dos registros individuais | Model Report | A fazer |
| Deployment | Publicação do painel em Streamlit | `app.py` | Primeira versão feita |
| Customer Acceptance | Validação do painel com leitores fora da área técnica | Project Final Report | A fazer |

O CRISP-DM aparece dentro das duas fases de dados no ciclo de entender o negócio, entender o dado, preparar o dado e avaliar o resultado. Foi esse ciclo que me fez trocar a hipótese inicial do projeto: eu entrei querendo mapear vazios de adoção, olhei o dado, vi que quase não existem vazios, e voltei para redefinir a pergunta em cima da intensidade.

## 8. Riscos

A ANEEL parou de atualizar o dataset entre setembro e novembro de 2025 por causa da migração do sistema SISGD, então a fonte pode ficar parada por um tempo grande. Por isso o painel sempre mostra a data de referência do dado e de onde ele veio.

O arquivo bruto tem 101 MB e passa do limite de 100 MB por arquivo do GitHub. Deixei ele no `.gitignore` e o script de coleta reconstrói quando precisa.

Se a API da ANEEL estiver fora no momento em que alguém abrir o painel, o app cai em um cache local e avisa na tela que o dado é guardado.
