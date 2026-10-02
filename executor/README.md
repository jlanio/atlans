# Atlans Executor

O **executor** é o componente de execução distribuída do Atlans. Ele conecta ao servidor via WebSocket, recebe workflows criptografados, executa o motor `flow/` localmente e retorna resultados em tempo real.

## Sumário

- [Visão Geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Setup](#instalação-e-setup)
- [Configuração](#configuração)
- [Execução](#execução)
- [Painel ao vivo](#painel-ao-vivo)
- [Docker](#docker)
- [Protocolo de Comunicação](#protocolo-de-comunicação)
- [Criptografia](#criptografia)
- [GeoSync — Sincronização de Arquivos](#geosync--sincronização-de-arquivos)
- [Limites de Recursos](#limites-de-recursos)
- [Troubleshooting](#troubleshooting)
- [HOST_ALIASES para Executores Externos](#host_aliases-para-executores-externos)

---

## Visão Geral

No Atlans, **toda execução de workflow acontece nos executores** — não existe Celery nem workers no servidor. O servidor é responsável por orquestrar, criptografar e despachar jobs; o executor é responsável por executar.

### Três jeitos de rodar um executor

A stack do servidor (`docker-compose.yml`) **não sobe executor nenhum**: o
primeiro é matriculado pelo painel (Executores → gerar o código) e roda onde
você quiser, inclusive no mesmo host.

| Jeito | Onde roda | Caso de uso |
|---|---|---|
| **Docker** | Qualquer máquina com Docker (`install.sh` servido pelo painel, ou `docker-compose.executor.yml`) | O caminho padrão: servidores, VMs, o próprio host da stack |
| **Python nativo** | Uma máquina com Python 3.12 (`python -m executor`) | Acesso a bancos internos e dados locais, desenvolvimento |
| **Desktop** | Máquina do usuário (app Electron, Windows) | Dados locais, prototipagem, uso individual |

Os três usam o mesmo código (`executor/`) — a diferença está no ambiente de execução e na forma como as variáveis de ambiente são configuradas.

### Quickstart (`install.sh`)

A tela de matrícula do painel (Executores → o executor → matricular) mostra o
comando pronto, com os endereços da instalação:

```bash
curl -fsSL https://<site>/executores/install | bash -s -- --executor-id=<ID> --otp=<OTP>
```

Requisitos na máquina: `docker` (com o plugin `compose`), `git` e `curl`; o
script confere. Ele clona o repositório (`--repo`, padrão: o que o servidor
configurou em `EXECUTOR_REPO_URL`), baixa a CA interna, semeia o `executor/.env`,
constrói a imagem, matricula e sobe o container com `docker-compose.executor.yml`.

| Flag | Para quê |
|---|---|
| `--executor-id=<ID>` / `--otp=<OTP>` | A identidade e o código de matrícula (sem eles, o script pergunta) |
| `--server=<URL>` / `--public-server=<URL>` | O host dos executores e o site (padrão: os do servidor que serviu o script) |
| `--dir=<caminho>` | Onde instalar (padrão `~/atlans-executor`) |
| `--repo=<URL git>` | O repositório a clonar |
| `--memoria=<N>G` | Limite de memória do container (padrão 75 % da memória que o Docker enxerga, mínimo 2G) |
| `--force` | Refaz uma instalação existente (apaga os certificados antigos) |

O script só executa depois de baixado inteiro (o corpo está numa função chamada
na última linha): um download cortado não roda meio instalador.

---

## Pré-requisitos

- **Python 3.12** — a versão das imagens Docker, do app desktop e do CI
- Acesso à plataforma Atlans (URL do servidor)
- **Executor ID** e um **OTP de enrollment** (gerados no painel, em Executores)

As bibliotecas geoespaciais (GDAL, GEOS, PROJ) vêm embutidas nas wheels do `pyogrio`, do `shapely` e do `pyproj`: não há nada para instalar no sistema. Só numa plataforma sem wheel publicada o pip compilaria esses pacotes, e aí precisaria de `libgdal-dev`, `libgeos-dev` e `libproj-dev` (ou `brew install gdal geos proj`).

---

## Instalação e Setup

### 1. Instale as dependências

```bash
# Num ambiente só do executor, de preferência
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate

# Dependências mínimas (execução básica)
pip install -r executor/requirements.txt

# Dependências completas (todas as categorias de nós)
pip install -r executor/requirements-full.txt
```

Os dois arquivos são **locks**: todas as dependências, travadas, com o hash de cada
arquivo, e o pip confere os hashes sozinho. Nada é resolvido na hora da instalação,
então a máquina recebe as mesmas versões do Docker e do app desktop, e uma versão
recém-publicada (ou um arquivo trocado no PyPI) não entra. As fontes, o que se edita,
são os `.in` ao lado. Para regenerar os locks: `python scripts/travar_python.py`, ver
[CONTRIBUTING, "Dependências Python"](../CONTRIBUTING.md#dependências-python-locks-com-hash).

### 2. Faça o enrollment

```bash
python -m executor enroll     --executor-id=<ID> --otp=<OTP> --server=https://agents.<dominio>
```

O comando gera o par Ed25519, envia o CSR, recebe e persiste o certificado mTLS,
fixa a chave pública do servidor e grava o `EXECUTOR_ID` no `.env`.

Gere o par ID + OTP no painel, em **Executores** → **Gerar OTP**. O código é de
uso único e vale por 24 horas.

> **No Windows, use o app desktop.** Ele traz o Python embarcado e faz o
> enrollment por formulário — sem terminal, sem Docker, sem clonar o repositório.
> Ver [`desktop/`](../desktop/).

> Existia aqui um wizard interativo (`python -m executor setup`), removido junto
> com `executor/setup.py`. Ele dependia de `input()`, que não existe em nenhum
> dos ambientes onde o executor roda de verdade: container sem `-it`, serviço, e
> o app desktop, que captura os pipes. Nos três, o wizard estourava `EOFError`
> no lugar da mensagem útil.

> O OTP pode ir por **stdin** em vez de argv, o que evita expô-lo na linha de
> comando do processo:
>
> ```bash
> echo "<OTP>" | python -m executor enroll --otp-stdin --executor-id=<ID> --server=<URL>
> ```

---

## Configuração

Arquivo: `executor/.env`

### Variáveis obrigatórias

| Variável | Descrição | Onde obter |
|---|---|---|
| `EXECUTOR_ID` | UUID do executor | Plataforma > Admin > Executores > Novo Executor |

Além do `EXECUTOR_ID`, o executor exige o **certificado mTLS** em
`EXECUTOR_CERT_DIR` — produzido pelo enrollment, não configurável à mão. A
checagem das duas coisas está em `config.assert_configured()` e
`config.assert_enrolled()`.

> `EXECUTOR_API_KEY` **não existe mais**. A autenticação por API key foi
> substituída por mTLS com enrollment por OTP; `SERVER_SIGNING_PUBLIC_KEY` também
> deixou de ser configurada à mão — vem no bundle do enrollment e é fixada
> (pinning) por `executor/server_key.py`.

### Variáveis opcionais — Conexão

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_SERVER_URL` | — (obrigatória; o enroll grava) | URL WebSocket do host dos executores da instalação |
| `EXECUTOR_VERSION` | `1.0.0` | Versão exibida na plataforma quando o executor roda fora da imagem Docker (o app desktop define a dele). Na imagem vale a gravada no build — versão do produto + commit do checkout, ex. `2.15.0+3f02f44` (`executor/versao.py`) —, acima do `.env` (um valor diferente do `1.0.0` antigo gera aviso no boot) |
| `EXECUTOR_RECONNECT_MAX_DELAY` | `15` | Cap (segundos) do backoff exponencial de reconexão |
| `NONCE_CACHE_TTL` | `600` | TTL do cache de nonces anti-replay (segundos) |

### Variáveis opcionais — Segurança e ciclo de vida

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_MAX_JOB_EXPIRY_SECONDS` | `900` | Teto da duração declarada do envelope de um job (`expires_at - issued_at`) |
| `EXECUTOR_CLOCK_SKEW_SECONDS` | `300` | Folga de relógio na checagem de expiração de jobs/comandos |
| `EXECUTOR_MAX_CLOCK_SKEW_SECONDS` | `900` | Teto rígido de deriva do relógio local. Acima dele, todo job/comando é recusado apontando o NTP — com deriva grande a janela de aceitação passaria do `NONCE_CACHE_TTL` e o anti-replay deixaria de valer. Subir este valor exige subir `NONCE_CACHE_TTL` junto |
| `EXECUTOR_AUTO_RESTART` | `auto` | Reinício ao receber `config_changed` do servidor: `auto` re-executa o processo fora de container e, em container, sai com código 1 para o Docker reiniciar (`restart: on-failure`); `always` sempre re-executa; `never` só encerra (use com systemd/pm2/NSSM). Com supervisor (`EXECUTOR_SUPERVISOR_PID`) o auto-restart é desligado |

> As quatro primeiras são lidas em `executor/job_validator.py`, junto do comentário que explica cada valor.

### Variáveis opcionais — Chaves e certificado

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_CERT_DIR` | `/data/certs` se `/data` existe, senão `./certs` | Diretório do cert mTLS + chaves gravados no enrollment: `cert.pem`, `chain.pem`, `ca.pem`, `key.pem` (chave Ed25519 do cert mTLS) e `x25519_key.pem` (chave de envelope) |
| `EXECUTOR_PRIVATE_KEY` | *(vazio)* | Chave privada X25519 em base64 (raw). Alternativa ao arquivo — **não** é gerada automaticamente: a chave nasce no enrollment |
| `EXECUTOR_PRIVATE_KEY_PATH` | `<EXECUTOR_CERT_DIR>/x25519_key.pem` | Caminho da chave X25519 gerada no enrollment. É o caminho alternativo usado pelo Electron |

### Variáveis opcionais — Recursos

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_MAX_CONCURRENT` | `4` | Jobs em execução simultânea (faixa 1–256) |
| `EXECUTOR_MAX_QUEUE_SIZE` | `50` | Fila local máxima — back-pressure se cheia (faixa 1–10 000) |
| `EXECUTOR_JOB_TIMEOUT` | `3600` | Timeout por job em segundos (mínimo 1, sem teto) |
| `EXECUTOR_ARTIFACTS_DIR` | `~/AtlansExecutor/artifacts` | Diretório de artefatos gerados |

> Valor fora da faixa, ou que não é um inteiro, não derruba o executor: ele avisa
> no log e usa o padrão (`executor/_ambiente.py`). A tela de Ajustes do app
> desktop aplica as mesmas faixas — `desktop/src/shared/limites.ts`, com teste que
> as compara com `executor/config.py`.

### Variáveis opcionais — Logging e painel

| Variável | Padrão | Descrição |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nível: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_COLOR` | `auto` | Cores no terminal: `auto`, `always`, `never`. `never` também desliga o painel |
| `LOG_FILE_AGENT` | *(vazio)* | Arquivo de log do executor (rotativo 10MB, 5 backups) |
| `LOG_FILE_WORKFLOW` | *(vazio)* | Arquivo de log dos workflows (rotativo 10MB, 5 backups) |
| `EXECUTOR_DASHBOARD` | `auto` | Painel ao vivo: `auto`, `on`, `off` (ver [Painel ao vivo](#painel-ao-vivo)) |
| `EXECUTOR_DASHBOARD_INTERVAL` | `1.0` | Segundos entre atualizações do painel (mínimo `0.25`) |
| `EXECUTOR_LOG_DIR` | `<pai de ARTIFACTS_DIR>/logs` | Onde o painel grava os logs. No host, `~/AtlansExecutor/logs`; no Docker, `/data/logs` |

> **Com o painel ativo, `LOG_FILE_AGENT` passa a receber *todos* os loggers** — `executor.*`, `flow.*`, `websockets`, `asyncio`, terceiros —, e não apenas `executor.*`/`httpx`. Ele vira o espelho fiel do que ia para o terminal. `LOG_FILE_WORKFLOW`, se definido, continua sendo um arquivo dedicado adicional.

### Variáveis opcionais — GeoSync

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_SYNC_DIRS` | *(vazio)* | Pastas para sincronizar (separadas por vírgula). Vazio = desabilitado |
| `EXECUTOR_SYNC_INTERVAL` | `30` | Intervalo de scan em segundos. O `.env.example` (semente de toda instalação nova) e o app desktop gravam `10` |
| `EXECUTOR_SYNC_MODE` | `upload` | Modo: `upload`, `download`, `bidirectional`, `catalog` (ver abaixo). O `.env.example` grava `bidirectional` |
| `EXECUTOR_SYNC_CONFLICT_STRATEGY` | `remote-wins` | Conflito: `local-wins`, `remote-wins`, `keep-both` |
| `EXECUTOR_SYNC_TRIGGERS` | *(vazio)* | Triggers adicionais de sincronização |

### Variáveis opcionais — Rede

| Variável | Padrão | Descrição |
|---|---|---|
| `EXECUTOR_HOST_ALIASES` | *(vazio)* | Reescrita de hostnames internos (ver [seção dedicada](#host_aliases-para-executores-externos)) |
| `WFS_CAPABILITIES_TTL_S` | `3600` | Cache do GetCapabilities do nó WFS entre execuções e retries (segundos; 0 desliga) |
| `WEBHOOK_RESPONSE_INLINE_LIMIT` | `1048576` | Acima deste tamanho (bytes), o body do ResponseNode sobe ao MinIO em vez de trafegar pelo WebSocket |
| `EXECUTOR_ENV_PATH` | `executor/.env` | Caminho alternativo do `.env` (usado pelo Electron) |

---

## Execução

```bash
python -m executor
```

O executor executa o seguinte fluxo de inicialização:

1. Carrega configuração (variáveis de ambiente)
2. Carrega a chave privada X25519 gravada no enrollment. **Nunca gera uma nova**:
   se ela faltar, o executor falha pedindo um novo enrollment (a chave pública
   correspondente já está registrada no servidor desde o enrollment)
3. Inicia a `ExecutorJobQueue` com workers concorrentes
4. Inicia a `ExecutorConnection` (WebSocket com mTLS e reconnect automático)
5. Opcionalmente inicia o GeoSync para cada diretório configurado
6. Aguarda `SIGTERM`/`SIGINT` para shutdown gracioso

> **Subcomando `status`.** `python -m executor status [--json]` consulta o
> servidor e lista os workspaces acessíveis a este executor (autenticando com o
> cert mTLS do enrollment) — útil para verificar o vínculo sem subir o executor.

### Painel ao vivo

Num terminal interativo, depois do boot o executor troca o log passo-a-passo por um **painel que se atualiza a cada segundo**:

```
+- Atlans Executor v1.0.0  ·  a1b2c3d4…  ·  wss://agents.exemplo.org ---------+
| geo-01 · container · 8 núcleos    ● conectado há 4h10m                      |
+- workflows -----------------------+- recursos ---------------------------- +
| total       133                   | CPU exec    47.2% de 8  █████░░░░░      |
| ok          129                   | RAM exec  812 MB · 34 threads           |
| erro          3                   | RAM livre 6.1 / 16.0 GB  ██████░░░░     |
| cancelado     1                   | Disco     221 / 930 GB  ████████░░      |
| sucesso     97.0%                 | pico nos wf cpu 91% · mem 1420 MB       |
| última hora  18  (1 erro)         | nós        1152 · 3 falha(s)            |
| vazão       1.4 wf/min            +---------------------------------------- +
+-----------------------------------+- fila & conexão ---------------------- +
+- tempos --------------------------+ slots      2 / 4  ████░░░░              |
| média    34.7s                    | fila       3 / 50  ░░░░░░░░             |
| p50 (1h) 18.1s                    | heartbeat  4.0s                         |
| p95 (1h) 184.0s                   | reconexões 2 · retry em 2.5s            |
| + lento  9c3b7712… 10m11s         +---------------------------------------- +
| último   a71f0099… ok 12.3s       |
| uptime   4h12m                    |
+-----------------------------------+
+- em execução (2) ----------------------------------------------------------+
| a71f0099…   buffer_1                                        1m02s      7/12 |
| 3c02aa11…   spatial_join_2                                    14s       2/9 |
+- geosync · /data/sync -----------------------------------------------------+
| ↑ enviado 42 arq · 1.2 GB     ↓ baixado 8 arq · 96 MB                       |
+- alertas · 1h: 1 erro, 3 avisos -------------------------------------------+
| 14:02:11 WARN  CONN  Conexão encerrada. Reconectando em 2.5s.               |
| 14:47:03 ERROR EXEC  Job 8f2a… falhou: relation "vias" does not exist       |
+----------------------------------------------------------------------------+
log: ~/AtlansExecutor/logs/executor.log  l log/painel  a alertas  d debug  q sai
```

**O log passo-a-passo não se perde**: ele vai para `~/AtlansExecutor/logs/executor.log`, rotativo (10 MB × 5), no mesmo formato de sempre. Acompanhe em outro terminal com `tail -f`.

O bloco **alertas** mostra os últimos `WARNING`/`ERROR`, para que um executor em loop de reconexão ou falhando todos os jobs não fique com a causa escondida. As seções **em execução** e **geosync** só aparecem quando têm o que mostrar, e o layout se adapta ao tamanho do terminal — de 4 colunas em telas largas até uma coluna só, cortando blocos por prioridade quando falta altura.

#### Atalhos de teclado

| Tecla | O que faz |
|---|---|
| `l` ou `Tab` | **Alterna entre o painel e o log linha a linha** — o comportamento histórico volta na hora, sem reiniciar o executor |
| `a` | Abre o histórico completo de alertas (o buffer guarda 200 linhas; o rodapé mostra 6) |
| `d` | **Liga/desliga o log `DEBUG` sem reiniciar** — o arquivo passa a receber detalhe na hora |
| `r` | Força a reconexão agora, sem esperar o backoff (que chega a `EXECUTOR_RECONNECT_MAX_DELAY`) |
| `z` | Zera os contadores da sessão (jobs em execução e conexão não são afetados) |
| `p` | Pausa/retoma a atualização do painel |
| `?` ou `h` | Mostra/esconde a lista de atalhos |
| `q` | Encerra o executor com o mesmo shutdown ordenado de um `SIGTERM` |
| `Ctrl+C` | Encerra o executor |

Alternar não custa registro nenhum: **o arquivo de log continua gravando nos dois modos**. No modo log o console volta a receber tudo e o arquivo segue como espelho; no modo painel só o arquivo recebe.

Quando o `DEBUG` está ligado, o rodapé mostra `[DEBUG]` — ele multiplica o volume do arquivo, e esquecer ligado enche o disco em silêncio. O `httpx`/`httpcore` ficam em `INFO` mesmo em modo debug, senão cada frame HTTP afogaria o log do `executor` e do `flow`. Depois de um `z`, o bloco **workflows** passa a mostrar *zerado há X* para que "total 0" não pareça um executor recém-subido.

Em telas estreitas a barra do rodapé encolhe, mantendo sempre `l`, `?` e `q` — o `?` lista todos.

Os atalhos exigem que o `stdin` seja um terminal. Se ele estiver redirecionado (`< /dev/null`, um pipe, um supervisor), o painel continua funcionando e o rodapé avisa que não há atalhos.

> No Windows a tecla `q` é a forma mais confiável de encerrar: o `asyncio` não registra handlers de sinal nessa plataforma, e o `Ctrl+C` pode derrubar o processo antes do shutdown ordenado.

#### Quando o painel liga

| Situação | Painel |
|---|---|
| `EXECUTOR_DASHBOARD=off` | não |
| `EXECUTOR_DASHBOARD=on` (e `rich` instalado) | sim, mesmo sem terminal interativo |
| `rich` não instalado | não — o executor sobe normalmente com o log de sempre |
| `stdout` ou `stderr` não é terminal | não — cobre Docker sem `-it`, systemd/journald, `\| tee`, Electron |
| `LOG_COLOR=never`, `NO_COLOR` ou `CI` definidos | não |
| `TERM` ausente ou `dumb` (POSIX) | não |
| terminal menor que 60×12 | não |
| resto | sim |

O motivo de não ligar aparece no banner de boot (`Painel: desligado (...)`). Se o arquivo de log não puder ser aberto, o painel também não liga — o objetivo é *mover* o log para disco, não apagá-lo.

O subcomando `python -m executor enroll` nunca aciona o painel.

### Shutdown gracioso

Ao receber sinal de encerramento, o executor:

- Fecha o painel e devolve o terminal (o encerramento volta a sair em texto)
- Aguarda jobs em andamento (timeout de 120s)
- Drena os resultados pela conexão ainda viva
- Cancela a conexão WebSocket, o renewal do certificado e o GeoSync
- Fecha pools de conexão asyncpg
- Encerra

---

## Canal com um supervisor (`EXECUTOR_DASHBOARD=json`)

Quando o executor é iniciado por um programa em vez de por uma pessoa — o app
desktop em [`desktop/`](../desktop/) —, o painel `rich` não serve: não há
terminal. No lugar dele, `EXECUTOR_DASHBOARD=json` liga um canal de eventos
estruturados.

O modo **nunca é inferido**: emitir JSON no `stdout` de quem esperava log humano
quebraria o consumidor em silêncio. Quem quer o canal, pede.

### Separação dos canais

| Canal | Conteúdo |
|---|---|
| `stdout` | **apenas** NDJSON, uma linha por evento |
| `stderr` | log humano formatado, exatamente como sempre |
| arquivo | log rotativo, ligado junto (best-effort) |

Isso funciona sem refactor porque o handler de console do `logging_setup` já
escreve em `stderr` — o `stdout` estava livre.

### Eventos (executor → supervisor)

Uma linha JSON por evento, terminada em `\n`, **sempre** começando por `{"v":1,`.
O prefixo é framing: o leitor descarta qualquer linha que não case, o que cobre
um `print()` acidental de um nó de workflow caindo no mesmo `stdout`.

| `t` | Quando | Conteúdo |
|---|---|---|
| `hello` | primeira linha, sempre | pid, executor_id, versão do Python, comandos aceitos |
| `state` | mudança de fase | `booting` (com `step`), `running`, `draining`, `stopped`, `failed` |
| `snapshot` | a cada `EXECUTOR_DASHBOARD_INTERVAL` | o `Snapshot` inteiro — os mesmos campos que o painel `rich` desenha |
| `job` | imediato | `started`, `finished`, `cancelled` |
| `sync` | imediato | eventos do GeoSync |
| `conn` | imediato | `connecting`, `connected`, `reconnecting`, `terminal` |
| `log` | `WARNING+` | nível, alias, mensagem |
| `ack` | resposta a comando | `ok`, `detail`, `id` do comando |

Os eventos imediatos existem porque o tick perde informação: `last_finished`
guarda **um** job, então dois terminando no mesmo segundo fariam o primeiro
desaparecer do histórico.

`state: failed` carrega o passo exato (`server_key`, `private_key`) e o motivo.
É a diferença entre a UI oferecer "refazer enrollment" e oferecer "tentar de
novo" — sem ele, uma falha de boot chega ao supervisor apenas como código de
saída 1.

### Comandos (supervisor → executor)

Uma linha JSON por comando no `stdin`. Espelham 1:1 as teclas do painel: a GUI
ganha exatamente a superfície de controle que o operador do terminal tem.

| Comando | Tecla | Efeito |
|---|---|---|
| `{"cmd":"shutdown"}` | `q` | shutdown ordenado — o **mesmo** caminho de um SIGTERM |
| `{"cmd":"reconnect"}` | `r` | interrompe o backoff de reconexão |
| `{"cmd":"reset_stats"}` | `z` | zera os contadores da sessão |
| `{"cmd":"toggle_debug"}` | `d` | alterna o nível de log |
| `{"cmd":"ping"}` | — | responde `ack` (verificação de liveness) |
| `{"cmd":"sync_now"}` | — | força uma varredura do GeoSync agora (sem tecla equivalente no painel) |

O campo `id` é opcional e volta no `ack` correspondente.

### `EXECUTOR_SUPERVISOR_PID`

O supervisor passa o próprio PID nesta variável. Duas coisas mudam:

1. Sobe o watchdog de [`executor/supervisor.py`](supervisor.py), que verifica a
   cada 5 s se o supervisor continua vivo — comparando PID **e** `create_time`,
   porque o sistema operacional recicla números de processo. Se o supervisor
   morrer (usuário matando o app pelo Gerenciador de Tarefas), o executor faz
   shutdown **ordenado** em vez de virar órfão segurando a conexão WebSocket.
2. Desliga o auto-restart interno. `os.execve` substitui o processo em POSIX,
   mas no Windows cria um processo novo e encerra o atual — o supervisor
   perderia o rastro do executor real e subiria um segundo. Havendo supervisor,
   religar é trabalho dele; o executor apenas sai com código diferente de zero.

---

## Docker

O executor é distribuído como uma imagem Docker standalone via `docker-compose.executor.yml`.

### Primeira configuração

Rode o enrollment gravando o cert num diretório do host que será montado no
container. **Não** monte sobre `/app/executor` — isso esconde o código do
executor. Grave em `/data/certs`:

```bash
# A imagem: construída daqui (`docker compose -f docker-compose.executor.yml build`)
# ou carregada do asset da release (`docker load < atlans-executor-docker-amd64.tar.gz`).
mkdir executor-certs
docker run --rm \
  -v $(pwd)/executor-certs:/data/certs \
  atlans-executor:latest \
  python -m executor enroll --executor-id=<ID> --otp=<OTP> \
    --cert-dir=/data/certs --server=https://agents.<dominio>
```

O `-it` não é necessário: o enrollment não é interativo. Depois monte
`./executor-certs` em `/data/certs` no compose (ou gere os certs direto no
volume `executor-data`, sem bind).

### Iniciar

```bash
docker compose -f docker-compose.executor.yml up -d
```

### Ver logs

```bash
docker compose -f docker-compose.executor.yml logs -f
```

> O painel ao vivo **não** liga sob Docker: sem `-it` o stdout não é um terminal, e o compose já define `EXECUTOR_DASHBOARD=off` explicitamente. A saída de `docker logs` continua sendo o log linha a linha de sempre.

### Parar

```bash
docker compose -f docker-compose.executor.yml down
```

Dois processos com o mesmo outbox (no desktop, o app morto à força deixa o
Python antigo drenando por até 150 s enquanto a reabertura sobe outro): o
diário tem dono. O processo trava `.executor_results.sqlite.dono` na subida; se outro
processo vivo já segura a trava, os jobs do diário são dele e nenhum é
convertido em falha — e o processo novo segue tentando em segundo plano, para
virar o dono assim que o anterior sair (senão um terceiro converteria os jobs
vivos dele).

### Limite de memória

O container recebe o limite de `EXECUTOR_MEMORIA`, lido do `.env` **ao lado** do
`docker-compose.executor.yml` (não do `executor/.env`, que é o ambiente do
processo). O instalador grava 75% da memória que o Docker enxerga — a RAM da
máquina no Linux, a da VM no Docker Desktop —, nunca menos que `2G`, ou o valor
de `--memoria=<N>G` (mínimo `512M`, a reserva do compose). Sem a variável, o
limite é `2G`. Se o `docker-compose.executor.yml` tiver edição local, o `git pull`
do instalador aborta e o arquivo segue com o limite fixo — o instalador avisa.

```bash
echo EXECUTOR_MEMORIA=12G >> .env
docker compose -f docker-compose.executor.yml up -d
```

O `2G` fixo de antes matava o executor por OOM do cgroup em máquinas com memória
de sobra; hoje, se isso acontecer, o próximo boot reporta o job interrompido com
o limite do container na mensagem (ver "Jobs que não terminam", acima).

### Volumes e configuração

| Item | Onde no container | Descrição |
|---|---|---|
| `executor-data` (volume nomeado) | `/data` | Dados persistentes: cert mTLS + chaves em `/data/certs` (`cert.pem`, `chain.pem`, `ca.pem`, `key.pem`, `x25519_key.pem`) e artefatos em `/data/artifacts` |
| `./executor-certs` (bind opcional) | `/data/certs` (`:ro`) | Certs gerados pelo enroll no host. Comente o mount se gerou os certs dentro do container |
| bind opcional do GeoSync | `/data/sync` | Pasta local a sincronizar (descomente junto com `EXECUTOR_SYNC_DIRS`) |

A configuração vem via `env_file: executor/.env` no compose — **não** é um volume
montado. As sobrescritas do container ficam no bloco `environment:`
(`EXECUTOR_ARTIFACTS_DIR=/data/artifacts`, `EXECUTOR_CERT_DIR=/data/certs`,
`EXECUTOR_DASHBOARD=off`, `LOG_COLOR=never`).

---

## Protocolo de Comunicação

```mermaid
sequenceDiagram
    participant Ex as Executor
    participant API as Servidor (API HTTPS)
    participant WS as Servidor (WebSocket)

    Note over Ex,API: Enrollment (uma única vez) — ver "Instalação e Setup"
    Ex->>Ex: Gera par Ed25519 (cert mTLS) + par X25519 (envelope)
    Ex->>API: POST /executores/enroll<br/>{csr_pem, public_key_pem, ...}<br/>Authorization: Bearer <OTP>
    API-->>Ex: cert.pem, chain.pem, ca.pem, server_signing_public_key
    Note over Ex: Persiste cert + chaves e fixa (pin) a chave do servidor

    Note over Ex,WS: Toda conexão — autenticação por mTLS (sem API key, sem JWT)
    Ex->>WS: WebSocket {SERVER_URL}/ws/executores/{EXECUTOR_ID}<br/>SSLContext mTLS: cert + key + CA fixada do enrollment
    Ex->>WS: {type: "handshake", protocol_version: "1.0", executor_version: "1.0.0", system_info}

    loop A cada 30s
        Ex->>WS: {type: "heartbeat"}
    end

    loop A cada 10s
        Ex->>WS: {type: "capacity", running: N, queued: M, max_concurrent: X, max_queue: Y}
    end

    loop Na conexão e a cada 60s
        Ex->>WS: {type: "inventario", ativos: [job_id], resultados: [job_id], truncado}
    end

    Note over WS: Dispatch de job (cifrado ponta a ponta)
    WS->>Ex: {type: "job", envelope: {...}, ephemeral_public, ciphertext, signature}
    Ex->>Ex: Verifica assinatura Ed25519 (chave fixada do servidor)
    Ex->>Ex: Descriptografa payload (X25519 ECDH + HKDF + AES-256-GCM)
    Ex->>WS: {type: "ack", job_id, status: "enqueued"}
    Ex->>Ex: Executa flow/

    loop Para cada nó executado
        Ex->>WS: {type: "node_event", node, status, ...}
    end

    Ex->>WS: {type: "job_result", job_id, run_id, status: "ok"|"error"}

    Note over WS,Ex: Controle (assinado Ed25519)
    WS->>Ex: {type: "cancel", job_id} · {type: "control", action}
```

### Tipos de mensagem

A autenticação é por **mTLS**: a identidade do executor vem do certificado
(CN/serial), validado no `accept()` do WebSocket. **Não há API key nem JWT
intermediário** — a URL é `{SERVER_URL}/ws/executores/{EXECUTOR_ID}` e o cert +
chave + CA fixada vão no `SSLContext` do connect. `control` e `cancel` exigem
assinatura Ed25519 do servidor e são recusados sem ela.

| Direção | Tipo | Descrição |
|---|---|---|
| Executor → Servidor | `handshake` | `protocol_version` + `executor_version` (+ `system_info`) na conexão |
| Executor → Servidor | `heartbeat` | Keep-alive (30s) |
| Executor → Servidor | `capacity` | Report de capacidade (10s): `running`, `queued`, `max_concurrent`, `max_queue` |
| Executor → Servidor | `node_event` | Progresso de execução por nó |
| Executor → Servidor | `job_result` | Resultado final do job |
| Executor → Servidor | `ack` | Confirmação de recebimento do job (`status: "enqueued"`); o servidor promove o run para "Em andamento" |
| Executor → Servidor | `inventario` | Na conexão e a cada 60s: jobs `ativos` (fila/execução) e com `resultados` ainda não confirmados — os do outbox, os da fila em memória e, no espaço que sobrar, os enviados há menos de 90 s (o servidor pode ainda não os ter processado). O servidor fecha como perdidos os runs deste executor que não estão aqui. Com o outbox ilegível o inventário sai marcado `truncado` (nada é fechado por ausência) |
| Servidor → Executor | `job` | Job criptografado para execução |
| Servidor → Executor | `drive_event` | Evento de sincronização de arquivos |
| Servidor → Executor | `cancel` | Interrompe um job em execução ou enfileirado (assinado Ed25519). Para um job que o executor não tem, devolve um `job_result` `cancelled` (o servidor fecha o run) e guarda uma lápide por 10 min: se o job chegar atrasado, é descartado sem rodar. Se o resultado do job estiver a caminho (outbox, fila em memória ou enviado há menos de 90 s), não responde nada — o job terminou aqui |
| Servidor → Executor | `control` | Ação de controle (assinado Ed25519): `revoked`, `shutdown`, `config_changed`, `purge_artifacts` |
| Servidor → Executor | `error` | Recusa de uma mensagem do executor (`invalid_json`, `invalid_schema`, `handshake_required`, `invalid_capacity`, `unsupported_protocol_version`), com o detalhe. Não é assinada: o executor só a registra em WARNING |

### Jobs que não terminam: o diário em disco

Todo job aceito entra num diário no mesmo SQLite do outbox de resultados
(`ARTIFACTS_DIR/.executor_results.sqlite`, tabela `jobs_em_voo`) e só sai quando
o resultado dele entra no outbox, na mesma transação. Se o processo morre no
meio — falta de memória, `kill`, queda da máquina —, o próximo boot encontra o
job no diário e o reporta como falha (`executor_lost`), com o ponto em que ele
estava (na fila ou executando) e o limite de memória do container. Antes o run
ficava "Em andamento" no servidor para sempre: o executor voltava em segundos e
ninguém mais sabia do job.

### Back-pressure

Quando a fila local do executor atinge `EXECUTOR_MAX_QUEUE_SIZE`, novos jobs são **rejeitados** com mensagem de erro `"Fila do executor cheia — back-pressure."`. O servidor pode então redirecionar para outro executor disponível.

---

## Criptografia

Toda comunicação de jobs entre servidor e executor é criptografada end-to-end. Mesmo com TLS, os payloads são cifrados para garantir que o servidor armazene apenas dados opacos.

### Algoritmos

| Etapa | Algoritmo | Finalidade |
|---|---|---|
| Troca de chaves | **X25519 ECDH** | Gera shared secret entre servidor e executor |
| Derivação de chave | **HKDF-SHA256** | Deriva chave AES a partir do shared secret |
| Criptografia | **AES-256-GCM** | Cifra o payload do workflow |
| Assinatura | **Ed25519** | Garante autenticidade e integridade do job |
| Anti-replay | **Nonce cache** | Impede reenvio de jobs com mesmo nonce |

### Fluxo de criptografia

```mermaid
graph TD
    subgraph Servidor
        A[Gera par efêmero X25519] --> B[ECDH: shared_secret = X25519 server_ephemeral, agent_public]
        B --> C[HKDF-SHA256 shared_secret, salt=nonce → aes_key]
        C --> D[AES-256-GCM encrypt payload → ciphertext]
        D --> E[Ed25519 sign envelope+ephemeral+ciphertext]
        E --> F[Envia: envelope, ephemeral_public, ciphertext, signature]
    end

    subgraph Executor
        G[Recebe mensagem] --> H[Ed25519 verify signature]
        H --> I[ECDH: shared_secret = X25519 agent_private, ephemeral_public]
        I --> J[HKDF-SHA256 shared_secret, salt=nonce → aes_key]
        J --> K[AES-256-GCM decrypt ciphertext → payload]
        K --> L[Executa workflow]
    end

    F -->|WebSocket| G
```

### Formato do ciphertext

Os primeiros **12 bytes** do ciphertext decodificado de base64 são o **GCM nonce**. O restante é o ciphertext + authentication tag.

### Segurança de chaves

- A chave privada X25519 é salva com permissões `0600` (somente leitura do owner)
- Após descriptografia, variáveis sensíveis (`shared_secret`, `aes_key`, `plaintext`) são deletadas da memória (best-effort)
- O info label do HKDF é fixo: `atlas-executor-job-v1`

---

## GeoSync — Sincronização de Arquivos

O GeoSync permite sincronizar pastas locais do executor com o Drive do Workspace na plataforma.

### Componentes

| Módulo | Responsabilidade |
|---|---|
| `sync/manager.py` | Orquestrador principal |
| `sync/scanner.py` | Detecta datasets na pasta local |
| `sync/watcher.py` | Monitora mudanças em tempo real (fsevents/inotify) |
| `sync/uploader.py` | Upload de arquivos para o Drive |
| `sync/downloader.py` | Download de arquivos do Drive |
| `sync/manifest.py` | Estado local da sincronização |
| `sync/validator.py` | Valida integridade dos datasets |
| `sync/metadata.py` | Extrai metadados geoespaciais |
| `sync/trigger.py` | Triggers de sincronização |
| `sync/ignore.py` | Filtro de arquivos ignorados |

### Modos de sincronização

| Modo | Descrição |
|---|---|
| `upload` | Envia arquivos locais para o Drive (padrão) |
| `download` | Baixa arquivos do Drive para a pasta local |
| `bidirectional` | Sincronização nos dois sentidos |
| `catalog` | Registra o dataset no Drive (nome, tipo, tamanho, CRS, bbox, contagem de feições) **sem enviar os bytes** — para dado pessoal/LGPD. O conteúdo nunca sai desta máquina e só workflows que rodam neste mesmo executor leem os arquivos |

> `upload` é o que o executor usa quando `EXECUTOR_SYNC_MODE` falta — o padrão
> seguro: nada que aconteça no Drive apaga ou sobrescreve arquivo local. O
> `.env.example`, que semeia o `.env` de toda instalação nova (`static/install.sh`,
> `python -m executor enroll` e o app desktop), grava `bidirectional`. A tela de
> GeoSync do app desktop mostra o modo que está no `.env` e, sem ele, `upload`.

### Estratégias de conflito

| Estratégia | Descrição |
|---|---|
| `remote-wins` | Versão do servidor prevalece (padrão) |
| `local-wins` | Versão local prevalece |
| `keep-both` | Mantém ambas as versões (renomeia a local) |

### Configuração exemplo

```env
EXECUTOR_SYNC_DIRS=/home/usuario/dados-geo,/home/usuario/shapefiles
EXECUTOR_SYNC_INTERVAL=30
EXECUTOR_SYNC_MODE=bidirectional
EXECUTOR_SYNC_CONFLICT_STRATEGY=remote-wins
```

### Eventos Drive via WebSocket

Quando o modo inclui `download` ou `bidirectional`, o executor recebe eventos `drive_event` do servidor via WebSocket. Esses eventos informam sobre uploads feitos por outros executores ou pela interface web, permitindo download imediato sem polling.

---

## Limites de Recursos

### Configurações de limites

```env
# Máximo de jobs rodando ao mesmo tempo
EXECUTOR_MAX_CONCURRENT=4

# Tamanho máximo da fila local (back-pressure acima disso)
EXECUTOR_MAX_QUEUE_SIZE=50

# Timeout por job individual (segundos)
EXECUTOR_JOB_TIMEOUT=3600
```

### Comportamento

| Situação | Ação do executor |
|---|---|
| Jobs em execução < `MAX_CONCURRENT` | Aceita e executa imediatamente |
| Jobs em execução = `MAX_CONCURRENT`, fila < `MAX_QUEUE_SIZE` | Aceita e enfileira |
| Fila = `MAX_QUEUE_SIZE` | **Rejeita** com back-pressure |
| Job excede `JOB_TIMEOUT` | **Cancela** e retorna erro de timeout |

### Capacity report

A cada 10 segundos, o executor envia um report de capacidade ao servidor:

```json
{
  "type": "capacity",
  "running": 2,
  "queued": 3,
  "max_concurrent": 4,
  "max_queue": 50
}
```

O servidor usa essas informações para decidir para qual executor despachar o próximo job.

---

## Troubleshooting

### Erros comuns

**`Variavel obrigatoria nao definida: EXECUTOR_ID`**
> O `.env` não existe ou está incompleto — o caminho esperado aparece na própria
> mensagem, e respeita `EXECUTOR_ENV_PATH`.
>
> `python -m executor enroll --executor-id=<ID> --otp=<OTP>
> --server=https://agents.<dominio>`, ou defina `EXECUTOR_ID` no `.env` montado
> no container. No app desktop, o formulário de vínculo faz isso pela interface.

---

**`EXECUTOR_SERVER_URL deve começar com ws:// ou wss://`**
> Verifique o valor no `.env`. Use `wss://` em produção e `ws://` em desenvolvimento local.

---

**Conexão fechada com `code=4404 Executor nao encontrado`**
> O servidor não reconhece mais este executor: ele foi removido ou revogado. O
> certificado em disco continua válido localmente, mas é inútil — só um
> enrollment novo devolve o executor ao ar. No app desktop há o botão **Refazer
> enrollment**, que descarta o certificado e leva ao formulário.

---

**Executor aparece offline na plataforma após alguns minutos**
> O executor envia heartbeat a cada 30 segundos. Se o servidor não receber por 90 segundos, fecha a conexão. Verifique:
> - Conectividade de rede entre o executor e o servidor
> - Firewalls ou proxies bloqueando WebSocket
> - Logs do executor para erros de reconexão

---

**`relation "..." does not exist`**
> A tabela referenciada no workflow não existe no banco de dados configurado na credencial. Verifique:
> - O schema e o nome da tabela
> - A connection string da credencial na plataforma
> - Se o executor tem acesso de rede ao banco de dados

---

**`Falha ao descriptografar payload do job`**
> A chave privada X25519 do executor (`x25519_key.pem`, gravada no enrollment em
> `EXECUTOR_CERT_DIR`) não corresponde mais à chave pública registrada no
> servidor. Isso pode acontecer se:
> - O arquivo `x25519_key.pem` foi deletado ou substituído após o enrollment
> - O executor foi reconfigurado apontando para outra chave
>
> **Solução:** refaça o enrollment (`python -m executor enroll --executor-id=<ID>
> --otp=<OTP> --server=<URL>`) — ele gera um par novo e registra a pública no
> servidor. O executor **nunca** gera nem re-registra a chave sozinho: se
> `x25519_key.pem` faltar, ele falha no boot pedindo um novo enrollment. Apagar a
> chave e reiniciar **não** resolve. No app desktop, use **Refazer enrollment**.

---

**`Fila do executor cheia — back-pressure`**
> O executor está sobrecarregado. Possíveis ações:
> - Aumente `EXECUTOR_MAX_CONCURRENT` (se a máquina tem recursos)
> - Aumente `EXECUTOR_MAX_QUEUE_SIZE`
> - Adicione mais executores ao workspace

---

**Jobs travam e dão timeout**
> Verifique:
> - `EXECUTOR_JOB_TIMEOUT` (padrão: 3600s = 1 hora)
> - Se o workflow acessa recursos externos (banco, API) que podem estar lentos
> - Logs de workflow: defina `LOG_FILE_WORKFLOW=/tmp/workflow.log` para capturar detalhes
> - Com o painel ativo, o bloco **em execução** mostra em qual nó cada run está parado e há quanto tempo

---

**O painel não aparece**
> O motivo é impresso no banner de boot, na linha `Painel: desligado (...)`. As causas mais comuns:
> - `rich` não instalado → `pip install rich`
> - saída redirecionada ou sob Docker sem `-it` (o painel exige terminal interativo)
> - `LOG_COLOR=never` no `.env` ou no compose
>
> Para forçar: `EXECUTOR_DASHBOARD=on`.

---

**Quero ver o log passo a passo de novo**
> Aperte `l`. O painel sai, o log volta ao terminal, e `l` de novo traz o painel. Para nunca ligar o painel, use `EXECUTOR_DASHBOARD=off`.

---

**As teclas não respondem**
> O rodapé mostra os atalhos apenas quando o `stdin` é um terminal. Se ele estiver redirecionado ou o executor rodar sob um supervisor que não repassa o teclado, o painel funciona mas sem atalhos — encerre com `Ctrl+C` ou `SIGTERM`.

---

**O terminal ficou sem cursor depois de encerrar o executor**
> Não deveria acontecer — o painel é fechado em todos os caminhos de saída. Se ocorrer, `reset` (POSIX) devolve o terminal, e vale abrir uma issue com o modo de encerramento usado.

---

**Erro de conexão SSL em desenvolvimento local**
> O executor detecta automaticamente servidores locais (`localhost`, `127.0.0.1`) e desabilita verificação de certificado. Se o servidor usa um hostname customizado local, adicione-o à detecção ou use `ws://` em vez de `wss://`.

---

## Veio de um executor com o nome antigo?

Até a versão anterior, a imagem, o container e o volume do Docker chamavam-se
`atlas-executor` (sem o «n»). Agora é `atlans-executor`:

- **Pelo compose** (`docker-compose.executor.yml`, o caminho do `install.sh`): o
  próximo `up -d` recria o container com o nome novo. O volume `executor-data`
  é o mesmo, e a matrícula continua valendo.
- **Pelo `docker run`** (as instruções da release): pare e remova o antigo
  (`docker rm -f atlas-executor`) e suba o novo com o volume que já tem a
  matrícula (`-v atlas-executor-data:/data`), em vez de criar outro.

Nada muda no protocolo: o rótulo de derivação de chaves dos jobs e as
identidades mTLS não dependem do nome.

## HOST_ALIASES para Executores Externos

Quando o executor roda **fora da rede do compose do servidor** (outra máquina, Python nativo, app desktop), os workflows podem referenciar hostnames internos do Docker (ex: `db`, `redis`, `minio`) que não são resolvidos na máquina do executor.

Use `EXECUTOR_HOST_ALIASES` para mapear esses nomes para endereços acessíveis:

```env
# Formato: hostname_interno=host_externo:porta, separados por vírgula
EXECUTOR_HOST_ALIASES=db=192.168.1.10:5432,redis=192.168.1.10:6379,minio=192.168.1.10:9000
```

### Como funciona

O executor intercepta connection strings nos payloads descriptografados e substitui os hostnames internos pelos mapeados. Por exemplo:

| Original (Docker) | Reescrito (executor externo) |
|---|---|
| `postgresql://user:pass@db:5432/geo` | `postgresql://user:pass@192.168.1.10:5432/geo` | <!-- pragma: allowlist secret -->
| `redis://:senha@redis:6379/0` | `redis://:senha@192.168.1.10:6379/0` |

### Quando usar

| Cenário | Necessário? |
|---|---|
| Executor Docker no mesmo host da stack, na rede do compose | Geralmente não |
| Executor Docker ou Python nativo em outra máquina | Sim, se os workflows usam hostnames internos |
| App desktop (máquina do usuário) | Sim, quase sempre |
