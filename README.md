# Radar Solar Municipal

Painel de acompanhamento da geração distribuída de energia no Brasil por município.

**Projeto de Bloco: Inteligência Artificial Aplicada**, Instituto Infnet  
Aluno: Rafael Celestino Tomiazi

**App publicado:** https://radar-solar-municipal-h3abtstmymwssr8a9wpb9m.streamlit.app/

## Entregas

| Etapa | O que foi entregue | Onde ver |
|---|---|---|
| TP1 | Proposta, Project Charter, Data Summary Report, coleta ANEEL/IBGE, processamento e app demo | tag [`tp1`](https://github.com/RafaelTomiazi/radar-solar-municipal/tree/tp1) |
| TP2 | Git e deploy, interface interativa, scraping com Beautiful Soup, nuvem de palavras e estatísticas, cache e estado de sessão, upload/download de CSV, documentos atualizados | branch `main` e [histórico de commits](https://github.com/RafaelTomiazi/radar-solar-municipal/commits/main) |

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
│   ├── DataAcquisition/     coleta nas APIs da ANEEL e do IBGE e scraping das notícias
│   ├── DataPreparation/     processamento e agregação
│   └── App/                 módulos do dashboard (texto/nuvem de palavras e upload)
├── Docs/
│   ├── Project/             Project Charter
│   ├── DataReport/          Data Summary Report
│   └── Prints/              prints da aplicação
├── Sample_Data/             amostras versionadas e exemplo de CSV para upload
├── data/
│   ├── raw/                 dado bruto, fora do versionamento
│   ├── external/            notícias da ANEEL extraídas com Beautiful Soup (CSV e TXT)
│   └── processed/           saída do pipeline
├── app.py                   aplicação Streamlit
└── requirements.txt
```
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

A coleta baixa uns 101 MB da ANEEL e levou por volta de 40 segundos aqui. O processamento chegou a uns 700 MB de memória no pico, então convém não deixar muita coisa aberta junto.

## O que o app faz (TP2)

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

Os prints dessas telas estão em [`Docs/Prints/`](Docs/Prints).

## Deploy

O app está publicado no Streamlit Community Cloud em https://radar-solar-municipal-h3abtstmymwssr8a9wpb9m.streamlit.app/. Ele foi preparado assim: o repositório é público, as dependências estão no `requirements.txt` e os dados que o app usa (`data/processed`, `data/external` e `Sample_Data`) estão versionados. Para publicar, basta entrar em share.streamlit.io com a conta do GitHub, escolher este repositório, a branch `main` e o arquivo `app.py`.

## Fontes de dados

- Geração distribuída: ANEEL, Portal de Dados Abertos, licença ODbL, referência de 21/08/2026.
- Malha municipal: IBGE, API de Localidades.
- População estimada: IBGE, API SIDRA (tabela 6579).
- Notícias: site da ANEEL, gov.br/aneel/pt-br/assuntos/noticias.

## Documentos

- [Project Charter](Docs/Project/project_charter.md)
- [Data Summary Report](Docs/DataReport/data_summary_report.md)
- [Prints da aplicação](Docs/Prints)
- PDFs entregues: [TP1](rafael_tomiazi_PB_TP1.pdf) e [TP2](rafael_tomiazi_PB_TP2.pdf)
