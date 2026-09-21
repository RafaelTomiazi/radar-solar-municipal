# Baixa a estimativa de populacao dos municipios na API SIDRA do IBGE.
# O arquivo gerado serve de exemplo pro upload do app: o usuario sobe esse CSV
# e o painel calcula a potencia instalada por mil habitantes.
# python Code/DataAcquisition/coleta_populacao.py

import os

import pandas as pd
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESTINO = os.path.join(RAIZ, "Sample_Data", "exemplo_upload_populacao.csv")

# tabela 6579 = estimativas de populacao, variavel 9324 = populacao residente
# estimada. n6/all = todos os municipios, p/last = ultimo ano disponivel
API_SIDRA = "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last"


def coletar_populacao():
    resposta = requests.get(API_SIDRA, timeout=120)
    resposta.raise_for_status()
    linhas = resposta.json()

    # a primeira linha da resposta da SIDRA e o cabecalho com a descricao das colunas
    tabela = pd.DataFrame(linhas[1:])
    tabela = tabela.rename(columns={"D1C": "CodMunicipioIbge", "V": "populacao", "D3N": "ano"})
    tabela = tabela[["CodMunicipioIbge", "populacao", "ano"]]
    tabela["CodMunicipioIbge"] = tabela["CodMunicipioIbge"].astype(int)
    tabela["populacao"] = pd.to_numeric(tabela["populacao"], errors="coerce")
    return tabela.dropna(subset=["populacao"])


if __name__ == "__main__":
    populacao = coletar_populacao()
    populacao.to_csv(DESTINO, index=False, encoding="utf-8")
    print("Salvei %d municipios (ano %s) em %s" % (len(populacao), populacao["ano"].iloc[0], DESTINO))
