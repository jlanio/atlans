// desktop/build/sign.cjs
//
// Hook de assinatura de código do electron-builder.
//
// Sem `ATLANS_SIGN_PROVIDER` no ambiente ele é um no-op e o build sai NÃO
// assinado — funcional, mas com o SmartScreen exibindo "O Windows protegeu o
// computador" e o botão "Executar assim mesmo" escondido atrás de "Mais
// informações". Para um app que dá spawn em `python.exe` e abre WebSocket de
// saída, heurística de antivírus corporativo também é provável.
//
// ── O que escolher ───────────────────────────────────────────────────────────
//
// Token físico USB (o padrão de OV/EV desde jun/2023) é INCOMPATÍVEL com runner
// do GitHub — ninguém pluga um token num runner efêmero. As opções viáveis:
//
//   Azure Trusted Signing   o mais barato de longe (~US$ 10/mês), mas exige
//                           pessoa jurídica com 3+ anos de histórico
//                           verificável. Confirmar elegibilidade de CNPJ
//                           brasileiro ANTES de contar com ele.
//   DigiCert KeyLocker      variante HSM-em-nuvem do OV/EV tradicional.
//   SSL.com eSigner         idem, costuma ser o mais acessível dos dois.
//
// Os três assinam via `signtool` — os dois primeiros com uma DLL de
// interoperabilidade (`/dlib`), o `.pfx` direto só existe para certificados
// antigos e para o autoteste local.
//
// **EV não é obrigatório para funcionar, mas muda muito na prática:** um
// certificado OV começa com reputação zero no SmartScreen e leva instalações
// até deixar de alertar; um EV alerta desde o primeiro dia zero vezes.
//
// ── Como ativar ──────────────────────────────────────────────────────────────
//
//   Azure Trusted Signing / DigiCert KeyLocker
//     ATLANS_SIGN_PROVIDER=dlib
//     ATLANS_SIGN_DLIB=C:\ts\bin\x64\Azure.CodeSigning.Dlib.dll
//     ATLANS_SIGN_DLIB_METADATA=C:\ts\metadata.json
//
//   Arquivo .pfx (certificado antigo, ou o autoteste — ver npm run sign:selftest)
//     ATLANS_SIGN_PROVIDER=pfx
//     ATLANS_SIGN_PFX=C:\caminho\cert.pfx     (ou o conteúdo em base64)
//     ATLANS_SIGN_PFX_PASSWORD=…
//
// No CI, os valores vêm de secrets; o job só os injeta quando existem, então um
// fork sem segredos continua conseguindo buildar.
//
// A extensão é `.cjs`, e não `.js`, porque o package.json declara
// `"type": "module"`: um `.js` seria carregado como ESM e o `exports.default`
// que o electron-builder procura não existiria. O erro que sai nesse caso é um
// stack trace do resolvedor de módulos, sem nenhuma menção a ESM.

'use strict'

const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

/**
 * Carimbo de tempo. **Não é opcional.**
 *
 * Sem ele a assinatura morre junto com o certificado — em 1 a 3 anos todo
 * instalador já distribuído volta a ser "editor desconhecido", inclusive os que
 * o cliente guardou. Com o carimbo, a assinatura continua válida para sempre
 * para os binários assinados enquanto o certificado valia.
 */
const TIMESTAMP_URL = process.env.ATLANS_SIGN_TIMESTAMP || 'http://timestamp.digicert.com'

/** Quantas vezes tentar. O serviço de timestamp é rede, e rede falha. */
const TENTATIVAS = 3

/**
 * Acha o `signtool.exe`.
 *
 * Ele não está no PATH numa máquina comum, e o SDK do Windows **não** é
 * pré-requisito deste projeto — nesta máquina de desenvolvimento, por exemplo,
 * não há Windows Kits nenhum. O que sempre existe é a cópia que o próprio
 * electron-builder baixa no pacote `winCodeSign`, e é ela a primeira escolha.
 *
 * ⚠️ O signtool do `winCodeSign` é antigo e **não suporta `/dlib`**. Para Azure
 * Trusted Signing ou DigiCert KeyLocker, instale o SDK do Windows e aponte
 * `ATLANS_SIGNTOOL` para o binário de lá — o `/dlib` é justamente o que aquele
 * signtool não conhece, e o erro que ele devolve não menciona a versão.
 */
exports.acharSigntool = acharSigntool
function acharSigntool() {
  if (process.env.ATLANS_SIGNTOOL) return process.env.ATLANS_SIGNTOOL

  for (const p of candidatosDoCacheDoBuilder()) {
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
    // Kits não instalado — segue para o PATH.
  }
  return 'signtool.exe'
}

/** `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign\<algo>\windows-10\x64`. */
function candidatosDoCacheDoBuilder() {
  const base = process.env.LOCALAPPDATA
  if (!base) return []
  const raiz = path.join(base, 'electron-builder', 'Cache', 'winCodeSign')

  let entradas
  try {
    entradas = fs.readdirSync(raiz)
  } catch {
    return []
  }

  // O diretório literal `winCodeSign` é o que a versão atual usa; os numéricos
  // são caches de versões anteriores. Mais novo primeiro, e o literal na frente.
  const ordenadas = [
    ...entradas.filter((e) => e === 'winCodeSign'),
    ...entradas.filter((e) => e !== 'winCodeSign').sort().reverse(),
  ]
  return ordenadas.flatMap((e) => [
    path.join(raiz, e, 'windows-10', 'x64', 'signtool.exe'),
    path.join(raiz, e, 'windows-10', 'ia32', 'signtool.exe'),
  ])
}

/** Aceita caminho de arquivo OU o .pfx inteiro em base64 (o que cabe num secret). */
function materializarPfx(valor) {
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

function argumentosDo(provedor, temporarios) {
  if (provedor === 'pfx') {
    const { arquivo, temporario } = materializarPfx(exigir('ATLANS_SIGN_PFX'))
    if (temporario) temporarios.push(arquivo)
    const args = ['/f', arquivo]
    const senha = process.env.ATLANS_SIGN_PFX_PASSWORD
    if (senha) args.push('/p', senha)
    return args
  }

  if (provedor === 'dlib') {
    // Caminho do Azure Trusted Signing e do DigiCert KeyLocker: a chave privada
    // nunca sai do HSM; a DLL fala com o serviço.
    return ['/dlib', exigir('ATLANS_SIGN_DLIB'), '/dmdf', exigir('ATLANS_SIGN_DLIB_METADATA')]
  }

  throw new Error(
    `ATLANS_SIGN_PROVIDER='${provedor}' desconhecido. Use 'pfx' ou 'dlib'.`,
  )
}

/**
 * @param {{ path: string, hash?: string, isNest?: boolean }} configuration
 *   `path` é o arquivo a assinar — o .exe do app e, depois, o do instalador.
 */
exports.default = async function sign(configuration) {
  const provedor = process.env.ATLANS_SIGN_PROVIDER
  if (!provedor) {
    // Silencioso de propósito: o build local e o do CI sem segredos são o caso
    // NORMAL hoje. Um aviso a cada arquivo assinado viraria ruído que se
    // aprende a ignorar — e aí o dia em que a assinatura falhar de verdade
    // passa despercebido.
    return
  }

  const temporarios = []
  try {
    const args = [
      'sign',
      // SHA-256 em tudo. SHA-1 ainda é aceito por compatibilidade antiga e é
      // exatamente o tipo de default que passa despercebido.
      '/fd', 'sha256',
      '/td', 'sha256',
      '/tr', TIMESTAMP_URL,
      ...argumentosDo(provedor, temporarios),
      // `isNest` = o arquivo já tem uma assinatura e esta é adicional. Sem
      // `/as`, a segunda SUBSTITUI a primeira em silêncio.
      ...(configuration.isNest ? ['/as'] : []),
      configuration.path,
    ]

    const signtool = acharSigntool()
    let ultimoErro
    for (let i = 1; i <= TENTATIVAS; i++) {
      try {
        execFileSync(signtool, args, { stdio: 'inherit' })
        return
      } catch (erro) {
        ultimoErro = erro
        if (i < TENTATIVAS) {
          console.warn(`[sign] tentativa ${i}/${TENTATIVAS} falhou; repetindo…`)
          // Espera curta e crescente: quase toda falha aqui é o servidor de
          // timestamp recusando por excesso de requisições.
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000 * i)
        }
      }
    }

    throw new Error(
      `Falha ao assinar ${configuration.path} com signtool (${TENTATIVAS} tentativas). ` +
      `Um build que DEVERIA ser assinado e sai sem assinatura é pior que um build ` +
      `que não termina: ele chega ao usuário com o aviso do SmartScreen e ninguém ` +
      `percebe até o primeiro chamado de suporte. Causa: ${ultimoErro && ultimoErro.message}`,
    )
  } finally {
    for (const t of temporarios) {
      try { fs.unlinkSync(t) } catch { /* já removido */ }
    }
  }
}
