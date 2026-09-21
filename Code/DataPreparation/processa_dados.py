# Transforma o parquet bruto nos CSVs que o dashboard usa

import json
import os

import pandas as pd
import pyarrow.parquet as pq

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_RAW = os.path.join(RAIZ, "data", "raw")
PASTA_PROCESSED = os.path.join(RAIZ, "data", "processed")
PASTA_AMOSTRA = os.path.join(RAIZ, "Sample_Data")

# leio so as colunas que uso mesmo. o arquivo tem 31 colunas e eu preciso de
# 8, isso derruba bastante o consumo de memoria (achei isso no stackoverflow,
# o read_table aceita o parametro columns direto)
COLUNAS = [
    "SigUF",
    "NomRegiao",
    "CodMunicipioIbge",
    "NomMunicipio",
    "DscClasseConsumo",
    "DscFonteGeracao",
    "DscPorte",
    "MdaPotenciaInstaladaKW",
    "DthAtualizaCadastralEmpreend",
]

# essas colunas existem no original e eu nao leio de proposito: nome e
# documento do titular. e dado pessoal e nao serve pra pergunta do projeto
COLUNAS_DESCARTADAS = ["NomTitularEmpreendimento", "NumCPFCNPJ", "CodCEP"]


def agregar_por_municipio(df):
    agregado = df.groupby(
        ["SigUF", "NomRegiao", "CodMunicipioIbge", "NomMunicipio"], as_index=False
    ).agg(
        qtd_empreendimentos=("MdaPotenciaInstaladaKW", "size"),
        potencia_total_kw=("MdaPotenciaInstaladaKW", "sum"),
        potencia_media_kw=("MdaPotenciaInstaladaKW", "mean"),
    )

    agregado["potencia_total_kw"] = agregado["potencia_total_kw"].round(2)
    agregado["potencia_media_kw"] = agregado["potencia_media_kw"].round(2)
    return agregado.sort_values("potencia_total_kw", ascending=False)


# tinha duas funcoes quase iguais aqui (uma por fonte e outra por classe),
# so mudava a coluna do groupby, entao juntei nessa
def agrupar(df, colunas):
    return (
        df.groupby(colunas, as_index=False)
        .agg(
            qtd_empreendimentos=("MdaPotenciaInstaladaKW", "size"),
            potencia_total_kw=("MdaPotenciaInstaladaKW", "sum"),
        )
        .sort_values("potencia_total_kw", ascending=False)
    )


def extrair_uf(municipio):
    # o IBGE devolve a UF por dois caminhos diferentes e uns municipios mais
    # novos vem com microrregiao nula. sem esse segundo if o script quebra,
    # descobri na marra na primeira vez que rodei
    micro = municipio.get("microrregiao")
    if micro:
        return micro["mesorregiao"]["UF"]["sigla"]

    imediata = municipio.get("regiao-imediata")
    if imediata:
        return imediata["regiao-intermediaria"]["UF"]["sigla"]

    return None


def juntar_com_ibge(agregado):
    caminho = os.path.join(PASTA_RAW, "municipios_ibge.json")
    if not os.path.exists(caminho):
        print("Sem o arquivo do IBGE, sigo so com os dados da ANEEL")
        return agregado

    with open(caminho, encoding="utf-8") as arquivo:
        municipios = json.load(arquivo)

    referencia = pd.DataFrame(
        [
            {
                "CodMunicipioIbge": m["id"],
                "municipio_ibge": m["nome"],
                "uf_ibge": extrair_uf(m),
            }
            for m in municipios
        ]
    )

    # left join segurando tudo que veio do IBGE, pq municipio sem nenhum
    # empreendimento tambem interessa (na real e justamente ele que interessa)
    completo = referencia.merge(agregado, on="CodMunicipioIbge", how="left")
    completo["qtd_empreendimentos"] = completo["qtd_empreendimentos"].fillna(0).astype(int)
    completo["potencia_total_kw"] = completo["potencia_total_kw"].fillna(0)

    # o merge deixa nome e UF repetidos (um lado da ANEEL, outro do IBGE).
    # fico com o do IBGE que e o oficial e jogo fora a duplicata
    completo = completo.drop(columns=["NomMunicipio", "SigUF"], errors="ignore")
    completo = completo.rename(
        columns={"municipio_ibge": "municipio", "uf_ibge": "uf"}
    )
    return completo[
        [
            "CodMunicipioIbge",
            "municipio",
            "uf",
            "NomRegiao",
            "qtd_empreendimentos",
            "potencia_total_kw",
            "potencia_media_kw",
        ]
    ]


if __name__ == "__main__":
    os.makedirs(PASTA_PROCESSED, exist_ok=True)
    os.makedirs(PASTA_AMOSTRA, exist_ok=True)

    caminho = os.path.join(PASTA_RAW, "empreendimento-geracao-distribuida.parquet")
    if not os.path.exists(caminho):
        raise FileNotFoundError(
            "Nao achei o parquet em data/raw. Roda o Code/DataAcquisition/coleta_dados.py antes"
        )

    tabela = pq.read_table(caminho, columns=COLUNAS)
    print("Li %d linhas do arquivo bruto" % tabela.num_rows)
    df = tabela.to_pandas()

    por_municipio = agregar_por_municipio(df)
    por_municipio.to_csv(os.path.join(PASTA_PROCESSED, "gd_por_municipio.csv"), index=False)
    print("Gerei o agregado municipal com %d linhas" % len(por_municipio))

    # por fonte de geracao (aqui da pra ver o tanto que a solar domina)
    agrupar(df, "DscFonteGeracao").to_csv(
        os.path.join(PASTA_PROCESSED, "gd_por_fonte.csv"), index=False
    )
    # por classe de consumo, pra ver o perfil de quem gera
    agrupar(df, ["SigUF", "DscClasseConsumo"]).to_csv(
        os.path.join(PASTA_PROCESSED, "gd_por_classe.csv"), index=False
    )

    completo = juntar_com_ibge(por_municipio)
    completo.to_csv(os.path.join(PASTA_PROCESSED, "cobertura_municipios.csv"), index=False)

    sem_registro = (completo["qtd_empreendimentos"] == 0).sum()
    print("Municipios do IBGE sem nenhum empreendimento na base: %d" % sem_registro)

    # essas amostras sao o que vai versionado no git, pro professor conseguir
    # abrir sem ter que rodar a coleta inteira
    df.head(500).to_csv(os.path.join(PASTA_AMOSTRA, "amostra_gd_bruto.csv"), index=False)
    por_municipio.head(200).to_csv(
        os.path.join(PASTA_AMOSTRA, "amostra_gd_municipio.csv"), index=False
    )
    print("Amostras salvas em Sample_Data")
