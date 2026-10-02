# Atlans Executor Desktop

Desktop app of the executor for **Windows x64**: it bundles the Python executor, the
`flow/` engine and a full CPython runtime into a single installer — no Docker, no Git,
no Python installed on the user's machine.

The installer, however, is only half of the app. The **main window** is not a local UI:
it loads the installation's remote web interface in an isolated `BrowserWindow`, giving
the executor — which runs in the background — the look of a standalone piece of software.
Practical consequence: **changes to the web frontend ship through the site without rebuilding
the desktop app**; only changes to the bundled payloads (`flow/`/`executor/`) require a
new installer.

- **Electron entry:** `dist/main/index.cjs` (main process; see `package.json`).
- **Web window:** `src/main/ui/janela-web.ts` loads `UI_URL` (`src/shared/ui.ts`,
  baked into the executable by the build) in an isolated, persistent session
  (`partition: 'persist:atlans'`, `sandbox: true`, `nodeIntegration: false`) — the
  login (same-origin NextAuth cookie) survives restarts. Override only in
  development, via `ATLANS_UI_URL`.
- **Enrollment:** through an `atlans://` deep link (registered by NSIS at install time),
  not by copy-pasting an API key.
- **Local panel + tray:** a second window (`src/renderer/`) shows the executor's state,
  logs and settings; the app lives in the system tray and updates itself
  via `electron-updater`.

## Building the installer

The app bakes the server and the UI of ONE installation into the executable, and the code ships
none: both come from the build environment, which fails without them
(`scripts/enderecos.mjs`). Switching servers requires another build — on purpose
(see `src/shared/servidor.ts`).

```bash
cd desktop
npm run runtime      # once: downloads and assembles resources/python (~390 MB)
export ATLANS_DESKTOP_SERVIDOR=wss://agents.<seu-dominio>
export ATLANS_DESKTOP_UI_URL=https://<seu-dominio>
export ATLANS_RELEASES_DONO=<dono>     # the GitHub repository whose releases
export ATLANS_RELEASES_REPO=<repo>     # carry the app's updates
npm run dist         # produces dist-installer/Atlans Executor Setup <versão>.exe
```

In CI (`.github/workflows/desktop-windows.yml`), the server and the UI come from the
repository variables of the same name (*Settings → Secrets and variables →
Actions → Variables*), and the update feed is the repository itself. In
`npm run dev`, without them, the local API and web apply.

`npm run empacotar` on its own packages whatever is in `dist/`, and only accepts
what came out of `npm run build`: after an `npm run dev`, `dist/main` points
to the local machine, and packaging stops and asks for the build.

Output: a **~182 MB** installer, ~708 MB installed. Alongside it go the `.blockmap`
(differential download) and `latest.yml` (auto-update) — without those two there are no
updates.

`desktop/.npmrc` turns on `ignore-scripts`: no package runs code on
`npm install`/`npm ci` (the door npm worms come through). `electron` does not need a
script: since version 44, it downloads its own binary the first time it is called,
checking the SHA-256 against the package's `checksums.json`. `npm run dev` does that
download as a visible step, and `npm run electron:binario` does it by hand.
`npm run dist` does not depend on this: electron-builder downloads Electron on its
own.

> **Before the first `npm run dist`, turn on Windows Developer Mode**
> (Settings → System → For developers).
>
> electron-builder downloads a signing tools package that contains
> **macOS symlinks** (`libcrypto.dylib`, `libssl.dylib`). Creating a symlink on
> Windows requires privileges, and without them the extraction fails with
> `Cannot create symbolic link` — the build does not even get to packaging. The files in
> question belong to another operating system and are not used here; it is the extraction
> that does not know how to skip them.
>
> Without Developer Mode, the workaround is
> `npx electron-builder --win --x64 --config.win.signAndEditExecutable=false`,
> which skips the whole step. **It costs the `.exe`'s icon and metadata**, so it
> is good for validating the packaging, not for producing a release.

---

## Why it exists

The only installation path on Windows today is manual: [`static/install.sh`](../static/install.sh)
is pure bash (it requires Git Bash or WSL) and the UI at `/executores` generates PowerShell commands
that assume Docker Desktop and a cloned repository. For someone who just wants to run
workflows on their own machine, that is a barrier.

There used to be an `agent-desktop/` in this repository (removed). It
rotted for two reasons that this project avoids by construction:

- it derived status by **parsing log lines** with regexes — exactly what the
  docstring of [`executor/stats.py`](../executor/stats.py) forbids;
- it spoke the `AGENT_API_KEY` protocol, abandoned when the executor moved to
  mTLS with OTP-based enrollment.

The replacement is a structured event channel (NDJSON) fed by the same
`Snapshot` that the `rich` panel already consumes.

---

## Python runtime pipeline

```bash
cd desktop
npm run python:fetch     # downloads and verifies the standalone CPython
npm run python:build     # pip install + pruning + precompilation
npm run payload:stage    # copies executor/ and flow/
npm run python:smoke     # validates the bundle
```

or `npm run runtime` for all four in sequence. No script has an npm
dependency — everything uses the Node 20 stdlib and Windows' own `tar`.

| Script | What it does |
|---|---|
| `scripts/fetch-python.mjs` | Downloads the asset described in `python-runtime.json`, **checks the SHA-256** and extracts it. Idempotent — that is what makes the CI cache useful. |
| `scripts/build-python-runtime.mjs` | `pip install --require-hashes` from the executor's lock ([`executor/requirements-full.txt`](../executor/requirements-full.txt)), pruning measured step by step, `compileall`, and writes `resources/payload.json`. |
| `scripts/check-lock.mjs` | `npm run python:lock:check` (runs in CI): installs the executor's lock into a clean Windows CPython, with hashes and wheels only, and runs `pip check`. |
| `scripts/payload-stage.mjs` | Copies `executor/` and `flow/` in deterministic order, excluding `.env`, `certs/` and `__pycache__`. |
| `scripts/smoke-python.mjs` + `smoke.py` | 12 steps that prove the bundle imports and works. |

### Three decisions that are not obvious

**No venv.** The dependencies are installed directly into the interpreter. A venv writes
`home = <caminho do build agent>` into `pyvenv.cfg` and embeds the same path in the `.exe` files
in `Scripts/` — none of that exists on the user's machine. Installing directly makes the
tree relocatable by construction, with no "first run" step (the old app's `conda-unpack`
extracted ~600 MB on first boot).

**No conda.** All 65 dependencies have a `win_amd64`/`cp312` wheel on PyPI,
including the GDAL stack. `--only-binary=:all:` guarantees that the build goes **red**
if any of them loses its wheel, instead of a runner trying to compile GDAL.

**`flow/` is a sibling of `executor/`.** [`job_executor.py`](../executor/job_executor.py)
inserts the parent directory into `sys.path` to import `flow.executor`. Hence the
mandatory layout, with `cwd` and `PYTHONPATH` pointing to `resources/`:

```
resources/
├── python/     interpreter + site-packages
├── executor/   copy of ../executor
└── flow/       copy of ../flow
```

### Size (measured, not estimated)

```
119 MB clean runtime  →  453 MB after pip  →  353 MB pruned  →  392 MB with .pyc
```

Pruning cuts 100 MB: GUI/test stdlib, the packages' test suites, headers and sources,
`pip`/`setuptools`, and `botocore/data` except `s3` and `sts`. `compileall` adds back
39 MB in `.pyc` — and it is worth it: without it every boot recompiles pandas and geopandas, and the `.pyc` files
generated at runtime would be left orphaned after uninstalling. Compressed, the payload comes
to ~83 MB.

The numbers for each step are written to `resources/payload.json` on every build.

---

## Versions

`python-runtime.json` pins CPython by **release and SHA-256** — without the hash, a
republished release would swap the interpreter without anyone noticing. Python 3.12 is not a
free choice: it aligns with [`Dockerfile.executor`](../Dockerfile.executor), with
[`Dockerfile.api`](../Dockerfile.api) and with the CI's `setup-python`. Changing the version
requires regenerating the Python locks (`python scripts/travar_python.py`), because wheels
are per CPython version (`cp312`).

The dependencies come from the **executor's lock**,
[`executor/requirements-full.txt`](../executor/requirements-full.txt): the same
versions and the same files as the Docker executor, and the build installs with
`--require-hashes`. There is no desktop-specific lock. There used to be one, a copy of the
executor's lock, regenerated on Windows on every change; Dependabot saw it as a standalone file and
bumped the transitive dependencies only in it, leaving the image behind. To change a version,
edit `executor/requirements-full.in` and regenerate the locks (`python scripts/travar_python.py`,
see CONTRIBUTING, "Python dependencies").

The lock is resolved on Linux. CI proves that it works for Windows with
`npm run python:lock:check`: it installs the lock into a clean Windows CPython, with
`--require-hashes` and `--only-binary=:all:`, and runs `pip check`. A wheel missing
for `win_amd64`, or a dependency that only Windows asks for, breaks there, and not in the
installer build.

This is not ceremony: before the lock, `requirements-full.txt` used loose pins and
resolved geopandas **1.1.4** while the root `requirements.txt` pinned **1.1.3** —
the Docker executor and the desktop one would run different libraries, and the bug that only
shows up in one of the two is the most expensive one to find.

---

## Where the user's data lives

Nothing is written to the installation directory. The app points the variables that
[`config.py`](../executor/config.py) already exposes to the user's profile:

| Path | Variable |
|---|---|
| `%APPDATA%\AtlansExecutor\config\.env` | `EXECUTOR_ENV_PATH` |
| `%APPDATA%\AtlansExecutor\certs\` | `EXECUTOR_CERT_DIR` |
| `%APPDATA%\AtlansExecutor\logs\` | `EXECUTOR_LOG_DIR` |
| `%USERPROFILE%\AtlansExecutor\artifacts\` | `EXECUTOR_ARTIFACTS_DIR` |

The spawn also **removes** `GDAL_DATA`, `PROJ_LIB`, `PROJ_DATA`, `PYTHONHOME` and
`PYTHONPATH` from the inherited environment. On a machine with QGIS or ArcGIS installed, those
variables point to that installation's data and the bundle's pyogrio/pyproj
would load incompatible projection tables — a `to_crs()` that returns a wrong
coordinate instead of blowing up.

---

## Troubleshooting

**`SHA-256 nao confere`** (SHA-256 does not match) — the python-build-standalone release changed. If it was
intentional, update `release`, `asset` and `sha256` in `python-runtime.json` in the same
PR.

**`In --require-hashes mode, all requirements must have their versions pinned`** in
`python:lock:check` — Windows asks for a dependency that the executor's lock (resolved
on Linux) does not have. If it is pure Python, add it with an exact version to
`executor/requirements-full.in` and regenerate the locks: it goes into the lock and, on Linux, is just
installed needlessly (`requirements-dev.in` brings in `colorama` for the same reason).
If it only exists for Windows (a `pywin32`), the Linux lock cannot bring it in
— with a `sys_platform` marker, pip-compile drops it — and the desktop app once again
needs its own lock. Today there is no such dependency.

**`Could not find a version that satisfies the requirement`** in `python:lock:check` —
a version in the lock has no `win_amd64` wheel for `cp312`. Pick, in the `.in`, a
version that has one.

**`falha ao extrair … com tar`** (failed to extract … with tar) — Git Bash's GNU tar reads `C:\...` as
`host:caminho` (host:path). The scripts already resolve System32's `tar.exe` by absolute path;
if the error comes back, it is because `%SystemRoot%` is not defined.

**Smoke fails at step 4 (registry)** — pruning removed something a node needs, or
a new node imports a dependency that is not in `requirements-full.in`.

**The installed app opens and closes immediately, with no error at all** — check
`ELECTRON_RUN_AS_NODE`:

```powershell
$env:ELECTRON_RUN_AS_NODE     # if it returns 1, that's it
```

With that variable set, the Electron executable becomes **plain Node**: there is no
`electron` module, there is no window, and the process dies with
`Cannot find module 'electron'` on a stderr nobody sees, because the app is a GUI.
The symptom is indistinguishable from "the app did not install".

Some build tools and editor extensions set this variable in the
environment and it is inherited by everything launched from there. Open the app from a
clean terminal, or remove the variable first.

**Two instances** — the app uses `requestSingleInstanceLock()`. An open `npm run dev`
holds the same lock as the installed app (same `app.setName`), and the second
instance exits silently, with code 0. Close the dev instance before testing the
packaged one.
