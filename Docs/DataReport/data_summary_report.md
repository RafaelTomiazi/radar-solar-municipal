# Data Summary Report

**Projeto:** Radar Solar Municipal
**Autor:** Rafael Celestino Tomiazi
**Data:** 24 de agosto de 2026 (TP1), atualizado em 21 de setembro de 2026 (TP2)

O Data Summary Report é o documento da fase de Data Acquisition & Understanding do TDSP. A primeira versão, do TP1, cobria a base da ANEEL e a malha do IBGE. Nesta versão do TP2 entraram três fontes novas: as notícias do site da ANEEL, extraídas com Beautiful Soup, a estimativa de população do IBGE e os arquivos que o próprio usuário envia pelo painel. Documentei só as colunas que eu uso de fato, não as 31 do arquivo original da ANEEL.

## 1. Fontes de dados

### ANEEL, empreendimentos de geração distribuída

Acesso pela API do CKAN em `https://dadosabertos.aneel.gov.br/api/3/action/package_show`, sem chave. Arquivo Parquet de 101 MB, 4.673.268 linhas e 31 colunas. Licença Open Data Commons ODbL, atualização verificada em 21/08/2026.

É a fonte principal. Cada linha é um empreendimento de micro ou minigeração ligado à rede, com localização, fonte de energia, classe de consumo e potência instalada.

Consulto a API em vez de fixar o link do arquivo porque a URL direta muda quando a ANEEL republica o dataset.

### IBGE, malha de municípios

Acesso em `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`, JSON, sem chave. Devolve os 5.571 municípios do Brasil com código oficial, nome e hierarquia territorial.

Uso como referência territorial. É ela que garante que município sem nenhum empreendimento apareça no painel, porque na base da ANEEL só existe linha para quem tem instalação.

### ANEEL, notícias do site (novo no TP2)

Extração com Beautiful Soup em `https://www.gov.br/aneel/pt-br/assuntos/noticias`, página pública, sem chave. O script `Code/DataAcquisition/scraping_noticias.py` percorre a listagem, que vem paginada de 30 em 30 pelo parâmetro `b_start:int`, pega data, categoria, título, resumo e link de cada notícia e depois entra em cada uma para ler o texto completo. Entre as requisições há uma pausa para não sobrecarregar o site. O `robots.txt` do gov.br não bloqueia essa área.

A coleta de 21/09/2026 trouxe 83 notícias, publicadas entre 15/03/2022 e 18/09/2026, em 20 categorias, com média de 264 palavras por notícia.

### IBGE, estimativa de população (novo no TP2)

Acesso pela API SIDRA em `https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last`, JSON, sem chave. Tabela 6579, variável 9324 (população residente estimada), todos os municípios, último ano disponível. Traz os 5.571 municípios com a estimativa de 2026, que soma 214,2 milhões de habitantes. O script é o `Code/DataAcquisition/coleta_populacao.py`.

### Dados enviados pelo usuário (novo no TP2)

Pela aba Seus dados o usuário envia um CSV com o código IBGE do município e uma ou mais colunas numéricas, como população, número de escolas ou orçamento de um programa. O arquivo não é gravado no servidor: ele fica só na sessão do usuário, é validado e combinado com a base da ANEEL pelo código IBGE.

### Objetivo de uso de cada fonte

| Fonte | Objetivo de uso no projeto | Onde aparece no painel |
|---|---|---|
| ANEEL, empreendimentos de GD | Medir a adoção da geração distribuída por município: quantidade, potência total e potência média | Panorama e Municípios |
| IBGE, malha de municípios | Garantir os 5.571 municípios no painel, inclusive os sem instalação, com nome oficial, UF e região | Panorama, Municípios e filtros |
| API da ANEEL (metadados) | Mostrar a data de referência da base, para o usuário nunca ver um número sem saber de quando ele é | Topo do painel |
| ANEEL, notícias | Dar o contexto regulatório: o que a agência está discutindo (tarifas, leilões, consultas públicas, regras de GD) e como isso muda com o tempo | Notícias ANEEL |
| IBGE, população | Transformar potência absoluta em indicador relativo (kW por mil habitantes), que compara municípios de tamanhos diferentes | Exemplo pronto de upload |
| Arquivo do usuário | Deixar o gestor cruzar o dado da ANEEL com a informação que ele já tem sobre o município | Seus dados, Panorama e Municípios |

## 2. Dicionário de dados

Colunas que leio do arquivo da ANEEL:

| Coluna | Tipo | Para que uso |
|---|---|---|
| `SigUF` | string | Agregação por estado |
| `NomRegiao` | string | Comparar o município com a região dele |
| `CodMunicipioIbge` | int64 | Chave de junção com o IBGE |
| `NomMunicipio` | string | Exibição no painel |
| `DscClasseConsumo` | string | Perfil de quem gera (Residencial, Comercial, Industrial, Rural e Serviço Público) |
| `DscFonteGeracao` | string | Separar a geração solar das outras fontes |
| `DscPorte` | string | Diferenciar microgeração de minigeração |
| `MdaPotenciaInstaladaKW` | double | Métrica principal, potência instalada em kW |
| `DthAtualizaCadastralEmpreend` | date32 | Verificar a defasagem do dado |

Colunas que uso do IBGE:

| Coluna | Tipo | Para que uso |
|---|---|---|
| `id` | int64 | Código do município, chave de junção |
| `nome` | string | Nome oficial |
| `microrregiao.mesorregiao.UF.sigla` | string | UF de referência |

Colunas do arquivo de notícias (`data/external/noticias_aneel.csv`):

| Coluna | Tipo | Para que uso |
|---|---|---|
| `data` | date | Filtro de período e gráfico de notícias por mês |
| `categoria` | string | Filtro e gráfico por categoria. Normalizada, porque o site às vezes escreve "Tarifas" e às vezes "TARIFAS" |
| `titulo` | string | Exibição e nuvem de palavras |
| `descricao` | string | Resumo exibido na lista de notícias |
| `url` | string | Link para a notícia original. Também serve para tirar duplicadas |
| `texto` | string | Texto completo, base da nuvem de palavras e da busca |
| `tema_gd` | bool | Marca as notícias que citam geração distribuída, micro ou minigeração, solar ou fotovoltaica |
| `qtd_palavras` | int | Estatística de tamanho das notícias |
| `coletado_em` | string | Data e hora da coleta, mostrada na tela |

O `data/external/noticias_aneel.txt` tem o mesmo conteúdo só em texto (título, resumo e corpo), uma notícia por linha.

Colunas do exemplo de população (`Sample_Data/exemplo_upload_populacao.csv`):

| Coluna | Tipo | Para que uso |
|---|---|---|
| `CodMunicipioIbge` | int64 | Chave de junção com a base da ANEEL |
| `populacao` | int64 | Divisor do indicador kW por mil habitantes |
| `ano` | int64 | Ano da estimativa. Como é igual em todas as linhas, o painel não transforma essa coluna em indicador |

Regras do arquivo enviado pelo usuário: a coluna do código IBGE pode se chamar `CodMunicipioIbge`, `cod_ibge`, `codigo_ibge`, `cod_municipio`, `ibge` ou `codigo`. O separador pode ser vírgula ou ponto e vírgula, e a codificação UTF-8 ou Latin-1, porque é assim que o Excel em português salva CSV. Números no formato brasileiro (1.234,5) são convertidos. Linhas com código inválido ou repetido são descartadas, com aviso na tela.

## 3. Colunas descartadas por privacidade

O arquivo original tem `NomTitularEmpreendimento`, `NumCPFCNPJ` e `CodCEP`. São dados pessoais, identificam o dono de cada instalação e não servem para nada na pergunta do projeto, que é territorial e agregada.

Optei por não ler essas colunas já na leitura do Parquet, em vez de apagar depois. Assim elas nem chegam a entrar na memória nem nos arquivos gerados.

## 4. O que encontrei na inspeção

A potência instalada total soma 51.630 MW, e 99,41% disso é radiação solar. Isso confirmou que tratar o projeto como painel solar é fiel ao dado.

Dos 5.571 municípios do IBGE, só 4 não têm nenhum empreendimento registrado. Isso derrubou a minha hipótese inicial, que era mapear vazios de adoção.

A desigualdade aparece na intensidade. Os 10% maiores municípios concentram 58,7% da potência nacional. A mediana municipal é 3.041 kW e o percentil 90 chega a 19.680 kW, uma diferença de mais de seis vezes. Foi esse recorte que passou a orientar o projeto.

Nas notícias, a categoria mais frequente é Tarifas (18 notícias), seguida de Geração (10), Institucional (8) e Fiscalização (8). Os termos que mais aparecem, tirando as stopwords, são pública (108 vezes, de consulta e audiência pública), transmissão (87), consulta (75) e distribuição (68). A pauta recente da agência é tarifária e de rede. Só 5 das 83 notícias tratam de geração distribuída ou solar, uma delas sobre novas regras para preparar a rede para geração solar, baterias e veículos elétricos.

Com a população, o Brasil tem 241 kW de geração distribuída por mil habitantes. Entre os estados a diferença é grande: Mato Grosso tem 806 kW por mil habitantes e o Amazonas tem 75, mais de dez vezes menos. No ranking por habitante aparecem no topo municípios pequenos com usinas de minigeração, como Santa Clara d'Oeste (SP), com 2.710 habitantes. Esse indicador relativo complementa o absoluto, que favorece as capitais.

## 5. Qualidade e limitações

As colunas `CodSubGrupoTarifario` e `SigModalidadeEmpreendimento` vêm todas nulas no arquivo, então não dá para usar.

A ANEEL informa que a atualização da base ficou suspensa entre 23/09/2025 e 13/11/2025 por migração do sistema SISGD, e que segue mais lenta desde então. Por isso o painel sempre mostra a data de referência do dado carregado.

Alguns municípios mais novos vêm do IBGE com `microrregiao` nula. Nesses casos eu pego a UF pelo caminho da `regiao-imediata`, senão o processamento quebra.

As notícias têm uma limitação importante. Durante o período eleitoral o site da ANEEL deixa públicas só as notícias recentes, e o arquivo por ano pede login. Por isso 76 das 83 notícias são de julho a setembro de 2026. Depois do período eleitoral vale rodar o scraping de novo.

O scraping depende do HTML do site. Se o layout mudar, o script para com erro em vez de gravar um arquivo vazio, e o painel continua com a última coleta versionada.

A estimativa de população do IBGE é uma projeção, não um censo. Para comparar municípios ela serve bem, mas não é contagem exata.

O arquivo enviado pelo usuário não passa por checagem de conteúdo além do formato. Se ele subir um número errado, o painel calcula o indicador com esse número.

## 6. Arquivos gerados

| Arquivo | Conteúdo | Tamanho |
|---|---|---|
| `data/processed/gd_por_municipio.csv` | Uma linha por município com quantidade e potência | 268 KB |
| `data/processed/cobertura_municipios.csv` | Os 5.571 municípios do IBGE com os indicadores preenchidos | 355 KB |
| `data/processed/gd_por_fonte.csv` | Potência por fonte de geração | 546 B |
| `data/processed/gd_por_classe.csv` | Potência por classe de consumo e UF | 5,8 KB |
| `Sample_Data/amostra_gd_bruto.csv` | 500 linhas do dado bruto | 42 KB |
| `Sample_Data/amostra_gd_municipio.csv` | 200 municípios do agregado | 10 KB |
| `data/external/noticias_aneel.csv` | 83 notícias da ANEEL com texto completo (TP2) | 178 KB |
| `data/external/noticias_aneel.txt` | Texto das notícias, uma por linha, para a nuvem de palavras (TP2) | 161 KB |
| `Sample_Data/exemplo_upload_populacao.csv` | População 2026 dos 5.571 municípios, exemplo de upload (TP2) | 106 KB |
