// desktop/build/sign.cjs
//
// electron-builder code-signing hook.
//
// Without `ATLANS_SIGN_PROVIDER` in the environment it is a no-op and the build
// comes out UNSIGNED — functional, but with SmartScreen showing "Windows
// protected your PC" and the "Run anyway" button hidden behind "More info".
// For an app that spawns `python.exe` and opens an outbound WebSocket,
// corporate antivirus heuristics are also likely.
//
// ── What to choose ───────────────────────────────────────────────────────────
//
// A physical USB token (the OV/EV standard since Jun/2023) is INCOMPATIBLE with
// GitHub runners — nobody plugs a token into an ephemeral runner. The viable
// options:
//
//   Azure Trusted Signing   by far the cheapest (~US$ 10/month), but requires
//                           a legal entity with 3+ years of verifiable
//                           history. Confirm eligibility of a Brazilian
//                           CNPJ BEFORE counting on it.
//   DigiCert KeyLocker      cloud-HSM variant of traditional OV/EV.
//   SSL.com eSigner         same, usually the more affordable of the two.
//
// All three sign via `signtool` — the first two with an interop DLL
// (`/dlib`); a direct `.pfx` only exists for legacy certificates and for the
// local self-test.
//
// **EV is not required for it to work, but it makes a big difference in
// practice:** an OV certificate starts with zero reputation in SmartScreen and
// takes a number of installs before it stops warning; an EV warns zero times
// from day one.
//
// ── How to enable ────────────────────────────────────────────────────────────
//
//   Azure Trusted Signing / DigiCert KeyLocker
//     ATLANS_SIGN_PROVIDER=dlib
//     ATLANS_SIGN_DLIB=C:\ts\bin\x64\Azure.CodeSigning.Dlib.dll
//     ATLANS_SIGN_DLIB_METADATA=C:\ts\metadata.json
//
//   .pfx file (legacy certificate, or the self-test — see npm run sign:selftest)
//     ATLANS_SIGN_PROVIDER=pfx
//     ATLANS_SIGN_PFX=C:\caminho\cert.pfx     (or the content in base64)
//     ATLANS_SIGN_PFX_PASSWORD=…
//
// In CI, the values come from secrets; the job only injects them when they
// exist, so a fork without secrets can still build.
//
// The extension is `.cjs`, not `.js`, because package.json declares
// `"type": "module"`: a `.js` would be loaded as ESM and the `exports.default`
// electron-builder looks for would not exist. The error you get in that case
// is a module resolver stack trace, with no mention of ESM whatsoever.

'use strict'

const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

/**
 * Timestamp. **It is not optional.**
 *
 * Without it the signature dies along with the certificate — in 1 to 3 years
 * every installer already distributed goes back to "unknown publisher",
 * including the ones the customer kept. With the timestamp, the signature
 * stays valid forever for the binaries signed while the certificate was valid.
 */
const TIMESTAMP_URL = process.env.ATLANS_SIGN_TIMESTAMP || 'http://timestamp.digicert.com'

/** How many times to try. The timestamp service is network, and networks fail. */
const TENTATIVAS = 3

/**
 * Finds `signtool.exe`.
 *
 * It is not on the PATH on an ordinary machine, and the Windows SDK is **not**
 * a prerequisite of this project — on this development machine, for example,
 * there are no Windows Kits at all. What always exists is the copy that
 * electron-builder itself downloads in the `winCodeSign` package, and that is
 * the first choice.
 *
 * ⚠️ The `winCodeSign` signtool is old and **does not support `/dlib`**. For
 * Azure Trusted Signing or DigiCert KeyLocker, install the Windows SDK and
 * point `ATLANS_SIGNTOOL` to its binary — `/dlib` is precisely what that
 * signtool does not know, and the error it returns does not mention the version.
 */
exports.acharSigntool = acharSigntool
function acharSigntool() {
  if (process.env.ATLANS_SIGNTOOL) return process.env.ATLANS_SIGNTOOL

  for (const p of builderCacheCandidates()) {
    if (fs.existsSync(p)) return p
  }

  const kits = 'C:\\Program Files (x86)\\Windows Kits\\10\\bin'
  try {
    const versoes = fs.readdirSync(kits)
      .filter((v) => /^10\./.test(v))
      .sort()
      .reverse()
    for (const v of versoes) {
      for (const arch of ['x64', 'x86']) {
        const p = path.join(kits, v, arch, 'signtool.exe')
        if (fs.existsSync(p)) return p
      }
    }
  } catch {
    // Kits not installed — moves on to the PATH.
  }
  return 'signtool.exe'
}

/** `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\<algo>\windows-10\x64`. */
function builderCacheCandidates() {
  const base = process.env.LOCALAPPDATA
  if (!base) return []
  const raiz = path.join(base, 'electron-builder', 'Cache', 'winCodeSign')

  let entradas
  try {
    entradas = fs.readdirSync(raiz)
  } catch {
    return []
  }

  // The literal `winCodeSign` directory is what the current version uses; the
  // numeric ones are caches from earlier versions. Newest first, and the literal
  // one in front.
  const ordenadas = [
    ...entradas.filter((e) => e === 'winCodeSign'),
    ...entradas.filter((e) => e !== 'winCodeSign').sort().reverse(),
  ]
  return ordenadas.flatMap((e) => [
    path.join(raiz, e, 'windows-10', 'x64', 'signtool.exe'),
    path.join(raiz, e, 'windows-10', 'ia32', 'signtool.exe'),
  ])
}

/** Accepts a file path OR the whole .pfx in base64 (what fits in a secret). */
function materializePfx(valor) {
  if (fs.existsSync(valor)) return { arquivo: valor, temporario: false }

  const destino = path.join(os.tmpdir(), `atlans-sign-${process.pid}.pfx`)
  fs.writeFileSync(destino, Buffer.from(valor, 'base64'), { mode: 0o600 })
  return { arquivo: destino, temporario: true }
}

function exigir(nome) {
  const v = process.env[nome]
  if (!v) throw new Error(`${nome} não definida — necessária para ATLANS_SIGN_PROVIDER.`)
  return v
}

function argumentsFor(provedor, tempFiles) {
  if (provedor === 'pfx') {
    const { arquivo, temporario } = materializePfx(exigir('ATLANS_SIGN_PFX'))
    if (temporario) tempFiles.push(arquivo)
    const args = ['/f', arquivo]
    const senha = process.env.ATLANS_SIGN_PFX_PASSWORD
    if (senha) args.push('/p', senha)
    return args
  }

  if (provedor === 'dlib') {
    // Azure Trusted Signing and DigiCert KeyLocker path: the private key never
    // leaves the HSM; the DLL talks to the service.
    return ['/dlib', exigir('ATLANS_SIGN_DLIB'), '/dmdf', exigir('ATLANS_SIGN_DLIB_METADATA')]
  }

  throw new Error(
    `ATLANS_SIGN_PROVIDER='${provedor}' desconhecido. Use 'pfx' ou 'dlib'.`,
  )
}

/**
 * @param {{ path: string, hash?: string, isNest?: boolean }} configuration
 *   `path` is the file to sign — the app's .exe and, afterwards, the installer's.
 */
exports.default = async function sign(configuration) {
  const provedor = process.env.ATLANS_SIGN_PROVIDER
  if (!provedor) {
    // Silent on purpose: the local build and the CI build without secrets are the
    // NORMAL case today. A warning for every signed file would become noise one
    // learns to ignore — and then the day signing really fails goes unnoticed.
    return
  }

  const tempFiles = []
  try {
    const args = [
      'sign',
      // SHA-256 everywhere. SHA-1 is still accepted for old compatibility and is
      // exactly the kind of default that goes unnoticed.
      '/fd', 'sha256',
      '/td', 'sha256',
      '/tr', TIMESTAMP_URL,
      ...argumentsFor(provedor, tempFiles),
      // `isNest` = the file already has a signature and this one is additional.
      // Without `/as`, the second one silently REPLACES the first.
      ...(configuration.isNest ? ['/as'] : []),
      configuration.path,
    ]

    const signtool = acharSigntool()
    let lastError
    for (let i = 1; i <= TENTATIVAS; i++) {
      try {
        execFileSync(signtool, args, { stdio: 'inherit' })
        return
      } catch (erro) {
        lastError = erro
        if (i < TENTATIVAS) {
          console.warn(`[sign] tentativa ${i}/${TENTATIVAS} falhou; repetindo…`)
          // Short, increasing wait: almost every failure here is the timestamp
          // server refusing because of too many requests.
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000 * i)
        }
      }
    }

    throw new Error(
      `Falha ao assinar ${configuration.path} com signtool (${TENTATIVAS} tentativas). ` +
      `Um build que DEVERIA ser assinado e sai sem assinatura é pior que um build ` +
      `que não termina: ele chega ao usuário com o aviso do SmartScreen e ninguém ` +
      `percebe até o primeiro chamado de suporte. Causa: ${lastError && lastError.message}`,
    )
  } finally {
    for (const t of tempFiles) {
      try { fs.unlinkSync(t) } catch { /* already removed */ }
    }
  }
}
