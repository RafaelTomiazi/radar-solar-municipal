# Funcoes de texto usadas na aba de noticias: contagem de termos e nuvem de palavras.
# Separei do app.py pra ele nao virar um arquivo de 600 linhas

import re
import unicodedata
from collections import Counter

from wordcloud import WordCloud

# o STOPWORDS que vem com o wordcloud e em ingles, entao montei a lista em
# portugues. inclui tambem palavras que aparecem em toda noticia e nao dizem nada
STOPWORDS_PT = set(
    """
    a à ao aos as às o os um uma uns umas de da do das dos dessa desse desta deste
    disso nisso isso isto aquele aquela aquilo em na no nas nos num numa pela pelo
    pelas pelos por para pra com sem sob sobre entre até após ante desde contra
    e ou mas nem que se como quando onde porque pois porém também ainda já não sim
    mais menos muito muitos muita muitas pouco todo toda todos todas cada outro
    outra outros outras mesmo mesma qual quais quanto seu sua seus suas ele ela
    eles elas lhe lhes nós você vocês esse essa esses essas este esta estes estas
    é ser são foi foram era será serão seria sido sendo está estão estava estar
    tem têm ter tinha teve há houver haver pode podem poderá deve devem deverá
    fazer faz feito vai vão segundo conforme além assim bem então apenas sobre
    dia dias ano anos mês meses nesta neste nessa nesse partir forma parte caso
    aneel agência nacional energia elétrica diretoria reunião sessão acordo
    feira segunda terça quarta quinta sexta sábado domingo gov
    r$ mil milhões bilhões cerca ainda sendo
    """.split()
)


CORES = ["#b45309", "#c2410c", "#92400e", "#d97706", "#78350f", "#1e3a5f"]


def tirar_acento(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def palavras(texto, stopwords=STOPWORDS_PT):
    # quebra o texto em palavras minusculas, sem numero e sem stopword.
    # comparo sem acento pra "agencia" e "agência" cairem na mesma stopword
    sem_acento = {tirar_acento(p) for p in stopwords}
    tokens = re.findall(r"[a-záàâãéêíóôõúç]+", texto.lower())
    return [t for t in tokens if len(t) > 2 and tirar_acento(t) not in sem_acento]


def contar_termos(textos, extras=()):
    # extras = palavras que o usuario escolheu esconder na tela
    stopwords = STOPWORDS_PT | {e.lower() for e in extras}
    contagem = Counter()
    for texto in textos:
        contagem.update(palavras(texto, stopwords))
    return contagem


def gerar_nuvem(frequencias, largura=900, altura=420):
    # recebo as frequencias ja contadas pra nuvem e tabela de termos baterem
    nuvem = WordCloud(
        width=largura,
        height=altura,
        background_color="white",
        # o colormap YlOrBr deixava as palavras amarelo claro ilegiveis no
        # fundo branco, entao sorteio so entre tons mais escuros
        color_func=lambda *args, **kwargs: CORES[kwargs["random_state"].randint(0, len(CORES) - 1)],
        max_words=80,
        prefer_horizontal=0.9,
        random_state=42,  # sem isso a nuvem muda de lugar a cada clique
        # "publica" (audiencia/consulta publica) aparecia enorme e escondia o resto
        relative_scaling=0.3,
        max_font_size=110,
    )
    return nuvem.generate_from_frequencies(frequencias).to_array()
