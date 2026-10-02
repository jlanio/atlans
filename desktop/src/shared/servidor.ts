// desktop/src/shared/servidor.ts
//
// O servidor do Atlans é FIXO neste app.
//
// Não é uma preferência com um bom default: é a única origem à qual este
// executável se vincula. Deixar o endereço editável dava a qualquer pessoa com
// acesso à máquina — ou a uma página web disparando um deep link — a chance de
// apontar o executor para outro servidor, e um executor apontado para servidor
// alheio roda, com as permissões do usuário, os workflows que aquele servidor
// mandar.
//
// Por isso o valor é gravado no executável pelo BUILD (ATLANS_DESKTOP_SERVIDOR,
// ver scripts/enderecos.mjs), e não vem de `.env`, nem de campo de formulário,
// nem de parâmetro de IPC vindo do renderer. O `.env` continua recebendo
// `EXECUTOR_SERVER_URL` porque é o Python que o lê, mas quem o escreve é sempre
// o main process, sempre com esta constante.
//
// O código não traz o endereço de instalação nenhuma: cada build grava o seu.
// Instalação apontada para outro servidor exige outro build. É deliberado.
declare const __ATLANS_SERVIDOR__: string
export const SERVIDOR: string = __ATLANS_SERVIDOR__

/** Host de {@link SERVIDOR} — o único aceito num deep link de enrollment. */
export const SERVIDOR_HOST = new URL(SERVIDOR).hostname
