# Scraping das noticias da ANEEL com Beautiful Soup.
# Roda separado do app, igual a coleta: python Code/DataAcquisition/scraping_noticias.py
# Salva um CSV (uma linha por noticia) e um TXT (so o texto, pra nuvem de palavras)
# em data/external. Nao uso data/raw pq ele ta no .gitignore e esses arquivos
# precisam ir pro repositorio pro app funcionar no deploy

import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_EXTERNAL = os.path.join(RAIZ, "data", "external")

URL_NOTICIAS = "https://www.gov.br/aneel/pt-br/assuntos/noticias"
POR_PAGINA = 30  # a listagem do gov.br pagina de 30 em 30 (parametro b_start:int)
PAGINAS = 10

# o gov.br devolve a pagina normal pra qualquer navegador, so me identifico
CABECALHO = {"User-Agent": "Mozilla/5.0 (projeto academico Infnet - Radar Solar Municipal)"}

# palavras que ligam a noticia ao tema do projeto
TERMOS_GD = [
    "solar", "fotovolta", "geração distribuída", "geracao distribuida",
    "micro e minigeração", "minigeração", "microgeração",
]


def baixar_pagina(inicio):
    resposta = requests.get(
        URL_NOTICIAS, params={"b_start:int": inicio}, headers=CABECALHO, timeout=30
    )
    resposta.raise_for_status()
    return resposta.text


def extrair_noticias(html):
    sopa = BeautifulSoup(html, "html.parser")
    noticias = []

    # cada noticia e um <li> com div.conteudo dentro. a paginacao tambem usa
    # <li>, por isso descarto os que nao tem o titulo
    for item in sopa.select("#content-core li"):
        link = item.select_one("h2.titulo a")
        if link is None:
            continue

        categoria = item.select_one(".subtitulo-noticia")
        data = item.select_one(".descricao .data")
        descricao = item.select_one(".descricao")

        # a descricao vem como "18/09/2026 - texto", tiro a data e o traco
        texto_desc = ""
        if descricao is not None:
            for span in descricao.find_all("span"):
                span.extract()
            texto_desc = descricao.get_text(" ", strip=True)

        noticias.append(
            {
                "data": data.get_text(strip=True) if data else "",
                "categoria": categoria.get_text(strip=True) if categoria else "",
                "titulo": link.get_text(" ", strip=True),
                "descricao": texto_desc,
                "url": link.get("href", ""),
            }
        )

    return noticias


def baixar_texto(url):
    # a listagem so tem titulo e resumo. o texto inteiro fica na pagina da
    # noticia, dentro do div com o corpo do artigo
    resposta = requests.get(url, headers=CABECALHO, timeout=30)
    resposta.raise_for_status()
    sopa = BeautifulSoup(resposta.text, "html.parser")
    corpo = sopa.select_one("#parent-fieldname-text")
    if corpo is None:
        return ""
    return corpo.get_text(" ", strip=True)


def marca_tema_gd(linha):
    texto = (linha["titulo"] + " " + linha["descricao"] + " " + linha["texto"]).lower()
    return any(termo in texto for termo in TERMOS_GD)


def coletar(paginas=PAGINAS):
    todas = []
    for pagina in range(paginas):
        inicio = pagina * POR_PAGINA
        try:
            noticias = extrair_noticias(baixar_pagina(inicio))
        except requests.RequestException as erro:
            print("Falhou a pagina %d: %s" % (pagina + 1, erro))
            continue

        print("Pagina %d: %d noticias" % (pagina + 1, len(noticias)))
        if not noticias:
            break
        todas.extend(noticias)

        # 1 segundo entre as paginas pra nao sobrecarregar o site
        time.sleep(1)

    # segunda passada: entra em cada noticia pra pegar o texto completo
    for i, noticia in enumerate(todas, start=1):
        try:
            noticia["texto"] = baixar_texto(noticia["url"])
        except requests.RequestException as erro:
            print("Falhou o texto de %s: %s" % (noticia["url"], erro))
            noticia["texto"] = ""
        if i % 20 == 0:
            print("Textos baixados: %d de %d" % (i, len(todas)))
        time.sleep(0.5)

    return todas


if __name__ == "__main__":
    noticias = coletar()

    # se o layout do site mudar o seletor para de achar as noticias. prefiro
    # parar aqui do que gravar um CSV vazio por cima do que ja existe
    if not noticias:
        sys.exit("Nenhuma noticia encontrada, o layout da pagina pode ter mudado")

    tabela = pd.DataFrame(noticias).drop_duplicates(subset="url")
    tabela["data"] = pd.to_datetime(tabela["data"], format="%d/%m/%Y", errors="coerce")
    # a categoria vem as vezes "Tarifas", as vezes "TARIFAS"
    tabela["categoria"] = tabela["categoria"].str.strip().str.capitalize()
    tabela["categoria"] = tabela["categoria"].replace("", "Sem categoria")
    tabela["tema_gd"] = tabela.apply(marca_tema_gd, axis=1)
    tabela["qtd_palavras"] = tabela["texto"].str.split().str.len().fillna(0).astype(int)
    tabela["coletado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    os.makedirs(PASTA_EXTERNAL, exist_ok=True)
    caminho_csv = os.path.join(PASTA_EXTERNAL, "noticias_aneel.csv")
    caminho_txt = os.path.join(PASTA_EXTERNAL, "noticias_aneel.txt")

    tabela.to_csv(caminho_csv, index=False, encoding="utf-8")
    with open(caminho_txt, "w", encoding="utf-8") as arquivo:
        for _, linha in tabela.iterrows():
            # uma noticia por linha: titulo, resumo e texto completo
            arquivo.write(" ".join([linha["titulo"] + ".", linha["descricao"], linha["texto"]]) + "\n")

    print("Salvei %d noticias em %s" % (len(tabela), caminho_csv))
    print("De %s ate %s" % (tabela["data"].min().date(), tabela["data"].max().date()))
    print("Ligadas a geracao distribuida/solar: %d" % tabela["tema_gd"].sum())
