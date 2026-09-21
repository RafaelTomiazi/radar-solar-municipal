# Data Summary Report, primeiro esboço

**Projeto:** Radar Solar Municipal
**Autor:** Rafael Celestino Tomiazi
**Data:** 24 de agosto de 2026

Esse é o primeiro esboço do Data Summary Report, escrito na fase de Data Acquisition & Understanding do TDSP. Documentei só as colunas que eu uso de fato, não as 31 do arquivo original.

## 1. Fontes de dados

### ANEEL, empreendimentos de geração distribuída

Acesso pela API do CKAN em `https://dadosabertos.aneel.gov.br/api/3/action/package_show`, sem chave. Arquivo Parquet de 101 MB, 4.673.268 linhas e 31 colunas. Licença Open Data Commons ODbL, atualização verificada em 21/08/2026.

É a fonte principal. Cada linha é um empreendimento de micro ou minigeração ligado à rede, com localização, fonte de energia, classe de consumo e potência instalada.

Consulto a API em vez de fixar o link do arquivo porque a URL direta muda quando a ANEEL republica o dataset.

### IBGE, malha de municípios

Acesso em `https://servicodados.ibge.gov.br/api/v1/localidades/municipios`, JSON, sem chave. Devolve os 5.571 municípios do Brasil com código oficial, nome e hierarquia territorial.

Uso como referência territorial. É ela que garante que município sem nenhum empreendimento apareça no painel, porque na base da ANEEL só existe linha para quem tem instalação.

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

## 3. Colunas descartadas por privacidade

O arquivo original tem `NomTitularEmpreendimento`, `NumCPFCNPJ` e `CodCEP`. São dados pessoais, identificam o dono de cada instalação e não servem para nada na pergunta do projeto, que é territorial e agregada.

Optei por não ler essas colunas já na leitura do Parquet, em vez de apagar depois. Assim elas nem chegam a entrar na memória nem nos arquivos gerados.

## 4. O que encontrei na inspeção

A potência instalada total soma 51.630 MW, e 99,41% disso é radiação solar. Isso confirmou que tratar o projeto como painel solar é fiel ao dado.

Dos 5.571 municípios do IBGE, só 4 não têm nenhum empreendimento registrado. Isso derrubou a minha hipótese inicial, que era mapear vazios de adoção.

A desigualdade aparece na intensidade. Os 10% maiores municípios concentram 58,7% da potência nacional. A mediana municipal é 3.041 kW e o percentil 90 chega a 19.680 kW, uma diferença de mais de seis vezes. Foi esse recorte que passou a orientar o projeto.

## 5. Qualidade e limitações

As colunas `CodSubGrupoTarifario` e `SigModalidadeEmpreendimento` vêm todas nulas no arquivo, então não dá para usar.

A ANEEL informa que a atualização da base ficou suspensa entre 23/09/2025 e 13/11/2025 por migração do sistema SISGD, e que segue mais lenta desde então. Por isso o painel sempre mostra a data de referência do dado carregado.

Alguns municípios mais novos vêm do IBGE com `microrregiao` nula. Nesses casos eu pego a UF pelo caminho da `regiao-imediata`, senão o processamento quebra.

## 6. Arquivos gerados

| Arquivo | Conteúdo | Tamanho |
|---|---|---|
| `data/processed/gd_por_municipio.csv` | Uma linha por município com quantidade e potência | 268 KB |
| `data/processed/cobertura_municipios.csv` | Os 5.571 municípios do IBGE com os indicadores preenchidos | 355 KB |
| `data/processed/gd_por_fonte.csv` | Potência por fonte de geração | 546 B |
| `data/processed/gd_por_classe.csv` | Potência por classe de consumo e UF | 5,8 KB |
| `Sample_Data/amostra_gd_bruto.csv` | 500 linhas do dado bruto | 42 KB |
| `Sample_Data/amostra_gd_municipio.csv` | 200 municípios do agregado | 10 KB |
