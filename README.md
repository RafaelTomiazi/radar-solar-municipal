# Radar Solar Municipal

Painel de acompanhamento da geração distribuída de energia no Brasil por município.

**Projeto de Bloco: Inteligência Artificial Aplicada**, Instituto Infnet
Aluno: Rafael Celestino Tomiazi

## O problema

A ANEEL publica a lista completa dos empreendimentos de micro e minigeração distribuída do país, mas o arquivo tem 101 MB, 4,67 milhões de linhas e 31 colunas técnicas. O dado é aberto e mesmo assim inacessível para quem não processa dados.

Os números do processamento: 51,6 GW instalados, 99,41% em radiação solar e presença em 5.567 dos 5.571 municípios. A desigualdade não está na ausência, está na intensidade: os 10% maiores municípios concentram 58,7% da potência nacional.

O ODS principal é o 7, Energia Limpa e Acessível. Secundários: ODS 11, ODS 13 e ODS 10.

## Estrutura de diretórios

A organização segue as fases do ciclo de vida do TDSP.

```
.
├── Code/
│   ├── DataAcquisition/     coleta nas APIs da ANEEL e do IBGE
│   ├── DataPreparation/     processamento e agregação
│   └── App/                 módulos do dashboard
├── Docs/
│   ├── Project/             Project Charter
│   ├── DataReport/          Data Summary Report
│   └── Model/               Model Report
├── Sample_Data/             amostras versionadas dos dados
├── data/
│   ├── raw/                 dado bruto, fora do versionamento
│   └── processed/           saída do pipeline
├── app.py                   aplicação Streamlit
└── requirements.txt
```

O `data/raw/` está no `.gitignore` porque o Parquet da ANEEL tem 101 MB e o GitHub não aceita arquivo acima de 100 MB. Descobri isso tentando dar push. Ele é reconstruído pelo script de coleta.

## Como rodar

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

A demo já funciona com as amostras versionadas em `Sample_Data/`. Para o painel com a base completa, rodar antes:

```bash
python Code/DataAcquisition/coleta_dados.py
python Code/DataPreparation/processa_dados.py
```

A coleta baixa uns 101 MB da ANEEL e levou por volta de 40 segundos aqui. O processamento chegou a uns 700 MB de memória no pico, então convém não deixar muita coisa aberta junto.

## Fontes de dados

Geração distribuída: ANEEL, Portal de Dados Abertos, licença ODbL, referência de 21/08/2026.
Malha municipal: IBGE, API de Localidades.

## Documentos

- [Project Charter](Docs/Project/project_charter.md)
- [Data Summary Report](Docs/DataReport/data_summary_report.md)
