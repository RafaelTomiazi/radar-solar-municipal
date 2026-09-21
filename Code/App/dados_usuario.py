# Leitura e validacao do CSV que o usuario sobe no app.
# A regra e simples: o arquivo precisa ter o codigo IBGE do municipio (7 digitos)
# e pelo menos uma coluna numerica. Com isso da pra juntar com a base da ANEEL.

import io

import pandas as pd

COLUNA_CHAVE = "CodMunicipioIbge"

# nomes que o pessoal costuma usar pra mesma coluna
APELIDOS_CHAVE = ["codmunicipioibge", "cod_ibge", "codigo_ibge", "cod_municipio", "ibge", "codigo"]


def ler_csv(arquivo_bytes):
    # tenta virgula e ponto e virgula, e utf-8 e latin-1, pq CSV salvo no Excel
    # em portugues vem com ; e latin-1
    ultimo_erro = None
    for encoding in ("utf-8", "latin-1"):
        for sep in (",", ";"):
            try:
                tabela = pd.read_csv(io.BytesIO(arquivo_bytes), sep=sep, encoding=encoding)
            except (UnicodeDecodeError, pd.errors.ParserError) as erro:
                ultimo_erro = erro
                continue
            if tabela.shape[1] > 1:
                return tabela
    raise ValueError("Não consegui ler o arquivo como CSV (%s)" % ultimo_erro)


def validar(tabela):
    # devolve (tabela_limpa, lista_de_colunas_numericas, avisos)
    avisos = []

    # acha a coluna do codigo IBGE mesmo que venha com outro nome
    chave = None
    for coluna in tabela.columns:
        if coluna.strip().lower() in APELIDOS_CHAVE:
            chave = coluna
            break
    if chave is None:
        raise ValueError(
            "O arquivo precisa de uma coluna com o código IBGE do município "
            "(por exemplo `CodMunicipioIbge`)."
        )

    tabela = tabela.rename(columns={chave: COLUNA_CHAVE})
    tabela[COLUNA_CHAVE] = pd.to_numeric(tabela[COLUNA_CHAVE], errors="coerce")

    invalidos = tabela[COLUNA_CHAVE].isna() | (tabela[COLUNA_CHAVE] < 1000000) | (tabela[COLUNA_CHAVE] > 9999999)
    if invalidos.any():
        avisos.append("%d linha(s) com código IBGE inválido foram descartadas." % invalidos.sum())
    tabela = tabela[~invalidos].copy()
    tabela[COLUNA_CHAVE] = tabela[COLUNA_CHAVE].astype(int)

    repetidos = tabela.duplicated(subset=COLUNA_CHAVE)
    if repetidos.any():
        avisos.append("%d município(s) repetido(s), mantive a primeira ocorrência." % repetidos.sum())
        tabela = tabela[~repetidos]

    # coluna com numero em formato brasileiro (1.234,5) vem como texto, tento converter
    for coluna in tabela.columns:
        if coluna == COLUNA_CHAVE or pd.api.types.is_numeric_dtype(tabela[coluna]):
            continue
        convertida = pd.to_numeric(
            tabela[coluna].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
            errors="coerce",
        )
        if convertida.notna().mean() > 0.9:
            tabela[coluna] = convertida

    numericas = [
        c for c in tabela.columns
        if c != COLUNA_CHAVE and pd.api.types.is_numeric_dtype(tabela[c])
    ]
    if not numericas:
        raise ValueError("O arquivo precisa de pelo menos uma coluna numérica além do código IBGE.")

    if tabela.empty:
        raise ValueError("Nenhuma linha válida sobrou depois da validação.")

    return tabela.reset_index(drop=True), numericas, avisos


def juntar(base, enviado):
    # left join: mantem todos os municipios da base e traz as colunas novas.
    # tiro do enviado as colunas que ja existem na base pra nao duplicar
    repetidas = [c for c in enviado.columns if c in base.columns and c != COLUNA_CHAVE]
    return base.merge(enviado.drop(columns=repetidas), on=COLUNA_CHAVE, how="left")


def modelo_csv():
    # arquivo de exemplo pro usuario baixar e preencher
    exemplo = pd.DataFrame(
        {
            COLUNA_CHAVE: [3304557, 3550308, 5300108],
            "municipio_referencia": ["Rio de Janeiro", "São Paulo", "Brasília"],
            "populacao": [6211423, 11451999, 2817381],
        }
    )
    return exemplo.to_csv(index=False).encode("utf-8")
