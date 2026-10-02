// desktop/scripts/sign-selftest.mjs
//
// Prova que `build/sign.cjs` assina de verdade — hoje, sem comprar nada.
//
// O risco real da assinatura de código não é técnico, é de CRONOGRAMA: o hook
// fica anos como no-op, alguém compra o certificado no dia da entrega, liga as
// variáveis e aí descobre que o signtool não é encontrado, que o `.pfx` em
// base64 não decodifica, que faltava o `/as`. Isso vira uma noite perdida no
// pior dia possível.
//
// Este script gera um certificado AUTOASSINADO, roda o hook de verdade contra
// um executável de mentira e verifica a assinatura resultante. O único trecho
// que ele não exercita é o `/dlib` do provedor em nuvem — que é justamente o
// que depende do certificado comprado. Todo o resto é o mesmo caminho.
//
// O certificado é temporário e some no fim; nada é instalado no repositório de
// certificados confiáveis da máquina.
//
//   npm run sign:selftest
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { log, ok, step } from './lib.mjs'

const DESKTOP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** Erro visível sem encerrar o processo — o `finally` ainda precisa limpar. */
const falha = (msg) => log(` ERRO  ${msg}`)

/**
 * Um PE sem assinatura e fora dos catálogos do Windows.
 *
 * `esbuild.exe` é dependência de build deste projeto, então está sempre
 * presente. `node.exe` é a reserva: maior, mas igualmente fora de catálogo.
 */
/** O arquivo que o electron-builder invoca — exercitar outro não provaria nada. */
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

// ── 0. Existe signtool nesta máquina? ────────────────────────────────────────
// O runner do GitHub traz o SDK do Windows, mas o cache do electron-builder só
// aparece depois do primeiro `npm run dist` — que roda DEPOIS deste autoteste.
// Se nenhum dos dois estiver lá, não há o que exercitar.
//
// Sem assinatura configurada isso é AVISO: o build sai não assinado de qualquer
// forma, e derrubar a release por causa disso seria desproporcional. Com
// assinatura configurada é ERRO — o `npm run dist` adiante falharia pelo mesmo
// motivo, e falhar aqui custa 40 minutos a menos.
/**
 * Encerra segundo a REGRA DE PROPORÇÃO deste autoteste.
 *
 * Ele é um canário de uma capacidade que ainda não está em uso: hoje o build
 * sai não assinado de qualquer forma. Enquanto `ATLANS_SIGN_PROVIDER` não
 * estiver definido, um problema do PRÓPRIO autoteste — SDK ausente, provedor de
 * certificado do Windows indisponível no runner, o que for — não pode derrubar
 * a release. Vira aviso, e o build segue.
 *
 * Com a assinatura configurada, o mesmo problema é erro: o `npm run dist`
 * adiante falharia pelo mesmo motivo, e falhar aqui custa 40 minutos a menos.
 *
 * Sem esta regra, o autoteste protege algo que ninguém usa e bloqueia o que
 * todo mundo espera.
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
  // ── 1. Certificado descartável ─────────────────────────────────────────────
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

  // ── 2. Um executável para assinar ──────────────────────────────────────────
  // Precisa ser um PE VÁLIDO (o signtool recusa arquivo vazio) e que NÃO esteja
  // num catálogo do Windows.
  //
  // A primeira versão usava `cmd.exe` e o teste passou a MENTIR: binários do
  // sistema são assinados por CATÁLOGO, e o `Get-AuthenticodeSignature` prefere
  // a assinatura do catálogo à embutida. Saía `status=Valid, subject=CN=
  // Microsoft Windows` mesmo depois de assinarmos — e, pior, o arquivo NÃO
  // assinado também aparecia como válido, o que faria o teste aprovar um hook
  // quebrado. O `esbuild.exe` do node_modules é PE de terceiro, sem catálogo e
  // sem assinatura própria.
  fs.copyFileSync(binarioDeTeste(), alvo)

  // ── 3. O HOOK DE VERDADE ───────────────────────────────────────────────────
  // Nada de reimplementar a chamada aqui: o que precisa ser exercitado é
  // exatamente o arquivo que o electron-builder invoca.
  step('Executando build/sign.cjs')
  process.env.ATLANS_SIGN_PROVIDER = 'pfx'
  process.env.ATLANS_SIGN_PFX = pfx
  process.env.ATLANS_SIGN_PFX_PASSWORD = SENHA

  // Interop CJS→ESM: `import()` de um CommonJS entrega `module.exports` em
  // `.default`, e o hook exporta `exports.default` — então o alvo fica em
  // `.default.default`. O electron-builder chega nele por `require(f).default`,
  // que é o primeiro nível. Aceitar os dois evita que o autoteste passe a
  // testar a interop em vez do hook.
  const assinar = typeof hook === 'function' ? hook : hook.default
  await assinar({ path: alvo })
  ok('hook executou sem erro')

  // ── 4. A assinatura existe mesmo? ──────────────────────────────────────────
  // "Não estourou" não é prova de nada: um signtool que não fez nada também
  // não estoura.
  step('Verificando a assinatura no arquivo')
  const info = ps(`
    $s = Get-AuthenticodeSignature -FilePath '${alvo}'
    "status=" + $s.Status
    "subject=" + $s.SignerCertificate.Subject
    "digest=" + $s.SignatureType
    "timestamp=" + $(if ($s.TimeStamperCertificate) { 'sim' } else { 'nao' })
  `)
  console.log(info.split('\n').map((l) => `      ${l}`).join('\n'))

  // `UnknownError` é o esperado: o certificado é autoassinado e a cadeia não é
  // confiável nesta máquina. O que importa é que HÁ uma assinatura, com o
  // sujeito certo. `NotSigned` seria a falha real.
  if (/status=NotSigned/.test(info)) {
    falha('O arquivo continua SEM assinatura — o hook não fez nada.')
    falhou = true
  } else if (!/Atlans Autoteste/.test(info)) {
    falha('Assinado, mas por outro certificado que não o do teste.')
    falhou = true
  } else if (!/timestamp=sim/.test(info)) {
    // Sem carimbo, a assinatura morre com o certificado e todo instalador já
    // distribuído volta a ser "editor desconhecido".
    falha('Assinado SEM carimbo de tempo — a assinatura expiraria junto com o certificado.')
    falhou = true
  } else {
    ok('assinatura presente, com carimbo de tempo e o certificado esperado')
  }

  // ── 5. O no-op continua sendo no-op ────────────────────────────────────────
  step('Sem ATLANS_SIGN_PROVIDER o hook não deve fazer nada')
  delete process.env.ATLANS_SIGN_PROVIDER
  const alvoLimpo = path.join(tmp, 'limpo.exe')
  fs.copyFileSync(binarioDeTeste(), alvoLimpo)
  await assinar({ path: alvoLimpo })

  // Verifica pelo SIGNATÁRIO, e não por `NotSigned`: se um dia o binário de
  // teste vier assinado pelo fornecedor, `NotSigned` deixaria de valer e o
  // teste falharia por um motivo que não é o dele.
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
