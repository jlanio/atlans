# Atlans Executor Desktop

App desktop do executor para **Windows x64**: empacota o executor Python, o motor
`flow/` e um runtime CPython completo num instalador único — sem Docker, sem Git,
sem Python instalado na máquina do usuário.

O instalador, porém, é só metade do app. A **janela principal** não é uma UI local:
ela carrega a interface web remota da instalação num `BrowserWindow` isolado, dando
ao executor — que roda em segundo plano — a cara de um software próprio.
Consequência prática: **mudanças no frontend web saem pelo site sem rebuild do
desktop**; só alterações nos payloads embarcados (`flow/`/`executor/`) exigem um
instalador novo.

- **Entry do Electron:** `dist/main/index.cjs` (processo main; ver `package.json`).
- **Janela web:** `src/main/ui/janela-web.ts` carrega `UI_URL` (`src/shared/ui.ts`,
  fixo no executável pelo build) em sessão isolada e persistente
  (`partition: 'persist:atlans'`, `sandbox: true`, `nodeIntegration: false`) — o
  login (cookie NextAuth same-origin) sobrevive a reinícios. Override apenas em
  desenvolvimento, via `ATLANS_UI_URL`.
- **Enrollment:** por deep link `atlans://` (registrado pelo NSIS na instalação),
  não por copiar-colar de chave de API.
- **Painel local + bandeja:** uma segunda janela (`src/renderer/`) mostra estado,
  logs e ajustes do executor; o app vive na bandeja (tray) e se atualiza sozinho
  via `electron-updater`.

## Gerar o instalador

O app grava no executável o servidor e a UI de UMA instalação, e o código não traz
nenhum: os dois vêm do ambiente do build, que falha sem eles
(`scripts/enderecos.mjs`). Trocar de servidor exige outro build — de propósito
(ver `src/shared/servidor.ts`).

```bash
cd desktop
npm run runtime      # uma vez: baixa e monta resources/python (~390 MB)
export ATLANS_DESKTOP_SERVIDOR=wss://agents.<seu-dominio>
export ATLANS_DESKTOP_UI_URL=https://<seu-dominio>
export ATLANS_RELEASES_DONO=<dono>     # o repositório do GitHub cujas releases
export ATLANS_RELEASES_REPO=<repo>     # trazem as atualizações do app
npm run dist         # gera dist-installer/Atlans Executor Setup <versão>.exe
```

No CI (`.github/workflows/desktop-windows.yml`), o servidor e a UI vêm das
variáveis do repositório de mesmo nome (*Settings → Secrets and variables →
Actions → Variables*), e o feed de atualização é o próprio repositório. Em
`npm run dev`, sem eles, valem a API e o web locais.

`npm run empacotar` sozinho empacota o que estiver em `dist/`, e só aceita o
que saiu de `npm run build`: depois de um `npm run dev`, o `dist/main` aponta
para a máquina local, e o empacotamento para pedindo o build.

Saída: **~182 MB** de instalador, ~708 MB instalados. Junto vão o `.blockmap`
(download diferencial) e o `latest.yml` (auto-update) — sem esses dois não há
atualização.

O `desktop/.npmrc` liga `ignore-scripts`: nenhum pacote roda código no
`npm install`/`npm ci` (a porta dos worms do npm). O `electron` não precisa de
script: desde o 44, ele baixa o próprio binário na primeira vez que é chamado,
conferindo o SHA-256 pelo `checksums.json` do pacote. O `npm run dev` faz esse
download num passo à vista, e `npm run electron:binario` faz à mão. O
`npm run dist` não depende disso: o electron-builder baixa o Electron por conta
própria.

> **Antes do primeiro `npm run dist`, ative o Modo de Desenvolvedor do Windows**
> (Configurações → Sistema → Para desenvolvedores).
>
> O electron-builder baixa um pacote de ferramentas de assinatura que contém
> **symlinks do macOS** (`libcrypto.dylib`, `libssl.dylib`). Criar symlink no
> Windows exige privilégio, e sem ele a extração falha com
> `Cannot create symbolic link` — o build nem chega a empacotar. Os arquivos em
> questão são de outro sistema operacional e não são usados aqui; é a extração
> que não sabe pulá-los.
>
> Sem o Modo de Desenvolvedor, o contorno é
> `npx electron-builder --win --x64 --config.win.signAndEditExecutable=false`,
> que pula a etapa inteira. **Custa o ícone e os metadados do `.exe`**, então
> serve para validar o empacotamento, não para gerar uma release.

---

## Por que existe

O único caminho de instalação no Windows hoje é manual: [`static/install.sh`](../static/install.sh)
é bash puro (exige Git Bash ou WSL) e a UI em `/executores` gera comandos PowerShell
que pressupõem Docker Desktop e o repositório clonado. Para quem só quer rodar
workflows na própria máquina, isso é uma barreira.

Já existiu um `agent-desktop/` neste repositório (removido). Ele
apodreceu por dois motivos que este projeto evita por construção:

- derivava status **parseando linhas de log** por regex — exatamente o que o
  docstring de [`executor/stats.py`](../executor/stats.py) proíbe;
- falava o protocolo `AGENT_API_KEY`, abandonado quando o executor migrou para
  mTLS com enrollment por OTP.

A substituição é um canal de eventos estruturados (NDJSON) alimentado pelo mesmo
`Snapshot` que o painel `rich` já consome.

---

## Pipeline do runtime Python

```bash
cd desktop
npm run python:fetch     # baixa e verifica o CPython standalone
npm run python:build     # pip install + poda + pré-compilação
npm run payload:stage    # copia executor/ e flow/
npm run python:smoke     # valida o bundle
```

ou `npm run runtime` para os quatro em sequência. Nenhum script tem dependência de
npm — tudo usa stdlib do Node 20 e o `tar` do próprio Windows.

| Script | O que faz |
|---|---|
| `scripts/fetch-python.mjs` | Baixa o asset descrito em `python-runtime.json`, **confere o SHA-256** e extrai. Idempotente — é o que torna o cache do CI útil. |
| `scripts/build-python-runtime.mjs` | `pip install --require-hashes` do lock do executor ([`executor/requirements-full.txt`](../executor/requirements-full.txt)), poda medida passo a passo, `compileall`, e escreve `resources/payload.json`. |
| `scripts/check-lock.mjs` | `npm run python:lock:check` (roda no CI): instala o lock do executor num CPython do Windows limpo, com hash e só wheel, e roda o `pip check`. |
| `scripts/payload-stage.mjs` | Copia `executor/` e `flow/` em ordem determinística, excluindo `.env`, `certs/` e `__pycache__`. |
| `scripts/smoke-python.mjs` + `smoke.py` | 12 passos que provam que o bundle importa e opera. |

### Três decisões que não são óbvias

**Sem venv.** As dependências são instaladas direto no interpretador. Um venv grava
`home = <caminho do build agent>` em `pyvenv.cfg` e embute o mesmo caminho nos `.exe`
de `Scripts/` — nada disso existe na máquina do usuário. Instalar direto torna a
árvore relocável por construção, sem passo de "primeira execução" (o `conda-unpack`
do app antigo extraía ~600 MB no primeiro boot).

**Sem conda.** Todas as 65 dependências têm wheel `win_amd64`/`cp312` no PyPI,
incluindo o stack GDAL. `--only-binary=:all:` garante que o build fica **vermelho**
se alguma perder a wheel, em vez de um runner tentar compilar GDAL.

**`flow/` é irmão de `executor/`.** [`job_executor.py`](../executor/job_executor.py)
insere o diretório-pai no `sys.path` para importar `flow.executor`. Daí o layout
obrigatório, com `cwd` e `PYTHONPATH` apontando para `resources/`:

```
resources/
├── python/     interpretador + site-packages
├── executor/   cópia de ../executor
└── flow/       cópia de ../flow
```

### Tamanho (medido, não estimado)

```
119 MB runtime limpo  →  453 MB após pip  →  353 MB podado  →  392 MB com .pyc
```

A poda corta 100 MB: stdlib GUI/test, suites de teste dos pacotes, headers e fontes,
`pip`/`setuptools`, e `botocore/data` exceto `s3` e `sts`. O `compileall` devolve
39 MB em `.pyc` — e vale: sem ele cada boot recompila pandas e geopandas, e os `.pyc`
gerados em runtime ficariam órfãos após a desinstalação. Comprimido, o payload fica
em ~83 MB.

Os números de cada passo ficam em `resources/payload.json` a cada build.

---

## Versões

`python-runtime.json` pina o CPython por **release e SHA-256** — sem o hash, uma
release republicada trocaria o interpretador sem ninguém notar. Python 3.12 não é
escolha livre: alinha com [`Dockerfile.executor`](../Dockerfile.executor), com o
[`Dockerfile.api`](../Dockerfile.api) e com o `setup-python` do CI. Trocar a versão
exige regerar os locks Python (`python scripts/travar_python.py`), porque as wheels
são por versão do CPython (`cp312`).

As dependências vêm do **lock do executor**,
[`executor/requirements-full.txt`](../executor/requirements-full.txt): as mesmas
versões e os mesmos arquivos do executor do Docker, e o build instala com
`--require-hashes`. Não há lock próprio do desktop. Havia um, cópia do lock do
executor, regerada no Windows a cada mudança; o Dependabot o via como arquivo solto e
subia as transitivas só nele, deixando a imagem para trás. Para mudar uma versão,
edite `executor/requirements-full.in` e regere os locks (`python scripts/travar_python.py`,
ver CONTRIBUTING, "Dependências Python").

O lock é resolvido no Linux. O CI prova que ele serve ao Windows com
`npm run python:lock:check`: instala o lock num CPython do Windows limpo, com
`--require-hashes` e `--only-binary=:all:`, e roda o `pip check`. Uma wheel que falte
para `win_amd64`, ou uma dependência que só o Windows pede, quebra ali, e não no build
do instalador.

Isso não é cerimônia: antes do lock, `requirements-full.txt` usava pins soltos e
resolvia geopandas **1.1.4** enquanto o `requirements.txt` da raiz pinava **1.1.3** —
o executor do Docker e o do desktop rodariam bibliotecas diferentes, e o bug que só
aparece num dos dois é o mais caro de achar.

---

## Onde ficam os dados do usuário

Nada é gravado no diretório de instalação. O app aponta as variáveis que o
[`config.py`](../executor/config.py) já expõe para o perfil do usuário:

| Caminho | Variável |
|---|---|
| `%APPDATA%\AtlansExecutor\config\.env` | `EXECUTOR_ENV_PATH` |
| `%APPDATA%\AtlansExecutor\certs\` | `EXECUTOR_CERT_DIR` |
| `%APPDATA%\AtlansExecutor\logs\` | `EXECUTOR_LOG_DIR` |
| `%USERPROFILE%\AtlansExecutor\artifacts\` | `EXECUTOR_ARTIFACTS_DIR` |

O spawn também **remove** `GDAL_DATA`, `PROJ_LIB`, `PROJ_DATA`, `PYTHONHOME` e
`PYTHONPATH` do ambiente herdado. Numa máquina com QGIS ou ArcGIS instalado, essas
variáveis apontam para os dados daquela instalação e o pyogrio/pyproj do bundle
carregaria tabelas de projeção incompatíveis — um `to_crs()` que devolve coordenada
errada em vez de estourar.

---

## Solução de problemas

**`SHA-256 nao confere`** — a release do python-build-standalone mudou. Se foi
intencional, atualize `release`, `asset` e `sha256` em `python-runtime.json` no mesmo
PR.

**`In --require-hashes mode, all requirements must have their versions pinned`** no
`python:lock:check` — o Windows pede uma dependência que o lock do executor (resolvido
no Linux) não tem. Se ela é Python puro, acrescente-a com versão exata ao
`executor/requirements-full.in` e regere os locks: ela entra no lock e, no Linux, só
fica instalada à toa (o `requirements-dev.in` traz o `colorama` pelo mesmo motivo).
Se ela só existe para Windows (um `pywin32`), o lock do Linux não consegue trazê-la
— com marcador `sys_platform`, o pip-compile a descarta — e o desktop volta a
precisar de um lock próprio. Hoje não há nenhuma assim.

**`Could not find a version that satisfies the requirement`** no `python:lock:check` —
uma versão do lock não tem wheel `win_amd64` para o `cp312`. Escolha, no `.in`, uma
versão que tenha.

**`falha ao extrair … com tar`** — o GNU tar do Git Bash lê `C:\...` como
`host:caminho`. Os scripts já resolvem o `tar.exe` do System32 por caminho absoluto;
se o erro voltar, é porque `%SystemRoot%` não está definido.

**Smoke falha no passo 4 (registry)** — a poda removeu algo de que um nó precisa, ou
um nó novo importa uma dependência que não está no `requirements-full.in`.

**O app instalado abre e fecha na hora, sem erro nenhum** — verifique
`ELECTRON_RUN_AS_NODE`:

```powershell
$env:ELECTRON_RUN_AS_NODE     # se devolver 1, é isso
```

Com essa variável definida, o executável do Electron vira **Node puro**: não há
módulo `electron`, não há janela, e o processo morre com
`Cannot find module 'electron'` num stderr que ninguém vê, porque o app é GUI.
O sintoma é indistinguível de "o app não instalou".

Algumas ferramentas de build e extensões de editor definem essa variável no
ambiente e ela é herdada por tudo que for lançado dali. Abra o app de um
terminal limpo, ou remova a variável antes.

**Duas instâncias** — o app usa `requestSingleInstanceLock()`. Um `npm run dev`
aberto segura o mesmo lock do app instalado (mesmo `app.setName`), e a segunda
instância sai em silêncio, com código 0. Feche o dev antes de testar o
empacotado.
