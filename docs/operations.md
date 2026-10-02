# Operações em produção

Playbook para quem opera uma instalação do Atlans. Para subir uma do zero, veja
[self-hosting.md](self-hosting.md) e
[mtls-bootstrap.md](mtls-bootstrap.md).

Nos exemplos, `<PUBLIC_HOST>`, `<AGENTS_HOST>` e `<S3_HOST>` são os hosts do
`.env`: o site, o dos executores e o do S3.

## Sumário

- [Atualizar a instalação](#atualizar-a-instalação)
- [Voltar de versão](#voltar-de-versão)
- [Backup e restore](#backup-e-restore)
- [Admin seed](#admin-seed)
- [Smoke test](#smoke-test)
- [Adicionar nova env var](#adicionar-nova-env-var)
- [Rotacionar senha do provisioner step-ca](#rotacionar-senha-do-provisioner-step-ca)
- [Rate limit por IP](#rate-limit-por-ip)
- [Prazo das consultas ao banco](#prazo-das-consultas-ao-banco)
- [CSP do frontend (bloqueante)](#csp-do-frontend-bloqueante)
- [Configuração dinâmica do Traefik](#configuração-dinâmica-do-traefik)
- [Servidor MCP](#servidor-mcp)
- [Logs que sobrevivem ao deploy](#logs-que-sobrevivem-ao-deploy)
- [Fluxos com nós renomeados](#fluxos-com-nós-renomeados)
- [Python 3.12 e os scripts dos usuários](#python-312-e-os-scripts-dos-usuários)
- [Troubleshooting](#troubleshooting)

## Atualizar a instalação

Com o código da versão nova no host (`git pull`, ou `git checkout` da tag):

```bash
docker compose --profile prod up -d --build --remove-orphans
```

O Compose recria só o serviço cuja imagem ou configuração mudou. Não use
`--force-recreate`: ele recriaria também Traefik, step-ca, Redis e MinIO.

Quem constrói as imagens em outro lugar (um CI, um registry) aponta
`ATLANS_API_IMAGE` e `ATLANS_WEB_IMAGE` para elas no `.env`, roda
`docker compose --profile prod pull api-prod web-prod` e sobe sem `--build`.
A imagem do web precisa do contexto de build `raiz` (a raiz do repositório),
de onde vêm a `LICENSE` e o `THIRD-PARTY-NOTICES.md` que ela leva:
`docker build -f web/Dockerfile.ui --build-context raiz=. -t <imagem> web`.

Antes de subir, compare o `.env.example` da versão nova com o seu `.env`: uma
variável nova não chega sozinha, e a API recusa subir com uma obrigatória
faltando ou inválida.

### Migrations (passo manual)

A API **não** roda migrations: não há entrypoint automático de Alembic (o
antigo foi removido — ver comentário em [Dockerfile.api](../Dockerfile.api)).
Após toda atualização que muda o schema, rode à mão:

```bash
docker compose exec api-prod alembic upgrade head
```

Na primeira subida (banco vazio), o mesmo comando cria o schema inteiro: a
revisão base executa o [scripts/init_schema.sql](../scripts/init_schema.sql) e
o `schema.sql` de cada extensão instalada (`app/extensoes/`).

## Voltar de versão

Volte o código à versão boa (`git checkout` da tag anterior) e suba como em
[Atualizar a instalação](#atualizar-a-instalação). Com imagens de um registry,
guarde uma tag por versão e aponte `ATLANS_API_IMAGE` e `ATLANS_WEB_IMAGE`
para a anterior.

Se a versão ruim trouxe migração, leia antes o que vem abaixo.

### Sobre o banco

Migrations Alembic **não são revertidas automaticamente**. Se o
problema for de schema:

```bash
docker compose exec api-prod alembic downgrade -1
```

Mas atenção: downgrade pode perder dados (`drop column`, etc.). Em
prod, **prefira fix-forward** a downgrade.

## Backup e restore

### step-ca (CA interna que assina certs mTLS)

**Crítico**: perder o volume `step-ca-data` invalida todos os executores
enrolados. Backup obrigatório.

```bash
# Backup manual
make backup-stepca
# Cria backups/step-ca-YYYY-MM-DD-HHMM.tar.gz, mantém 14 últimos.
```

**Cron diário** (no host):

```cron
0 3 * * * cd /caminho/da/instalacao && ./scripts/backup-stepca.sh >> backups/cron.log 2>&1
```

**Restore**:

```bash
# 1. Tirar quem monta o volume: a step-ca e a API (que lê o root dele)
docker compose --profile prod rm -sf step-ca api-prod

# 2. Limpar volume corrompido
docker volume rm step-ca-data
docker volume create step-ca-data

# 3. Restaurar do backup
docker run --rm \
    -v step-ca-data:/data \
    -v $(pwd)/backups:/backup:ro \
    alpine tar xzf /backup/step-ca-YYYY-MM-DD-HHMM.tar.gz -C /data

# 4. Subir e validar
docker compose --profile prod up -d step-ca api-prod
make smoke
```

Se o fingerprint da CA mudou (backup de instância diferente), atualize
`STEPCA_ROOT_FINGERPRINT` no `.env` (e na cópia dele que o seu deploy
guardar, se houver uma).

### PostgreSQL

`pg_dump` rotineiro do volume externo (gerenciado fora deste compose).
Não há automação aqui — depende do seu provedor de Postgres.

```bash
# O DATABASE_URL da API tem o driver (`postgresql+asyncpg://`) e às vezes um
# `?ssl=...` do asyncpg — o pg_dump não aceita nenhum dos dois. O `sed` tira o
# driver e a query (o libpq usa `sslmode=prefer` por padrão). POSIX: funciona
# em bash e em sh/dash. Rode no host: nenhum container do compose tem pg_dump.
U=$(printf %s "$DATABASE_URL" | sed -e 's/+asyncpg//' -e 's/?.*//')
pg_dump "$U" --no-owner --no-privileges -F c -f atlans-$(date +%F).dump
```

## Admin seed

Primeiro admin (idempotente — não duplica):

```bash
make seed-admin
# (interativo: pede email e senha >= 12 chars)
```

Ou non-interactive:

```bash
docker compose exec api-prod python -m app.cli create-admin \
    --email admin@example.com --password 'senha-forte-de-pelo-menos-12'
```

Se o email já existir mas não for admin, o comando **promove** a admin
e atualiza a senha.

## Smoke test

```bash
make smoke
```

Valida em sequência (a API e o web, por dentro do container: em produção eles
não publicam porta no host):
- API `/ping` responde
- Schema Alembic aplicado (`alembic current` retorna versão)
- Redis PING
- MinIO `/minio/health/live`
- step-ca healthy (prod)
- Web `:3000` responde
- O `install.sh` dos executores sai com o fingerprint da CA (prod): sem ele, a
  API foi reiniciada em vez de recriada depois do `bootstrap-stepca`
- O `install.sh` servido anuncia `wss://<AGENTS_HOST>` (prod): `AGENTS_URL` e
  `AGENTS_HOST` concordam
- `<AGENTS_HOST>` servido com o cert da CA interna, sem CDN na frente (prod)

Saída: `Resultado: N/M OK` ou lista do que falhou.

## Adicionar nova env var

1. Adicionar a var no [.env.example](../.env.example) com placeholder ou comentário.
2. Adicionar leitura em [app/core/config.py](../app/core/config.py) ou onde for usada.
3. Dizer no PR, e nas notas da versão, que as instalações precisam dela: o
   `.env` de cada uma não muda sozinho.
4. Se a var é necessária para o frontend, repassá-la em `web-prod` e `web-dev`
   no `docker-compose.yml` (lembrando que vars `NEXT_PUBLIC_*` vazam para o
   browser e são gravadas no build).

## Rotacionar senha do provisioner step-ca

Em caso de comprometimento, ou rotação periódica:

```bash
# 0. Backup do volume antes de tudo
make backup-stepca

# 1. Para o step-ca
docker compose --profile prod stop step-ca

# 2. Gera nova senha (do usuário step do container, UID 1000)
openssl rand -base64 48 > secrets/stepca_password.txt
chmod 600 secrets/stepca_password.txt
sudo chown 1000:1000 secrets/stepca_password.txt

# 3. Atualiza o .env (e a cópia dele que o seu deploy guardar)
sed -i.bak -E "s|^STEPCA_PROVISIONER_PASSWORD=.*|STEPCA_PROVISIONER_PASSWORD=\"$(cat secrets/stepca_password.txt)\"|" .env && rm .env.bak

# 4. Cria um par de chaves novo para o provisioner, cifrado com a senha nova
#    (atlans-app é o STEPCA_PROVISIONER_NAME padrão; use o do seu .env), e
#    reinicia a step-ca, que só lê o ca.json novo ao subir
docker compose --profile prod up -d step-ca
docker compose --profile prod exec step-ca \
    step ca provisioner update atlans-app \
        --password-file=/run/secrets/stepca_password \
        --create
docker compose --profile prod restart step-ca

# 5. Recria a API: o container só lê o .env ao ser criado
docker compose --profile prod up -d api-prod
```

O provisioner ganha um par de chaves novo, e só a API o usa, para assinar os
pedidos de certificado. Os certificados já emitidos foram assinados pela CA, e
não por essa chave: nenhum executor perde nada.

## Rate limit por IP

Os limites por rota (`10/hour` no enrollment, `10/minute` no patch de
executor, etc.) usam como chave o IP real do cliente, resolvido pelo
`X-Forwarded-For`: caminhando o header da direita para a esquerda, o primeiro
IP que **não** é um proxy conhecido (`TRUSTED_PROXIES` + `EDGE_PROXIES`, ver
[app/core/trusted_proxy.py](../app/core/trusted_proxy.py)). Atrás da
Cloudflare o primeiro elemento do header é escrito pelo cliente e não vale
nada — por isso o sentido da leitura.

Os contadores ficam no Redis da aplicação (`REDIS_URL`) e valem para a API
inteira. Em memória, `api-prod` (`uvicorn --workers 4`) daria a cada worker o
próprio balde — um limite de `10/minute` valeria até 4x — e tudo zeraria a
cada deploy. A escolha, em [app/core/rate_limiter.py](../app/core/rate_limiter.py):

1. `RATE_LIMIT_STORAGE_URI`, se definida: outra URI `redis://`, ou
   `memory://` para voltar à memória de cada worker;
2. senão, o `REDIS_URL` (o bloco `x-api-env` do `docker-compose.yml` monta os
   dois; vazia equivale a ausente);
3. sem nenhum dos dois, memória (testes, dev sem Redis).

O storage Redis é síncrono: um round-trip curto na rede do compose por
request nas rotas com limite, dentro do event loop do worker. Por isso cada
ida ao Redis tem prazo de 0,25 s (`socket_timeout` e `socket_connect_timeout`;
a ida normal leva bem menos de 1 ms, e parâmetros na query da URI, como
`?socket_timeout=2`, valem mais): sem ele, um Redis travado — que aceita a
conexão e não responde — prende o worker inteiro sem fim. Se o Redis cair ou
estourar o prazo, o slowapi cai para memória sozinho e volta quando ele
responder; a API não cai junto, os limites só voltam a valer por worker nesse
intervalo (logs do slowapi: `Rate limit storage unreachable - falling back to
in-memory storage` e `Rate limit storage recovered`). Com o Redis travado, o
preço é o loop parado por até 0,5 s na primeira falha e por até 0,25 s em cada
nova conferência, que o slowapi faz com 2, 4, 8, 16 e 32 s de intervalo e
recomeça. A resolução do nome `redis` não entra nesse prazo: com o container
fora do ar, o DNS do Docker repassa a consulta ao do host.

Uma URI que o `limits` recusa (esquema desconhecido, porta inválida, `memory`
sem `://`) não derruba a API: cai em memória com `Rate limit: storage ...
recusado` no log.

Onde estão os contadores, sem expor a senha:

```bash
docker compose --profile prod logs api-prod | grep "Rate limit: contadores em"
# Rate limit: contadores em redis://redis:6379/0 (compartilhados; memoria se cair)
docker compose --profile prod exec api-prod python -c "from app.core.rate_limiter import limiter as l; print(type(l._storage).__name__, l._storage.check())"
# RedisStorage True
```

O balde é por IP **e por caminho**: o slowapi usa a URL como parte da chave
(`key_style="url"`), então rotas com parâmetro no caminho contam por valor —
os `600/minute` dos tiles valem por tile, e os `10/minute` do download, por
artefato. Com os limites globais, um escritório, uma turma ou um CGNAT de
operadora atrás de um único IP divide o mesmo balde. Os limites com mais
chance de pegar uso normal:

| Rota | Limite por IP |
|---|---|
| Login e cadastro | `20/minute` (o bloqueio por conta segura a força bruta) |
| Esqueci a senha / reenviar verificação | `3/minute` / `2/minute` |
| Conversa do assistente | `120/hour` |
| Agendamentos em `/me` | `60/minute` |
| Enrollment e OTP de executor | `10/hour` (uma leva grande de executores num site só esbarra nele) |
| Gatilho por webhook | `20/minute` por IP e workflow |

Para acompanhar as recusas:

```bash
docker compose --profile prod logs api-prod --since 24h | grep -c '" 429'
```

Em dev os contadores também sobrevivem ao `--reload` e ao restart — os limites
por hora ou por dia (enrollment, renovação de cert) podem travar quem está
testando. `RATE_LIMIT_STORAGE_URI=memory://` no `.env` de dev evita, e para
zerar os contadores:

```bash
docker compose exec redis sh -c 'redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --scan --pattern "LIMITS:*" | xargs -r redis-cli --no-auth-warning -a "$REDIS_PASSWORD" del'
```

## Prazo das consultas ao banco

Cada comando da API no Postgres tem prazo ([app/core/db.py](../app/core/db.py)).
Sem ele, uma consulta travada — lock esperando outro, plano ruim, rede que some
sem derrubar a conexão — segurava a conexão sem fim; cada worker tem 13, e
poucas presas esgotam o pool dele (o `POOL_TIMEOUT` só limita a espera por uma
conexão livre).

| Variável | Padrão | O que faz |
|---|---|---|
| `DB_STATEMENT_TIMEOUT` | 60 s | O Postgres cancela o comando (`QueryCanceledError: canceling statement due to statement timeout`). Conta a espera por lock. A conexão segue boa, e um savepoint (`begin_nested`) contém o erro. |
| `DB_COMMAND_TIMEOUT` | 90 s | O asyncpg desiste de esperar a resposta (`asyncio.TimeoutError`, que do Python 3.11 em diante é o próprio `TimeoutError` embutido): o banco que nem responde. Maior que o anterior, para que no caso normal quem cancela seja o Postgres. A conexão é descartada, e a transação de quem chamou vai junto, savepoint ou não. |

Vazias valem o padrão; `0` desliga cada uma; um valor que não é número inteiro
de segundos (`60s`, `5min`) vale o padrão com aviso no log. As migrações não
são afetadas (o Alembic usa um engine próprio), e a CLI de manutenção
(`python -m app.cli`) roda sem prazo, salvo se a variável estiver definida.
Mudar o valor exige recriar o container
(`docker compose --profile prod up -d api-prod`).

Conexão descartada por prazo estourado ou por tarefa cancelada tem o socket
derrubado na hora (`_abortar_conexao_presa` em `db.py`): o fechamento cortês
do asyncpg espera a confirmação do cancelamento sem prazo, e com a rede muda
(NAT que esqueceu o fluxo, host congelado) nem o `command_timeout` nem um
`asyncio.wait_for` em volta da escrita voltavam — medido com um proxy que
congela os dois sentidos. O backend órfão no Postgres morre no
`statement_timeout`.

A consulta legítima mais lenta, para conferir a folga (com a extensão
`pg_stat_statements` habilitada):

```sql
SELECT round(max_exec_time) AS max_ms, calls, left(query, 120)
FROM pg_stat_statements ORDER BY max_exec_time DESC LIMIT 20;
```

Uma tarefa que precise de mais tempo abre exceção só na transação dela, com
`SET LOCAL statement_timeout = '80s'` antes do comando longo — até o
`DB_COMMAND_TIMEOUT`, que é do lado do cliente e não se ergue por transação.
Acima disso, a tarefa precisa de um engine próprio. O `command_timeout` vale
para o `executemany` inteiro, não por linha: um lote de 500 linhas precisa
terminar em 90 s. Um `UPDATE` que espera um lock mais que 60 s — a linha do
agendamento travada durante o despacho, uma corrida de índice único contra
uma transação longa — falha em vez de esperar.

## CSP do frontend (bloqueante)

O frontend manda uma `Content-Security-Policy` em toda resposta
(`web/next.config.ts`, no `headers()` — e não no middleware, cujo matcher
exclui a superfície pública). O navegador **bloqueia** o que a política não
prevê e relata o bloqueio em `/api/csp-report`; o coletor grava uma linha por
violação no log do container (até 20 por POST):

```bash
docker compose --profile prod logs web-prod --tail 500 | grep csp-report
# [csp-report] {"documento":"https://<PUBLIC_HOST>/","diretiva":"script-src-elem","bloqueado":"https://…","origem":…,"disposicao":"enforce"}
```

Os relatos não chegam na hora. Em produção (HTTPS) o Chrome usa o
`report-to` (Reporting API) e manda em lotes, até um minuto depois do bloqueio —
um lote pode passar de 20 KB, por isso o coletor aceita até 256 KB. Em HTTP o
Chrome não entrega pelo Reporting API e, com `report-to` presente, também
ignora o `report-uri`: por isso o `next dev` sai sem `report-to`, e ali cada
bloqueio vira um POST na hora. Uma instalação servida sem TLS não registra
relato nenhum.

Ela rodou antes em modo relatório (`-Report-Only`, `"disposicao":"report"`),
que não bloqueia nada, para colher o que a política ainda não previa. O único
relato legítimo das telas do app era o **Monaco** (o editor de código dos nós
Python/SQL), que o `@monaco-editor/loader` buscava no jsdelivr: agora ele vem da
própria origem, de `public/monaco/vs`, copiado de `node_modules/monaco-editor`
por `web/scripts/copiar-monaco.mjs` antes de todo `npm run build` e `npm run dev`
(a pasta é gerada: fica fora do git e do contexto do Docker). O worker do
**MapLibre** segue o mesmo caminho, de `public/maplibre`, copiado por
`web/scripts/copiar-maplibre.mjs`: desde o maplibre-gl 6 ele roda a partir de uma
URL que a biblioteca, empacotada pelo Next, não acha sozinha. Sem a cópia o mapa
abre, mas os tiles vetoriais nunca chegam, e nada aparece no console.

Triagem de cada relato, agora que ele é um bloqueio de verdade:

- **Código ou biblioteca nossa** (React Flow, tiles, URLs pré-assinadas do S3,
  WebSocket): a funcionalidade está quebrada para quem usa. Liberar a fonte na
  política, ou consertar o uso, e subir a imagem web.
- **O que a borda injeta**: atrás da Cloudflare, ela insere em todo HTML da zona o beacon
  do Web Analytics (`static.cloudflareinsights.com/beacon.min.js/<versão>`)
  enquanto a injeção automática estiver ligada no painel dela (Analytics &
  Logs → Web Analytics → Manage site → Advanced options → JS snippet
  injection). O host já está liberado no `script-src`; o POST do beacon
  (`cloudflareinsights.com`) cabe no `https:` do `connect-src`. Desligar o Web
  Analytics no painel torna a entrada inócua — a política não precisa mudar.
  Outro recurso da borda que injete script de outro host (Rocket Loader, Zaraz,
  um app do painel) passa a ser bloqueado: liberar o host ou desligar o recurso.
- **Extensão do navegador** (`"bloqueado":"chrome-extension"`, `moz-extension`):
  ruído da máquina de quem navega, não do app. Ignorar.
- **O resto** é o que a CSP existe para pegar: script ou conexão que ninguém
  pediu. Investigar antes de liberar.

**Fora da origem, só HTTPS.** Em produção a política libera `https:`/`wss:`
para tiles, URLs pré-assinadas e WebSocket de outro host, e nada em `http:` —
numa página HTTPS o navegador barraria isso como conteúdo misto de qualquer
forma. O `next dev` libera também `http:`/`ws:`, porque lá o WebSocket vai
direto à API em outra porta (`NEXT_PUBLIC_API_PORT`) e o MinIO é
`http://localhost:9000`. Uma instalação servida sem TLS precisa manter API,
WebSocket e MinIO na mesma origem (o proxy reverso) ou servir o MinIO por HTTPS.

**Voltar ao modo relatório** é um build novo da imagem web, não uma variável: o
`next.config.ts` é avaliado no build. Trocar o header para
`Content-Security-Policy-Report-Only` e subir a imagem.

**Não é da CSP:** com o DevTools aberto na Home, o console do Chromium mostra
`GL Driver Message … performance warning: READ-usage buffer was written, then
fenced, but written again before being read back`, repetido (o número colado
na frente é o contador de repetições do DevTools). É um aviso de desempenho do
processo de GPU sobre a medição de erro da projeção do globo do MapLibre — ela
lê um pixel de volta a cada poucos quadros por um buffer de leitura (caso
aberto em [maplibre/maplibre-gl-js#7872](https://github.com/maplibre/maplibre-gl-js/issues/7872)).
Não é erro, não afeta o mapa e só aparece com o DevTools aberto; o portal
`/share` (Mercator) não o emite.

## Configuração dinâmica do Traefik

Middlewares, opções de TLS e certificados ficam em **`traefik-dynamic/dynamic.yml`**, e o compose
monta o **diretório** que o contém:

```yaml
- ./traefik-dynamic:/etc/traefik/dynamic:ro
```
```
--providers.file.directory=/etc/traefik/dynamic
--providers.file.watch=true
```

**O diretório não é preciosismo.** Bind mount de arquivo único prende o *inode*, não o caminho: se
o arquivo do host for apagado e outro escrito no lugar, o container segue lendo o inode antigo — já
desvinculado — até ser recriado. Uma atualização que apaga o arquivo antes de copiar o novo deixa o
Traefik com a versão velha: um middleware recém-adicionado, como o `rate-mcp`, não existe para ele,
o router `api-mcp`, que o referencia, é descartado, e `https://<PUBLIC_HOST>/mcp` passa a cair no
catch-all do Next.js — HTML para um cliente MCP, sem nenhum sintoma nas outras rotas.

**E por que na raiz, e não em `traefik/dynamic/`?** Porque `traefik/` guarda o que é da
instalação, e não do repositório: o `atlans-ca` (o intermediário da CA interna e o certificado do
`AGENTS_HOST`), que o `make bootstrap` cria e o `bootstrap-stepca` preenche, fora do git. O
`traefik-dynamic/` vem do repositório e muda a cada versão. Separados, quem atualiza o código (um
usuário de deploy sem root, por exemplo) não precisa escrever na pasta da CA.

Três consequências práticas:

- **Não volte a montar o arquivo solto**, e não apague o arquivo antes de copiar o novo ao
  atualizar.
- **Não mova o diretório para dentro de `traefik/`**: essa pasta é da instalação.
- Com `watch=true`, mudar o `dynamic.yml` **não** exige recriar o Traefik. Ele relê sozinho; o log
  registra a recarga.

Um router que referencia middleware inexistente é **descartado em silêncio** para quem só olha o
HTTP — mas não para quem lê o log:

```bash
docker compose --profile prod logs traefik --tail 500 | grep -i "does not exist"
```

Se a resposta de um path da API for a página do Next.js, comece por aqui.

## Servidor MCP

A rota `/mcp` roda dentro do processo da API (`app/mcp/`) e é autenticada por
token pessoal, não pelo JWT da sessão. O contrato para quem conecta um cliente
está em [mcp.md](mcp.md); aqui fica só o que muda em produção.

### Variáveis

| Variável | Efeito |
|---|---|
| `MCP_ALLOWED_HOSTS` | Hosts aceitos pelo transporte, separados por vírgula. Vazia (padrão) = o host do `FRONTEND_URL` (com e sem porta), `localhost:*` e `127.0.0.1:*`. Um `Host` fora da lista recebe **421** antes de qualquer ferramenta rodar. Só mexa se a API passar a atender por outro domínio. A lista é lida na montagem do servidor MCP, na subida do processo: **mudar o valor exige recriar o container** (`docker compose --profile prod up -d api-prod`), não basta reescrever o `.env`. |
| `MINIO_EXTERNAL_ENDPOINT` | Host que as URLs pré-assinadas prendem na assinatura. Em produção **precisa** ser `https://<S3_HOST>`; com `http://localhost:9000` os downloads do Drive, dos artefatos e do MCP só abrem de dentro do Docker. |
| `RATE_LIMIT_STORAGE_URI` | Não afeta as cotas do MCP (que ficam no Redis da aplicação, chaveadas por token). Para o resto da API, ver [Rate limit por IP](#rate-limit-por-ip). |
| `FRONTEND_URL` | Base das URLs de compartilhamento do portal devolvidas por `get_portal_info`. Em produção, `https://<PUBLIC_HOST>`. |

`MCP_ALLOWED_HOSTS` entra pelo bloco `x-api-env` do `docker-compose.yml`, como
as demais: defina no `.env` (ver
[Adicionar nova env var](#adicionar-nova-env-var)).

### Aviso de boot do MinIO

Quando `MINIO_EXTERNAL_ENDPOINT` aponta para um host local (`localhost`,
`127.0.0.1` ou `minio`), a API registra um `WARNING` logo depois de garantir o
bucket. Em produção esse aviso é um defeito de configuração, não ruído:

```bash
docker compose --profile prod logs api-prod --tail 200 | grep -i 'MINIO_EXTERNAL_ENDPOINT'
```

Uma linha ali significa que toda URL pré-assinada que a API entregar hoje —
Drive, artefatos e MCP — vai falhar para quem estiver fora da rede do compose.
Corrija a variável e recrie o container.

### Traefik

O router `api-mcp` (labels do `api-prod`) casa `Host(<PUBLIC_HOST>) &&
PathPrefix(/mcp)` com **prioridade 20**. A prioridade é obrigatória: o
catch-all `web-prod` responde por `Host(<PUBLIC_HOST>)` com prioridade 1 e, sem
ela, `/mcp` cairia no Next.js e o cliente receberia HTML em vez de JSON.

`PathPrefix` e não `Path` porque a API registra as duas grafias — `/mcp` e
`/mcp/` — como rotas exatas para o mesmo servidor, e as duas precisam chegar
até ela. Nenhuma redireciona: um `307` faria o cliente repetir a requisição
(com o `Authorization` junto) para um `Location` montado pela app, que roda sem
`--proxy-headers` e portanto escreveria `http://`.

Os middlewares são `strip-executor-cert-header@file` e `rate-mcp-<borda>@file`
(240 req/min por IP, burst 60), onde `<borda>` é o `BORDA_MIDDLEWARE` do
`.env`: `rate-mcp-borda-aberta` conta pelo IP da conexão e
`rate-mcp-cloudflare-only` pelo último IP que a Cloudflare anexa ao
`X-Forwarded-For` (`ipStrategy.depth: 1`) — mesmo desenho de `rate-download`.
Um `ipStrategy.depth` numa instalação sem CDN não é «por IP»: o Traefik apaga
o `X-Forwarded-For` de quem não está em `trustedIPs` antes dos middlewares, a
fonte do limite fica vazia e todos os clientes caem num balde só. **Nunca**
aplique `mtls-executores` neste router: o
`<PUBLIC_HOST>` pode estar atrás de um CDN, que termina o TLS, e nenhum
certificado de cliente chegaria ao Traefik. O mTLS é só do `<AGENTS_HOST>`.

### Conferir que está no ar

O `initialize` do MCP exige os dois headers de `Accept` — sem eles o transporte
recusa antes de olhar o corpo:

```bash
curl -sS -i https://<PUBLIC_HOST>/mcp \
  -H "Authorization: Bearer ${ATLANS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

Esperado: `200` com o nome do servidor (`atlans`) e a versão no resultado.
Diagnóstico rápido do que mais aparece:

| Resposta | Causa |
|---|---|
| HTML do Next.js | O router `api-mcp` não subiu ou perdeu a prioridade — confira as labels e `docker compose config` |
| `401` com `WWW-Authenticate: Bearer` | Token ausente, revogado, expirado ou de conta suspensa (o servidor está de pé) |
| `421` | `Host` fora de `MCP_ALLOWED_HOSTS` |
| `429` | Teto do `rate-mcp` no Traefik |
| `307` | Nenhum caso conhecido: `/mcp` e `/mcp/` são rotas exatas para o mesmo servidor e nenhuma redireciona. Um `307` aqui é o roteamento da borda mandando para outro caminho — confira a regra do router `api-mcp` |

Sem token, um `POST` na rota responde `401` — isso já prova que o servidor está
montado e que o roteamento chegou na API.

## Logs que sobrevivem ao deploy

Com `LOG_DRIVER=journald` no `.env` (num host com systemd), `api-prod` e
`web-prod` gravam no journald do host, com as tags `atlans-api` e
`atlans-web`. Cada atualização recria esses dois containers, e o driver
padrão (`json-file`) apaga o log junto: o rastro de um problema some na
atualização seguinte.

```bash
# O de sempre continua funcionando (o Docker lê do journald):
docker compose --profile prod logs api-prod --tail 200

# Direto no journal, inclusive de containers que já foram recriados
# (as horas são as do fuso do host; `timedatectl` diz qual é):
journalctl -t atlans-api --since "2026-01-15 12:55" --until "2026-01-15 13:05"

# Worker da API que o uvicorn matou e recriou (5 s sem responder, falta de memória...):
journalctl -t atlans-api --since today | grep -E 'Child process \[[0-9]+\] died'
```

O espaço é o teto do próprio journald (`SystemMaxUse`, por padrão 10% do disco
e no máximo 4 GB): quando enche, sai o mais antigo. Para guardar mais, aumente
`SystemMaxUse` em `/etc/systemd/journald.conf`. O journal precisa ser
persistente — sem o diretório `/var/log/journal`, ele vive em memória e some no
próximo boot.

## Fluxos com nós renomeados

Um fluxo salvo com o nome antigo de um nó falha na partida com `Node 'X' não
encontrado para instância` — foi o caso do `DriveTrigger` (hoje `DataInput`) e do
`ArtifactOutput` (hoje `DataOutput`), renomeados numa versão anterior sem migrar
o que já estava salvo. O comando reescreve workflows e versões; é idempotente e, sem
`--aplicar`, só lista o que mudaria:

```bash
docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos
docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos --aplicar
```

A reescrita é no lugar e alcança também as versões — "restaurar versão" não a
desfaz. Guarde as duas tabelas antes do `--aplicar`:

```bash
# No host (nenhum container do compose tem pg_dump), com o DATABASE_URL do .env.
U=$(printf %s "$DATABASE_URL" | sed -e 's/+asyncpg//' -e 's/?.*//')
pg_dump "$U" -t workflows -t workflow_versions -F c -f fluxos-antes-de-migrar-nos.dump
```

O que o comando preserva:

- **Expressões que citam o nó.** Sem alias válido (o editor grava o rótulo do
  catálogo, "Drive de arquivos"), os outros nós o citam pelo nome
  (`$DriveTrigger.metadata.original_name`). O nome antigo fica fixado como alias
  — o título do nó no editor passa a mostrá-lo — e a saída que mudou de nome
  (`metadata.drive_file_id` → `metadata.file_id`) é reescrita nas expressões.
  Formas que ele não reescreve com segurança (`named.X`, `nodes['id']`, entrada
  mapeada, código Python) saem no relatório como `REVISAR a mao`.
- **Download protegido.** O `ArtifactOutput` com credencial vira `DataOutput`
  com `isPublic=False` — no nó novo o padrão é público, e renomear sem isso
  publicaria um download que era protegido.

O que ele NÃO faz: transferir a marca de "desabilitado" do admin para o nó
novo (desabilitar o `DataOutput` pararia também os fluxos que já o usam). Se um
nome antigo estiver desabilitado, o comando avisa. O mapa de nomes mora em
`flow/nodes/contrato.py` (`NOMES_ANTIGOS`).

## Python 3.12 e os scripts dos usuários

API, executor (Docker, CLI) e app desktop rodam Python 3.12 — era 3.10. O código
da plataforma foi ajustado e testado; o que pode mudar de resultado é o código
que o **usuário** escreve no nó PythonScript, que roda no interpretador do
executor. O sandbox libera `enum`, `random` e `re`, e neles o 3.12 mudou:

| Script do usuário | Python 3.10 | Python 3.12 |
|---|---|---|
| `f"{Uso.URBANO}"` com `class Uso(str, Enum)` | `urbano` (o valor) | `Uso.URBANO` |
| `str(Classe.ALTA)` com `IntEnum` | `Classe.ALTA` | `3` |
| `random.sample(um_set, 2)` | funciona | `TypeError` (use `sorted(um_set)`) |
| `random.randrange(10.0)` | funciona | `TypeError` (use inteiro) |
| `re.search("abc(?i)", s)` — flag no meio do padrão | funciona | `re.error` (flag no início) |

Enquanto houver executor antigo (3.10) na frota, o mesmo fluxo pode dar
resultado diferente conforme o executor que o roda — atualizar a imagem do
executor e o app desktop encerra a diferença. Para `Enum`, `f"{x.value}"` vale
nas duas versões.

Também saiu do sandbox o módulo `typing`: ele permitia `eval` com os builtins
reais (`typing.ForwardRef(...)._evaluate`, `typing.get_type_hints(...)`), uma
fuga do sandbox. Anotação de tipo não precisa dele — `list[int]`, `dict[str, float]`
e `X | None` são embutidos. Script que importa `typing` falha na validação, com a
mensagem de módulo não permitido.

## Troubleshooting

### Agent não conecta

```bash
docker compose --profile prod logs api-prod --tail 100 | grep -iE 'mtls|cert'
```

| Sintoma | Causa provável | Fix |
|---|---|---|
| `Cert mTLS ausente ou invalido` | Traefik não está repassando cert | Verificar middleware `pass-executor-cert` em `traefik-dynamic/dynamic.yml` |
| `Cert mTLS nao corresponde ao registrado` | Agent rotacionou cert mas DB ainda tem o antigo | Verificar `cert_serial` na tabela `executors` |
| `Cert mTLS revogado` | Serial está na blacklist Redis | `redis-cli DEL agent_cert_revoked:<serial>` se foi engano |
| `Cert mTLS expirado` | Cert do executor passou de `cert_expires_at` | Agent precisa renovar via `/executores/renew-cert` ou re-enrollar |
| `revogado com a sessão aberta` (executor fecha com 4403) | Executor ou cert revogado; a conferência periódica da sessão derrubou a conexão | Esperado depois de uma revogação. Para voltar: re-enrollar com OTP novo |
| `Renovacao do executor ... descartada` (renovação responde 409) | O executor foi revogado enquanto o step-ca assinava o cert novo | Esperado depois de uma revogação; o cert novo foi para a blacklist. Para voltar: re-enrollar |
| Renovação responde 429 | Limite de 6 por hora ou 30 por dia por executor | O executor tenta de novo na hora seguinte; persistindo, investigar o que está renovando em laço |
| `<AGENTS_HOST>` responde com o cert do CDN | O host está atrás do CDN (na Cloudflare, *proxied*) | Tirar do CDN (na Cloudflare, DNS-only) |

### API 500 ao subir

```bash
docker compose --profile prod logs api-prod --tail 50
```

Causas comuns:
- **Schema não migrado** — o startup **não** roda migrations (ver
  [Migrations](#migrations-passo-manual), em Atualizar a instalação). Se a API sobe mas
  falha em queries (`relation "..." does not exist`), rode
  `docker compose exec api-prod alembic upgrade head`. Se o próprio
  `alembic upgrade head` falha, conferir `DATABASE_URL` e logs do Postgres.
- `psycopg2.errors.UndefinedObject: extension "postgis" does not exist` —
  rodar `CREATE EXTENSION postgis;` e `uuid-ossp` no banco.
- `STEPCA_PROVISIONER_PASSWORD` errada — o valor é gravado por
  [bootstrap.sh](../scripts/bootstrap.sh) e deve casar com
  `secrets/stepca_password.txt`;
  para rotação, ver
  [Rotacionar senha do provisioner step-ca](#rotacionar-senha-do-provisioner-step-ca).

### Traefik retorna 404

```bash
docker compose --profile prod logs traefik --tail 50
```

| Path | Esperado | Se 404 |
|---|---|---|
| `https://<PUBLIC_HOST>/` | web-prod (Next.js) | Verificar label `traefik.http.routers.web-prod` |
| `https://<PUBLIC_HOST>/ws/*` | api-prod | Verificar router `api-ws-ui` |
| `https://<PUBLIC_HOST>/mcp` | api-prod (401/405 JSON) | **HTML do Next.js** = o router `api-mcp` foi descartado; ver [Configuração dinâmica do Traefik](#configuração-dinâmica-do-traefik) |
| `https://<AGENTS_HOST>/ws/executores/*` | api-prod | Confirmar que o host não está atrás do CDN (um CDN quebra o mTLS) |

### MinIO bucket não existe

```bash
# As variáveis são as do container (o compose as passa ao MinIO), por isso o sh -c
docker compose exec minio sh -c 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"'
docker compose exec minio mc mb local/atlans-drive   # o MINIO_BUCKET do .env (atlans-drive por padrão)
```

O bucket é criado automaticamente pela API no primeiro upload, mas se
você quer pré-criar, é assim.
