# Radar Solar Municipal

Painel de acompanhamento da geração distribuída de energia no Brasil por município.

**Projeto de Bloco: Inteligência Artificial Aplicada**, Instituto Infnet  
Aluno: Rafael Celestino Tomiazi

**App publicado:** https://radar-solar-municipal-h3abtstmymwssr8a9wpb9m.streamlit.app/

## Entregas

| Etapa | O que foi entregue | Onde ver |
|---|---|---|
| TP1 | Proposta, Project Charter, Data Summary Report, coleta ANEEL/IBGE, processamento e app demo | tag [`tp1`](https://github.com/RafaelTomiazi/radar-solar-municipal/tree/tp1) |
| TP2 | Git e deploy, interface interativa, scraping com Beautiful Soup, nuvem de palavras e estatísticas, cache e estado de sessão, upload/download de CSV, documentos atualizados | tag [`tp2`](https://github.com/RafaelTomiazi/radar-solar-municipal/tree/tp2) |
| TP3 | App multipágina com menu de navegação, API com FastAPI integrada ao app, scraping da página dinâmica do ONS com Selenium, documentos revisados e planejamento do uso de LLM | branch `main` e [histórico de commits](https://github.com/RafaelTomiazi/radar-solar-municipal/commits/main) |

### Correções feitas a partir do retorno do TP1

- `requirements.txt` com faixas de versão (`>=`) no lugar de versões fixas (`==`), como recomendado na correção.
- Instalação testada do zero em um ambiente virtual limpo (`pip install -r requirements.txt` e `pip check` sem conflitos) antes da entrega.
- Troca do parâmetro `use_container_width`, que foi descontinuado no Streamlit, por `width`.

## O problema

A ANEEL publica a lista completa dos empreendimentos de micro e minigeração distribuída do país, mas o arquivo tem 101 MB, 4,67 milhões de linhas e 31 colunas técnicas. O dado é aberto e mesmo assim inacessível para quem não processa dados.

Os números do processamento: 51,6 GW instalados, 99,41% em radiação solar e presença em 5.567 dos 5.571 municípios. A desigualdade não está na ausência, está na intensidade: os 10% maiores municípios concentram 58,7% da potência nacional.

O ODS principal é o 7, Energia Limpa e Acessível. Secundários: ODS 11, ODS 13 e ODS 10.

## Estrutura de diretórios

A organização segue as fases do ciclo de vida do TDSP.

```
.
├── Code/
│   ├── DataAcquisition/     coleta nas APIs da ANEEL e do IBGE, scraping das notícias (Beautiful Soup) e do ONS (Selenium)
│   ├── DataPreparation/     processamento e agregação
│   ├── API/                 API com FastAPI que serve os dados por município (TP3)
│   └── App/                 código comum às páginas, texto/nuvem de palavras e upload
├── paginas/                 uma página do app por arquivo (TP3)
├── Docs/
│   ├── Project/             Project Charter
│   ├── DataReport/          Data Summary Report
│   └── Prints/              prints da aplicação
├── Sample_Data/             amostras versionadas e exemplo de CSV para upload
├── data/
│   ├── raw/                 dado bruto, fora do versionamento
│   ├── external/            notícias da ANEEL (Beautiful Soup) e geração do ONS (Selenium), em CSV e TXT
│   └── processed/           saída do pipeline
├── app.py                   entrada do app: menu de navegação e filtros
└── requirements.txt
```

O nome da pasta das páginas é `paginas/` e não `pages/` de propósito. Com `pages/`, o Streamlit ativa o modo antigo de multipágina e executa cada arquivo direto, sem passar pelo `app.py`, e aí o menu e os filtros somem. Descobri isso testando.
O `data/raw/` está no `.gitignore` porque o Parquet da ANEEL tem 101 MB e o GitHub não aceita arquivo acima de 100 MB. Descobri isso tentando dar push. Ele é reconstruído pelo script de coleta.

## Como rodar

A forma mais rápida de ver o projeto é o app publicado (link no topo). Para rodar localmente:

Clonar o repositório:

```bash
git clone https://github.com/RafaelTomiazi/radar-solar-municipal.git
cd radar-solar-municipal
```

Criar e ativar o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate        # Linux e macOS
.venv\Scripts\activate           # Windows
```

Instalar as dependências:

```bash
pip install -r requirements.txt
```

Rodar a aplicação:

```bash
streamlit run app.py
```

O app abre direto, sem rodar nenhum script antes: os dados processados (`data/processed`), as notícias extraídas (`data/external`) e as amostras (`Sample_Data`) já estão no repositório. Se `data/processed` não existir, o app cai para as amostras de `Sample_Data/` e avisa na tela.

Para refazer a base completa a partir da ANEEL e do IBGE:

```bash
python Code/DataAcquisition/coleta_dados.py
python Code/DataPreparation/processa_dados.py
```

Para atualizar as notícias da ANEEL e o exemplo de população:

```bash
python Code/DataAcquisition/scraping_noticias.py
python Code/DataAcquisition/coleta_populacao.py
```

O scraping lê a listagem de notícias do site da ANEEL (gov.br) e depois entra em cada notícia para pegar o texto completo, com uma pausa entre as requisições. O resultado fica em `data/external/noticias_aneel.csv` (uma linha por notícia) e `data/external/noticias_aneel.txt` (só o texto, usado na nuvem de palavras). Esses arquivos são versionados para o app funcionar sem rodar o scraping.

Para atualizar a geração do ONS (precisa do Google Chrome ou Chromium instalado; o Selenium 4 baixa o driver sozinho):

```bash
python Code/DataAcquisition/scraping_ons_selenium.py
```

A página "Energia Agora" do ONS monta os números de geração com JavaScript depois de abrir, então o Beautiful Soup recebe a página sem os valores. O script abre a página num Chrome sem janela (headless), espera os números aparecerem e lê a tela. O resultado fica em `data/external/geracao_ons.csv` e `.txt`. Se o Chrome estiver em outro lugar, dá para indicar com as variáveis `CHROME_BIN` e `CHROMEDRIVER`.

### API (FastAPI)

O `streamlit run app.py` já sobe a API sozinho, numa thread, na porta 8000, se ela não estiver no ar. Para rodar a API separada:

```bash
uvicorn Code.API.api:app --reload --port 8000
```

A documentação interativa (Swagger) fica em http://localhost:8000/docs. Rotas:

| Método | Rota | O que faz |
|---|---|---|
| GET | `/` | Status da API e quantos municípios foram carregados |
| GET | `/municipios?uf=RJ&limite=50` | Lista municípios ordenados por potência, com filtro opcional por UF |
| GET | `/municipios/{cod_ibge}` | Ficha de um município pelo código IBGE (404 se não existir) |
| GET | `/ranking?por=potencia&uf=SP&top=10` | Ranking por `potencia`, `quantidade` ou `media` |
| POST | `/indicador-por-habitante` | Recebe `{"cod_ibge": 3304557, "populacao": 6211000}` e devolve a potência por mil habitantes |

Exemplo pelo terminal:

```bash
curl "http://localhost:8000/ranking?uf=PI&top=3"
curl -X POST http://localhost:8000/indicador-por-habitante \
     -H "Content-Type: application/json" -d '{"cod_ibge": 3304557, "populacao": 6211000}'
```

A coleta baixa uns 101 MB da ANEEL e levou por volta de 40 segundos aqui. O processamento chegou a uns 700 MB de memória no pico, então convém não deixar muita coisa aberta junto.

## O que o app faz

No TP3 as abas viraram páginas, com um menu de navegação na barra lateral dividido em Análise, Dados coletados e Projeto. Os filtros de região e UF continuam na barra lateral e valem em todas as páginas.

Novidades do TP3:

- **Geração agora (ONS):** geração do país por fonte no momento da coleta, extraída com Selenium, e a comparação entre a GD instalada (ANEEL) e o que a MMGD estava gerando.
- **Consulta via API:** a página consome a API FastAPI por HTTP. Dá para consultar o ranking (GET), buscar a ficha de um município (GET) e enviar município + população para calcular o indicador (POST). O número de consultas fica na barra lateral.
- **Próximos passos: IA:** o planejamento das tarefas com LLM para o TP4, ligando cada tarefa ao dado que já existe no projeto.

Do TP2, mantidas:

- **Panorama:** indicadores do recorte escolhido na barra lateral (região e UF), comparação entre estados com seletor de indicador e potência por classe de consumo.
- **Municípios:** busca de município com posição na UF e no Brasil, ranking configurável (indicador, maiores/menores, quantidade) com download em CSV e comparação de até 6 municípios.
- **Notícias ANEEL:** notícias extraídas com Beautiful Soup, com filtros por categoria, período, busca no texto e tema (geração distribuída/solar), nuvem de palavras, termos mais frequentes, notícias por categoria e por mês.
- **Seus dados:** upload de CSV com o código IBGE do município. As colunas enviadas entram no painel como novos indicadores (por exemplo, kW por mil habitantes) e a base combinada pode ser baixada. Tem um modelo e um exemplo pronto com a população do IBGE para testar.
- **Cache e estado de sessão:** as cargas de CSV, a consulta à API da ANEEL e a nuvem de palavras usam `st.cache_data`. Filtros, município consultado, histórico de consultas e o arquivo enviado ficam no `st.session_state` e continuam valendo ao trocar de aba.

### Roteiro rápido para testar as funcionalidades do TP2

1. **Filtros e estado de sessão:** escolha uma região na barra lateral e troque de aba. O filtro continua valendo.
2. **Municípios:** busque um município, mude o ranking (indicador, maiores/menores, quantidade), baixe o CSV e compare municípios. O histórico aparece na barra lateral.
3. **Notícias ANEEL:** veja a nuvem de palavras e as estatísticas, e filtre por categoria, período ou busca no texto (por exemplo, "tarifa").
4. **Upload:** na aba Seus dados, clique em "Baixar exemplo pronto: população 2026 (IBGE)" e envie esse mesmo arquivo. Depois, na aba Panorama, escolha o indicador "kW por mil de 'populacao'".

### Roteiro rápido para testar as funcionalidades do TP3

1. **Menu:** navegue pelas páginas na barra lateral. Escolha uma UF no filtro, vá para Municípios e volte para Panorama: o filtro continua valendo.
2. **API:** na página Consulta via API, digite `PI` no campo UF e clique em Consultar ranking. Depois, na aba POST, clique em Enviar. Para ver a API direto, abra http://localhost:8000/docs.
3. **Selenium:** a página Geração agora (ONS) mostra o resultado da última coleta. Para coletar de novo, rode `python Code/DataAcquisition/scraping_ons_selenium.py`.

Os prints dessas telas estão em [`Docs/Prints/`](Docs/Prints).

## Deploy

O app está publicado no Streamlit Community Cloud em https://radar-solar-municipal-h3abtstmymwssr8a9wpb9m.streamlit.app/. Ele foi preparado assim: o repositório é público, as dependências estão no `requirements.txt` e os dados que o app usa (`data/processed`, `data/external` e `Sample_Data`) estão versionados. Para publicar, basta entrar em share.streamlit.io com a conta do GitHub, escolher este repositório, a branch `main` e o arquivo `app.py`.

## Fontes de dados

- Geração distribuída: ANEEL, Portal de Dados Abertos, licença ODbL, referência de 21/08/2026.
- Malha municipal: IBGE, API de Localidades.
- População estimada: IBGE, API SIDRA (tabela 6579).
- Notícias: site da ANEEL, gov.br/aneel/pt-br/assuntos/noticias.
- Geração por fonte em tempo real: ONS, ons.org.br/paginas/energia-agora/carga-e-geracao (Selenium).

## Uso de IA

O TP2 e o TP3 têm sinal verde para ferramentas de IA, com citação. Usei o Claude (Anthropic) como apoio no desenvolvimento do código e na revisão dos documentos. Os números citados nos documentos saem da execução dos scripts sobre os dados reais.

## Documentos

- [Project Charter](Docs/Project/project_charter.md)
- [Data Summary Report](Docs/DataReport/data_summary_report.md)
- [Prints da aplicação](Docs/Prints)
- PDFs entregues: [TP1](rafael_tomiazi_PB_TP1.pdf), [TP2](rafael_tomiazi_PB_TP2.pdf) e [TP3](rafael_tomiazi_PB_TP3.pdf)
