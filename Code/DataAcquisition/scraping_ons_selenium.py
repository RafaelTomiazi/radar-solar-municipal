# Scraping da pagina "Energia Agora" do ONS com Selenium.
# Rodar separado, igual aos outros: python Code/DataAcquisition/scraping_ons_selenium.py
# Salva em data/external/geracao_ons.csv e .txt
#
# Por que Selenium e nao Beautiful Soup aqui? Essa pagina do ONS carrega os
# numeros de geracao por JavaScript depois que a pagina abre. Se eu baixar o
# HTML com requests + BeautifulSoup vem a estrutura da pagina mas os valores
# ficam vazios (a pagina tem 154 KB de HTML e so 2 KB de texto util antes do JS
# rodar). Com o Selenium eu abro a pagina num navegador de verdade, espero o JS
# montar os numeros e so entao leio a tela.
#
# O dado e a geracao nacional por fonte em tempo real. Interessa pro projeto
# porque mostra onde a solar e a MMGD (micro e minigeracao distribuida, que e o
# tema do painel) entram na matriz do pais inteiro.

import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_EXTERNAL = os.path.join(RAIZ, "data", "external")

URL_ONS = "https://www.ons.org.br/paginas/energia-agora/carga-e-geracao"

# o chrome e o chromedriver podem estar em lugares diferentes dependendo da
# maquina. deixo o padrao do sistema (PATH) e dou pra sobrescrever por variavel
# de ambiente pra rodar no Streamlit Cloud, que instala o chromium via packages.txt
CHROME_BIN = os.environ.get("CHROME_BIN")
CHROMEDRIVER = os.environ.get("CHROMEDRIVER")

# as fontes que aparecem no quadro "Geracao (MW)" do ONS
FONTES = ["Hidráulica", "Térmica", "Nuclear", "Eólica", "Solar", "MMGD", "Importação"]


def abrir_navegador():
    opcoes = Options()
    if CHROME_BIN:
        opcoes.binary_location = CHROME_BIN
    # headless = sem abrir janela, roda no servidor. os outros flags sao o
    # combo padrao pra rodar chrome dentro de container/linux sem tela
    for flag in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--disable-gpu", "--window-size=1920,1080"]:
        opcoes.add_argument(flag)
    opcoes.add_argument("--user-agent=Mozilla/5.0 (projeto academico Infnet - Radar Solar Municipal)")

    servico = Service(CHROMEDRIVER) if CHROMEDRIVER else Service()
    navegador = webdriver.Chrome(service=servico, options=opcoes)
    navegador.set_page_load_timeout(60)
    return navegador


def ler_geracao(texto_pagina):
    # o ONS escreve cada fonte como "Ger. Solar: 65,5 MW". pego o numero que
    # vem depois de cada nome de fonte
    registros = []
    for fonte in FONTES:
        # aceita "Ger. Solar: 65,5 MW" e "Solar: 65,5 MW"
        padrao = re.compile(r"%s\s*:?\s*([\d.]+,\d+|\d+)\s*MW" % re.escape(fonte), re.IGNORECASE)
        achado = padrao.search(texto_pagina)
        if achado:
            # numero vem em formato brasileiro (63.464,8), converto pra float
            valor = float(achado.group(1).replace(".", "").replace(",", "."))
            registros.append({"fonte": fonte, "geracao_mw": valor})
    return registros


def ler_atualizacao(texto_pagina):
    # a pagina mostra "ULTIMA ATUALIZACAO: 19/10/2026 18:16"
    achado = re.search(r"ATUALIZA[ÇC][ÃA]O:\s*([\d/]+\s+[\d:]+)", texto_pagina, re.IGNORECASE)
    return achado.group(1) if achado else ""


def coletar():
    navegador = abrir_navegador()
    try:
        print("Abrindo a pagina do ONS...")
        navegador.get(URL_ONS)

        # o JS precisa de um tempo pra buscar os numeros e montar a tela.
        # espero ate aparecer algum valor em MW, checando de 2 em 2 segundos
        texto = ""
        for tentativa in range(10):
            time.sleep(2)
            texto = navegador.find_element(By.TAG_NAME, "body").text
            if "MW" in texto and ler_geracao(texto):
                print("Numeros carregaram depois de ~%d segundos" % ((tentativa + 1) * 2))
                break
        else:
            raise RuntimeError("Os numeros nao carregaram, o layout do ONS pode ter mudado")

        geracao = ler_geracao(texto)
        atualizacao = ler_atualizacao(texto)
        return geracao, atualizacao
    finally:
        navegador.quit()


if __name__ == "__main__":
    try:
        geracao, atualizacao = coletar()
    except Exception as erro:
        sys.exit("Falhou o scraping do ONS: %s" % erro)

    if not geracao:
        sys.exit("Nenhum valor de geracao encontrado")

    tabela = pd.DataFrame(geracao)
    total = tabela["geracao_mw"].sum()
    tabela["participacao_pct"] = (tabela["geracao_mw"] / total * 100).round(2)
    tabela["atualizacao_ons"] = atualizacao
    tabela["coletado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    os.makedirs(PASTA_EXTERNAL, exist_ok=True)
    caminho_csv = os.path.join(PASTA_EXTERNAL, "geracao_ons.csv")
    tabela.to_csv(caminho_csv, index=False, encoding="utf-8")

    # um txt curtinho so pra deixar registrado em texto, no mesmo padrao do
    # scraping de noticias
    caminho_txt = os.path.join(PASTA_EXTERNAL, "geracao_ons.txt")
    with open(caminho_txt, "w", encoding="utf-8") as arquivo:
        arquivo.write("Geracao por fonte no SIN - ONS (coletado via Selenium)\n")
        arquivo.write("Atualizacao do ONS: %s\n\n" % atualizacao)
        for _, linha in tabela.iterrows():
            arquivo.write("%s: %.1f MW (%.2f%%)\n" % (linha["fonte"], linha["geracao_mw"], linha["participacao_pct"]))

    print("Salvei %d fontes em %s" % (len(tabela), caminho_csv))
    print("Geracao total do SIN: %.0f MW" % total)
    solar_mmgd = tabela[tabela["fonte"].isin(["Solar", "MMGD"])]["geracao_mw"].sum()
    print("Solar + MMGD: %.1f MW (%.2f%% da matriz)" % (solar_mmgd, solar_mmgd / total * 100))
