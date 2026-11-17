# Integração do LLM local (TP4)

Este documento registra como escolhi o modelo de linguagem do Radar Solar Municipal e como integrei esse modelo à API FastAPI rodando inteiramente na minha máquina. Ele complementa a seção 11 do Project Charter.

## 1. O que o modelo precisa fazer

O plano de LLM escrito no TP3 (Charter, seção 10) tinha três prioridades, e as três dependem de gerar ou entender texto em português:

1. Escrever a ficha do município em linguagem simples para o gestor, a partir dos números da API (geração de texto condicionada a dados).
2. Resumir as notícias da ANEEL respondendo "isso muda algo para quem tem ou quer instalar solar?" (resumo).
3. Classificar o impacto da notícia em três classes: afeta a GD, afeta o consumidor em geral ou não afeta (classificação).

Isso eliminou cedo os modelos que só classificam. Eu queria um único modelo para as três tarefas, que lesse e escrevesse em português e que seguisse uma instrução sem precisar de treino, porque tenho só 83 notícias e nenhuma rotulada.

## 2. Minha máquina (o limite de custo computacional)

Notebook com Intel Core i7-1165G7 (4 núcleos, 8 threads), 16 GB de RAM e GPU integrada Intel Iris Xe. A Iris Xe não tem CUDA, então na prática o PyTorch roda só na CPU. Esse foi o critério que mais pesou: qualquer modelo que pedisse GPU NVIDIA ou mais de uns 6 GB de RAM deixaria o computador travado com o Streamlit aberto junto.

## 3. Candidatos e critérios

Pesquisei no HuggingFace Model Hub e comparei os candidatos pelos três critérios do enunciado: desempenho para a minha tarefa, custo computacional local e acessibilidade (dá para baixar e rodar com `transformers` sem conta, sem pagar e sem internet depois do primeiro download).

| Modelo | Tipo | Tamanho | Desempenho para a tarefa | Custo local (CPU, float32) | Acessibilidade | Decisão |
|---|---|---|---|---|---|---|
| `gpt2` | decoder (GPT) | 124 M | Treinado só em inglês e não segue instrução: só continua o texto | ~0,5 GB RAM, rápido | Livre (MIT) | Descartado |
| `neuralmind/bert-base-portuguese-cased` (BERTimbau) | encoder (BERT) | 110 M | Ótimo em português, mas não gera texto. Para classificar precisaria de fine-tuning com notícias rotuladas que eu não tenho | ~0,5 GB RAM, rápido | Livre (MIT) | Descartado |
| `google/flan-t5-base` | encoder-decoder (T5) | 250 M | Segue instrução, mas foi treinado quase todo em inglês. Em português responde curto e com erros | ~1 GB RAM | Livre (Apache 2.0) | Descartado |
| `unicamp-dl/ptt5-base-portuguese-vocab` (PTT5) | encoder-decoder (T5) | 220 M | Português nativo, mas não é instruído: precisaria de fine-tuning para resumir | ~1 GB RAM | Livre (MIT) | Descartado |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | decoder | 1,1 B | Conversa em inglês; em português mistura idiomas | ~4,5 GB RAM | Livre (Apache 2.0) | Descartado |
| `meta-llama/Llama-3.2-1B-Instruct` | decoder | 1,2 B | Bom e multilíngue | ~5 GB RAM | Repositório "gated": exige conta, aceite de licença e token. Quem for rodar o projeto teria que fazer isso também | Descartado |
| `microsoft/Phi-3.5-mini-instruct` | decoder | 3,8 B | Melhor qualidade da lista | ~15 GB RAM: não cabe com o resto aberto | Livre (MIT) | Descartado |
| `Qwen/Qwen2.5-1.5B-Instruct` | decoder | 1,5 B | Melhor que o 0,5B no português e nos números | ~6 GB RAM, cerca de 3 vezes mais lento que o 0,5B (estimado pelo tamanho) | Livre (Apache 2.0) | Alternativa (troca por variável de ambiente) |
| `Qwen/Qwen2.5-0.5B-Instruct` | decoder | 0,5 B | Instruído, multilíngue (o português está entre os idiomas de treino), contexto de 32 mil tokens. Faz as três tarefas só com prompt | ~2 GB RAM, ~950 MB em disco. Medido aqui: carga de 5 s (62 s na primeira vez, com download), 8 a 26 s por resposta | Livre (Apache 2.0), sem login | **Escolhido** |

A escolha ficou no `Qwen/Qwen2.5-0.5B-Instruct` porque é o único da lista que atende os três critérios ao mesmo tempo. Em desempenho, ele é um modelo de instrução (como o GPT, mas pequeno), então resume, classifica e escreve a ficha só mudando o prompt, sem treino; os modelos BERT e T5 em português precisariam de dados rotulados que eu não tenho. Em custo, ele cabe com folga nos 16 GB e responde na CPU em segundos, o que permite usar no painel sem o gestor desistir esperando. Em acessibilidade, tem licença Apache 2.0, não pede conta nem token, e depois do primeiro download funciona sem internet, que é o que o enunciado pede ("sem necessidade de conexão com a nuvem").

O preço dessa escolha é a qualidade. Um modelo de 0,5 bilhão de parâmetros erra mais que os grandes: às vezes repete frase, às vezes arredonda um número. Por isso tomei três cuidados. O prompt da ficha do município manda usar só os números do JSON, e eu mando esses números já formatados em português (o modelo copia melhor "12,34 MW" do que converte 12345.6 kW). Toda resposta volta marcada como gerada por IA e com os números originais ao lado (`dados_usados`), para a pessoa conferir. E deixei o nome do modelo numa variável (`RADAR_LLM_MODELO`), então quem tiver uma máquina melhor troca para o `Qwen2.5-1.5B-Instruct` sem mexer no código.

## 4. Como a integração local foi feita

### 4.1 Ambiente

Criei um ambiente virtual novo e instalei o PyTorch na versão só CPU, que vem do índice próprio do PyTorch e tem uns 200 MB (a versão padrão do pip no Windows também funciona, mas a de Linux puxa CUDA e passa de 2 GB):

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-llm.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

Versões que usei e testei: Python 3.13, torch 2.15.0+cpu, transformers 5.23.0, fastapi e uvicorn do `requirements.txt`. As dependências do LLM ficaram num arquivo separado (`requirements-llm.txt`) de propósito: o app publicado no Streamlit Cloud continua usando só o `requirements.txt`, porque o plano gratuito tem cerca de 1 GB de memória e não roda o modelo. Lá a página de IA explica isso e a API responde 503, em vez de o deploy quebrar.

### 4.2 Download e carga do modelo

O download acontece sozinho na primeira chamada: `AutoTokenizer.from_pretrained` e `AutoModelForCausalLM.from_pretrained` baixam os arquivos do Hub (~950 MB) para `~/.cache/huggingface/hub` e, das próximas vezes, leem do disco. Depois disso a API funciona com a internet desligada. No meu Windows apareceu um aviso de que o cache não consegue usar links simbólicos; ele funciona do mesmo jeito, só ocupa um pouco mais de disco, e dá para silenciar com `HF_HUB_DISABLE_SYMLINKS_WARNING=1`.

O código fica em `Code/API/llm_local.py`, separado da `api.py`. A carga é preguiçosa: a API sobe em menos de um segundo e o modelo só vai para a memória na primeira requisição (ou quando o app chama `POST /llm/carregar` para aquecer). Uma trava (`threading.Lock`) impede que duas requisições ao mesmo tempo carreguem duas cópias do modelo.

### 4.3 Ajustes para o hardware

Como não tenho GPU NVIDIA, fiz quatro ajustes. Carrego o modelo em `float32`, porque em CPU comum o `bfloat16` economiza memória mas fica bem mais lento. Uso uma thread do PyTorch por núcleo físico (`torch.set_num_threads(os.cpu_count() // 2)`, 4 aqui). Comecei com "threads lógicas menos um" (7) e, com o Chrome e o Streamlit abertos, uma ficha de município que levava 15 s no teste estourou o tempo limite de 90 s que eu tinha posto: threads demais disputando quatro núcleos deixam o torch mais lento. Mesmo depois do ajuste, com a máquina ocupada por outros programas, medi respostas de cerca de 60 s, então subi o tempo limite padrão para 180 s. Uso um único trabalhador (`ThreadPoolExecutor(max_workers=1)`), porque duas gerações ao mesmo tempo na CPU só deixam as duas mais lentas, e esse trabalhador também me permite aplicar o tempo limite com `future.result(timeout=...)`. Por fim, limito o tamanho das respostas (`max_new_tokens` de 80 a 160) e do texto de entrada (6.000 caracteres), que são o que mais pesa no tempo de geração.

Também desliguei o sorteio na geração (`do_sample=False`): a mesma pergunta dá sempre a mesma resposta, o que deixa o resultado reproduzível e faz o cache valer a pena. O cache é um `lru_cache` em memória por texto e tipo de análise, e por município.

Um ajuste de compatibilidade de versão: no transformers 5 o parâmetro `torch_dtype` virou `dtype`. Comecei com o nome antigo e troquei.

### 4.4 Rotas novas na API

| Método | Rota | O que faz |
|---|---|---|
| GET | `/llm/status` | Qual modelo, se está carregado, se as bibliotecas existem e o tempo limite |
| POST | `/llm/carregar` | Carrega o modelo na memória |
| POST | `/processar_texto` | Recebe `{"texto", "tipo"}`; `tipo` é `resumo` ou `impacto_gd` |
| POST | `/resumo-municipio` | Recebe `{"cod_ibge"}` e devolve o parágrafo para o gestor com os números usados |

Todas têm `response_model` (Pydantic), então o FastAPI valida a saída e documenta no Swagger (`/docs`). A entrada também é validada por modelo: o texto tem que ter entre 20 e 6.000 caracteres sem contar espaços, o tipo só aceita os dois valores do `Enum` e o código IBGE precisa ter 7 dígitos.

### 4.5 Tratamento de erros

Todo erro da API sai no mesmo formato (`ErroResposta`: `codigo`, `erro`, `detail` e `dica`), montado por handlers globais (`@app.exception_handler`) em vez de cada rota fazer do seu jeito. O campo `detail` manteve o nome padrão do FastAPI para o app continuar lendo igual.

| Código | Quando acontece | Exemplo de mensagem |
|---|---|---|
| 422 | Texto curto, longo, só espaços, tipo inexistente, campo faltando, IBGE inválido | `texto: Value error, o texto precisa ter pelo menos 20 caracteres além de espaços` |
| 404 | Município não existe na base | `Município 9999999 não encontrado` |
| 405 | Método errado na rota | `Method Not Allowed` |
| 502 | O modelo devolveu texto vazio | `O modelo devolveu uma resposta vazia. Tente de novo.` |
| 503 | Modelo não carregou: sem torch/transformers, desativado, falha no download ou memória | `torch e transformers não estão instalados neste ambiente...` |
| 504 | A geração passou do tempo limite (`RADAR_LLM_TIMEOUT`, padrão 180 s) | `O modelo passou de 180 s sem responder.` |
| 500 | Qualquer outra exceção, sem mostrar traceback ao usuário | `Erro inesperado: RuntimeError` |

No app, `comum.chamar_api` mostra o `detail` e a `dica` na tela, e trata separado o caso de a própria requisição passar do tempo.

## 5. Testes

O script `Code/API/testa_api_llm.py` chama todas as rotas novas pelo `TestClient` do FastAPI, incluindo os cenários de erro (o 503 é simulado desativando o modelo e o 504 baixando o tempo limite para 1 segundo), e salva cada chamada em `Docs/LLM/testes_api_llm.json`. Resultado: 18 de 18 testes passaram (8 de caminho feliz, 6 de entrada inválida com 422, 1 de 404, 1 de 405, 1 de 503 e 1 de 504).

Tempos medidos na minha máquina, com o modelo já carregado: classificação de impacto entre 8 e 10 segundos, ficha do município entre 13 e 16 segundos, resumo de notícia de 16 a 23 segundos e zero quando a resposta vem do cache.

### 5.1 O que melhorou entre a primeira e a segunda bateria

Na primeira versão o prompt da ficha do município pedia "um parágrafo de 3 a 4 frases" mais livre, e o modelo inventou. Para o Rio de Janeiro ele escreveu que a cidade fica "na região metropolitana de São Paulo" e que a energia solar "atende a cerca de 40% da população", nada disso nos dados. O resumo de notícia saiu em tópicos, com título, e não respondia se a notícia muda algo para a GD.

Mudei três coisas. Fechei o roteiro do prompt frase por frase (potência e empreendimentos; posição no estado e no Brasil; comparação com a mediana). Tirei a conta do modelo: a comparação com a mediana do estado agora vai pronta no JSON (para o Rio, "tem 40,4 vezes a potência do município típico do estado (mediana)"), porque modelo pequeno erra divisão. E criei a checagem `numeros_fora_dos_dados`, que extrai todo número do texto gerado e confere se ele existe na origem. Na segunda bateria a ficha do Rio saiu assim:

> A potência instalada de geração distribuída é de 384,69 MW, com 40.363 empreendimentos. O município está na 1ª posição no estado, com 4º lugar no Brasil. A média de potência instalada por empreendimento é de 9,5 kW, enquanto a média nacional é de 9,52 MW.

Todos os números conferem com os dados, mas o último trecho mostra o limite que ainda existe: "9,52 MW" é a mediana do estado, e o modelo chamou de "média nacional". A checagem pega número inventado, mas não pega número certo com rótulo errado. Por isso a página mostra os números originais do lado do texto, e é por isso também que deixei a troca de modelo por variável de ambiente.

### 5.2 Como reproduzir

```
pip install -r requirements-llm.txt --extra-index-url https://download.pytorch.org/whl/cpu
python Code/API/testa_api_llm.py
uvicorn Code.API.api:app --port 8000      # Swagger em http://localhost:8000/docs
streamlit run app.py                       # página "IA local (LLM)"
```
