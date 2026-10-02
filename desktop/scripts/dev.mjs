// desktop/scripts/dev.mjs
//
// Modo desenvolvimento: Vite servindo o renderer com HMR + Electron apontado
// para ele.
//
// Em dev o app usa `resources/python` se existir e cai no Python do sistema se
// nao — assim da para iterar na UI sem reconstruir 390 MB a cada mudanca (ver
// `resolverPythonDev` em src/main/paths.ts).
//
//   node scripts/dev.mjs
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { createServer } from 'vite'
import { DESKTOP, log, ok, run, step } from './lib.mjs'

// O binario do Electron nao vem no `npm ci`: o pacote (44+) o baixa na primeira
// vez que e chamado, e o desktop/.npmrc desliga os scripts de instalacao de
// qualquer forma. Baixa aqui, uma vez e num passo a vista (e nao escondido no
// `import('electron')` la embaixo), pelo proprio install.js do pacote — que
// confere o SHA-256 pelo checksums.json que veio no tarball do npm (este, por
// sua vez, conferido pelo hash do package-lock).
const ELECTRON = path.join(DESKTOP, 'node_modules', 'electron')
if (!fs.existsSync(path.join(ELECTRON, 'path.txt'))) {
  step('Baixando o binario do Electron (primeira vez depois do npm ci)')
  run(process.execPath, [path.join(ELECTRON, 'install.js')], { stdio: 'inherit' })
}

step('Subindo o dev server do renderer')
const vite = await createServer({ configFile: `${DESKTOP}/vite.config.ts` })
await vite.listen()
const url = vite.resolvedUrls?.local?.[0]
if (!url) throw new Error('o Vite nao reportou a URL local')
ok(`renderer em ${url}`)

step('Compilando main e preload (com sourcemap)')
run(process.execPath, [`${DESKTOP}/scripts/build-main.mjs`, '--dev'], { stdio: 'inherit' })

step('Abrindo o Electron')

// `ELECTRON_RUN_AS_NODE` faz o executavel do Electron virar Node puro: sem
// modulo `electron`, sem janela, e o processo morre com
// "Cannot find module 'electron'" — que com `stdio: inherit` some no meio da
// saida do Vite. Terminais integrados de editor definem essa variavel, e ela e
// herdada por tudo que roda dali.
//
// Removida aqui, e nao documentada como pre-requisito: exigir que o usuario
// saiba disso para rodar `npm run dev` seria transferir a ele um problema que o
// script pode resolver sozinho.
const env = { ...process.env, VITE_DEV_SERVER_URL: url }
if (env.ELECTRON_RUN_AS_NODE) {
  log('ELECTRON_RUN_AS_NODE estava definido no ambiente — removido para este processo.')
  delete env.ELECTRON_RUN_AS_NODE
}

const electron = spawn((await import('electron')).default, [DESKTOP], {
  stdio: 'inherit',
  env,
})

// Fechar o app derruba o dev server junto: um Vite orfao segurando a porta faz
// o proximo `npm run dev` falhar com "port is already in use".
electron.on('exit', (codigo) => {
  log(`Electron encerrou (${codigo})`)
  void vite.close().then(() => process.exit(codigo ?? 0))
})

for (const sinal of ['SIGINT', 'SIGTERM']) {
  process.on(sinal, () => { electron.kill(); void vite.close() })
}
