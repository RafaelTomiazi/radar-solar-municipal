# Modelo de linguagem (LLM) rodando local, novo no TP4.
# Usa a biblioteca Transformers da HuggingFace pra baixar o modelo uma vez e
# depois rodar tudo na propria maquina, sem chamar servico nenhum na nuvem.
#
# Modelo escolhido: Qwen/Qwen2.5-0.5B-Instruct (a justificativa completa esta em
# Docs/Project/integracao_llm.md). Resumindo: entende portugues, segue instrucao
# (e um modelo "Instruct"), tem licenca Apache 2.0 e roda na CPU com uns 2 GB
# de RAM. Da pra trocar por outro modelo pela variavel RADAR_LLM_MODELO.
#
# Por que esse arquivo separado da api.py? Pra API continuar subindo mesmo em
# maquina sem torch/transformers (o Streamlit Cloud, por exemplo). Nesse caso as
# rotas de LLM respondem 503 explicando o motivo, e o resto da API funciona.

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TempoEsgotado

MODELO_PADRAO = "Qwen/Qwen2.5-0.5B-Instruct"
NOME_MODELO = os.environ.get("RADAR_LLM_MODELO", MODELO_PADRAO)
# quantos segundos a API espera a resposta do modelo antes de desistir (504)
# (comecei com 90 s, mas com a maquina ocupada uma resposta chegou a 76 s)
TEMPO_LIMITE = int(os.environ.get("RADAR_LLM_TIMEOUT", "180"))

# estado do modelo. comeca vazio e so carrega na primeira chamada (carga
# preguicosa), senao a API demorava uns 20 s pra subir toda vez
_modelo = None
_tokenizador = None
_erro_carga = None
_trava = threading.Lock()
# um trabalhador so: a CPU nao ganha nada rodando duas geracoes ao mesmo tempo,
# e assim da pra aplicar o tempo limite com future.result(timeout=...)
_executor = ThreadPoolExecutor(max_workers=1)


class ModeloIndisponivel(Exception):
    # o modelo nao carregou (biblioteca faltando, sem internet no primeiro
    # download, memoria insuficiente...). a API transforma isso em 503
    pass


class TempoLimiteModelo(Exception):
    # o modelo demorou mais que TEMPO_LIMITE. a API transforma em 504
    pass


def bibliotecas_instaladas():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


def carregar_modelo():
    # carrega o modelo uma vez so. a trava evita que duas requisicoes ao mesmo
    # tempo carreguem duas copias e estourem a memoria
    global _modelo, _tokenizador, _erro_carga
    if _modelo is not None:
        return _modelo, _tokenizador

    with _trava:
        if _modelo is not None:
            return _modelo, _tokenizador
        if os.environ.get("RADAR_LLM_DESATIVADO") == "1":
            _erro_carga = "LLM desativado pela variável RADAR_LLM_DESATIVADO=1."
            raise ModeloIndisponivel(_erro_carga)
        if not bibliotecas_instaladas():
            _erro_carga = (
                "torch e transformers não estão instalados neste ambiente. "
                "Instale com: pip install -r requirements-llm.txt"
            )
            raise ModeloIndisponivel(_erro_carga)

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        try:
            # na primeira vez baixa da HuggingFace (~1 GB) e guarda no cache
            # local (~/.cache/huggingface). das proximas vezes le do disco
            _tokenizador = AutoTokenizer.from_pretrained(NOME_MODELO)
            _modelo = AutoModelForCausalLM.from_pretrained(
                NOME_MODELO,
                # float32 na CPU: bfloat16 economiza memoria mas fica bem mais
                # lento em CPU comum. com GPU o dtype="auto" seria melhor.
                # (no transformers 5 o parametro se chama dtype, antes era torch_dtype)
                dtype=torch.float32,
            )
            _modelo.eval()
            # uma thread por nucleo fisico (cpu_count conta os logicos, com
            # hyperthreading e o dobro). comecei com "logicos menos um" (7 aqui)
            # e com o Chrome e o Streamlit abertos a geracao foi de 15 s pra 76 s:
            # thread demais disputando 4 nucleos deixa o torch mais lento
            torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
            _erro_carga = None
        except Exception as erro:  # noqa: BLE001
            _modelo, _tokenizador = None, None
            _erro_carga = "Falha ao carregar %s: %s" % (NOME_MODELO, erro.__class__.__name__)
            raise ModeloIndisponivel(_erro_carga) from erro

    return _modelo, _tokenizador


def status():
    # usado pela rota GET /llm/status
    return {
        "modelo": NOME_MODELO,
        "carregado": _modelo is not None,
        "bibliotecas_instaladas": bibliotecas_instaladas(),
        "erro_carga": _erro_carga,
        "tempo_limite_s": TEMPO_LIMITE,
    }


def _gerar(mensagens, max_tokens):
    # a geracao em si. roda dentro do executor
    import torch

    modelo, tokenizador = carregar_modelo()
    # o chat template monta o texto no formato que o modelo Instruct foi
    # treinado (papeis system/user/assistant)
    texto = tokenizador.apply_chat_template(mensagens, tokenize=False, add_generation_prompt=True)
    entrada = tokenizador([texto], return_tensors="pt")
    with torch.no_grad():
        saida = modelo.generate(
            **entrada,
            max_new_tokens=max_tokens,
            # sem sorteio: a mesma pergunta da a mesma resposta, o que deixa o
            # resultado reproduzivel e o cache faz sentido
            do_sample=False,
            repetition_penalty=1.1,
            pad_token_id=tokenizador.eos_token_id,
        )
    # corta o prompt e fica so com o que o modelo escreveu
    novos = saida[0][entrada["input_ids"].shape[1]:]
    return tokenizador.decode(novos, skip_special_tokens=True).strip()


def gerar(instrucao, texto_usuario, max_tokens=200):
    # chamada que a API usa. devolve (texto, segundos)
    mensagens = [
        {"role": "system", "content": instrucao},
        {"role": "user", "content": texto_usuario},
    ]
    # carrega fora do executor pra erro de carga virar 503 na hora, e nao
    # contar no tempo limite (o primeiro download pode levar minutos)
    carregar_modelo()
    inicio = time.time()
    futuro = _executor.submit(_gerar, mensagens, max_tokens)
    try:
        resposta = futuro.result(timeout=TEMPO_LIMITE)
    except TempoEsgotado as erro:
        raise TempoLimiteModelo("O modelo passou de %d s sem responder." % TEMPO_LIMITE) from erro
    return resposta, round(time.time() - inicio, 2)
