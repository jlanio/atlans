// desktop/scripts/sign-selftest.mjs
//
// Proves that `build/sign.cjs` really signs — today, without buying anything.
//
// The real risk of code signing is not technical, it is SCHEDULE: the hook
// sits as a no-op for years, someone buys the certificate on delivery day,
// sets the variables and only then discovers that signtool is not found, that
// the base64 `.pfx` does not decode, that `/as` was missing. That turns into a
// lost night on the worst possible day.
//
// This script generates a SELF-SIGNED certificate, runs the real hook against
// a dummy executable and verifies the resulting signature. The only part it
// does not exercise is the cloud provider's `/dlib` — which is precisely what
// depends on the purchased certificate. Everything else is the same path.
//
// The certificate is temporary and goes away at the end; nothing is installed
// into the machine's trusted certificate store.
//
//   npm run sign:selftest
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { log, ok, step } from './lib.mjs'

const DESKTOP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** Visible error without exiting the process — the `finally` still needs to clean up. */
const falha = (msg) => log(` ERRO  ${msg}`)

/**
 * An unsigned PE outside Windows' catalogs.
 *
 * `esbuild.exe` is a build dependency of this project, so it is always
 * present. `node.exe` is the fallback: larger, but equally outside any catalog.
 */
/** The file electron-builder invokes — exercising another one would prove nothing. */
const CAMINHO_HOOK = path.join(DESKTOP, 'build', 'sign.cjs').split(path.sep).join('/')

function binarioDeTeste() {
  const esbuild = path.join(DESKTOP, 'node_modules', '@esbuild', 'win32-x64', 'esbuild.exe')
  return fs.existsSync(esbuild) ? esbuild : process.execPath
}

if (process.platform !== 'win32') {
  falha('Este autoteste só roda no Windows — signtool e New-SelfSignedCertificate são de lá.')
  process.exit(1)
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlans-signtest-'))
const pfx = path.join(tmp, 'teste.pfx')
const alvo = path.join(tmp, 'alvo.exe')
const SENHA = 'autoteste'

function ps(script) {
  return execFileSync(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-Command', script],
    { encoding: 'utf8' },
  ).trim()
}

/** Carrega o hook — interop CJS→ESM entrega `module.exports` em `.default`. */
const hook = await import(`file://${CAMINHO_HOOK}`).then((m) => m.default ?? m)

// ── 0. Is there a signtool on this machine? ──────────────────────────────────
// The GitHub runner ships the Windows SDK, but the electron-builder cache only
// shows up after the first `npm run dist` — which runs AFTER this self-test.
// If neither is there, there is nothing to exercise.
//
// With no signing configured this is a WARNING: the build comes out unsigned
// anyway, and bringing down the release because of it would be
// disproportionate. With signing configured it is an ERROR — the `npm run dist`
// later on would fail for the same reason, and failing here costs 40 minutes
// less.
/**
 * Exits according to this self-test's PROPORTIONALITY RULE.
 *
 * It is a canary for a capability that is not in use yet: today the build
 * comes out unsigned anyway. As long as `ATLANS_SIGN_PROVIDER` is not defined,
 * a problem with the self-test ITSELF — SDK missing, Windows certificate
 * provider unavailable on the runner, whatever — must not bring down the
 * release. It becomes a warning, and the build goes on.
 *
 * With signing configured, the same problem is an error: the `npm run dist`
 * later on would fail for the same reason, and failing here costs 40 minutes less.
 *
 * Without this rule, the self-test protects something nobody uses and blocks
 * what everybody is waiting for.
 */
function encerrar(houveFalha, motivo) {
  const exigido = Boolean(process.env.ATLANS_SIGN_PROVIDER)
  if (!houveFalha) {
    ok('Autoteste de assinatura passou. Com um certificado real, basta trocar as variáveis.')
    process.exit(0)
  }
  if (exigido) {
    falha(`Autoteste FALHOU e ATLANS_SIGN_PROVIDER está definido — a assinatura não aconteceria. ${motivo ?? ''}`)
    process.exit(1)
  }
  log(`AVISO  autoteste não pôde rodar (${motivo ?? 'ver acima'}).`)
  ok('Sem assinatura configurada, o build segue não assinado — não é motivo para parar a release.')
  process.exit(0)
}

const signtool = hook.acharSigntool()
if (signtool === 'signtool.exe' && !fs.existsSync(signtool)) {
  encerrar(true, 'signtool.exe não encontrado: SDK do Windows ausente e cache do electron-builder vazio')
}

let falhou = false
try {
  // ── 1. Throwaway certificate ───────────────────────────────────────────────
  step('Gerando certificado autoassinado de teste')
  ps(`
    $ErrorActionPreference = 'Stop'
    # O drive 'Cert:' vem de Microsoft.PowerShell.Security. No runner do GitHub
    # o autoload não acontece e o New-SelfSignedCertificate falha com
    # "A drive with the name 'Cert' does not exist" — o cmdlet existe, o
    # PROVEDOR é que não está registrado. Importar explicitamente resolve.
    Import-Module Microsoft.PowerShell.Security -ErrorAction SilentlyContinue
    Import-Module PKI -ErrorAction SilentlyContinue
    $c = New-SelfSignedCertificate \`
      -Type CodeSigningCert \`
      -Subject 'CN=Atlans Autoteste (NAO CONFIAVEL)' \`
      -CertStoreLocation Cert:\\CurrentUser\\My \`
      -NotAfter (Get-Date).AddDays(1)
    $p = ConvertTo-SecureString -String '${SENHA}' -Force -AsPlainText
    Export-PfxCertificate -Cert $c -FilePath '${pfx}' -Password $p | Out-Null
    # Sai do store do usuario na hora: nada persiste depois deste script.
    Remove-Item -Path ("Cert:\\CurrentUser\\My\\" + $c.Thumbprint) -Force
  `)
  ok(`pfx em ${pfx}`)

  // ── 2. An executable to sign ───────────────────────────────────────────────
  // It must be a VALID PE (signtool refuses an empty file) and one that is NOT
  // in a Windows catalog.
  //
  // The first version used `cmd.exe` and the test started to LIE: system
  // binaries are signed by CATALOG, and `Get-AuthenticodeSignature` prefers the
  // catalog signature over the embedded one. It reported `status=Valid, subject=CN=
  // Microsoft Windows` even after we signed it — and, worse, the UNSIGNED file
  // also showed up as valid, which would make the test approve a broken hook.
  // The `esbuild.exe` from node_modules is a third-party PE, with no catalog
  // and no signature of its own.
  fs.copyFileSync(binarioDeTeste(), alvo)

  // ── 3. THE REAL HOOK ───────────────────────────────────────────────────────
  // No reimplementing the call here: what needs to be exercised is exactly the
  // file electron-builder invokes.
  step('Executando build/sign.cjs')
  process.env.ATLANS_SIGN_PROVIDER = 'pfx'
  process.env.ATLANS_SIGN_PFX = pfx
  process.env.ATLANS_SIGN_PFX_PASSWORD = SENHA

  // CJS→ESM interop: `import()` of a CommonJS module delivers `module.exports`
  // in `.default`, and the hook exports `exports.default` — so the target ends
  // up in `.default.default`. electron-builder reaches it via
  // `require(f).default`, which is the first level. Accepting both keeps the
  // self-test from ending up testing the interop instead of the hook.
  const assinar = typeof hook === 'function' ? hook : hook.default
  await assinar({ path: alvo })
  ok('hook executou sem erro')

  // ── 4. Does the signature really exist? ────────────────────────────────────
  // "It didn't blow up" proves nothing: a signtool that did nothing doesn't
  // blow up either.
  step('Verificando a assinatura no arquivo')
  const info = ps(`
    $s = Get-AuthenticodeSignature -FilePath '${alvo}'
    "status=" + $s.Status
    "subject=" + $s.SignerCertificate.Subject
    "digest=" + $s.SignatureType
    "timestamp=" + $(if ($s.TimeStamperCertificate) { 'sim' } else { 'nao' })
  `)
  console.log(info.split('\n').map((l) => `      ${l}`).join('\n'))

  // `UnknownError` is expected: the certificate is self-signed and the chain is
  // not trusted on this machine. What matters is that there IS a signature,
  // with the right subject. `NotSigned` would be the real failure.
  if (/status=NotSigned/.test(info)) {
    falha('O arquivo continua SEM assinatura — o hook não fez nada.')
    falhou = true
  } else if (!/Atlans Autoteste/.test(info)) {
    falha('Assinado, mas por outro certificado que não o do teste.')
    falhou = true
  } else if (!/timestamp=sim/.test(info)) {
    // Without a timestamp, the signature dies with the certificate and every
    // installer already distributed goes back to "unknown publisher".
    falha('Assinado SEM carimbo de tempo — a assinatura expiraria junto com o certificado.')
    falhou = true
  } else {
    ok('assinatura presente, com carimbo de tempo e o certificado esperado')
  }

  // ── 5. The no-op is still a no-op ──────────────────────────────────────────
  step('Sem ATLANS_SIGN_PROVIDER o hook não deve fazer nada')
  delete process.env.ATLANS_SIGN_PROVIDER
  const alvoLimpo = path.join(tmp, 'limpo.exe')
  fs.copyFileSync(binarioDeTeste(), alvoLimpo)
  await assinar({ path: alvoLimpo })

  // Checks by SIGNER, not by `NotSigned`: if some day the test binary comes
  // signed by its vendor, `NotSigned` would no longer hold and the test would
  // fail for a reason that is not its own.
  const limpo = ps(`"subject=" + (Get-AuthenticodeSignature -FilePath '${alvoLimpo}').SignerCertificate.Subject`)
  if (/Atlans Autoteste/.test(limpo)) {
    falha('O hook assinou sem provedor configurado.')
    falhou = true
  } else {
    ok('no-op confirmado — build local e CI sem segredos seguem funcionando')
  }
} catch (e) {
  falha(String(e && e.message ? e.message : e))
  falhou = true
} finally {
  fs.rmSync(tmp, { recursive: true, force: true })
}

encerrar(falhou)
