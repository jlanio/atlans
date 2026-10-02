# A marca Atlans

O código do Atlans é livre: AGPL-3.0-only, ver [LICENSE](LICENSE). O nome
**Atlans**, a forma **Atlans.app** e os logotipos (o glifo dos dois nós
ligados, o ícone do web e os do app desktop) não são: são marcas do titular do
projeto, quem mantém o repositório oficial, e a licença do código não dá
direito de usá-las. Esta página diz o que dá para fazer sem pedir.

O objetivo é um só: quem vê o nome Atlans saber que está diante do Atlans
publicado pelo titular, e não de uma versão alterada por outra pessoa.

## Pode, sem pedir

- Falar do Atlans pelo nome: em textos, aulas, comparações e no código («um
  fork do Atlans», «baseado no Atlans», «compatível com o Atlans»).
- Instalar o Atlans, com ou sem modificações, para você ou para a sua
  organização, e mantê-lo com o nome e os logotipos.
- Redistribuir, sem modificação, o código ou os instaladores publicados pelo
  titular, com o nome e os logotipos como vieram.

## Precisa trocar o nome e os logotipos

- Ao distribuir uma versão modificada, em código ou em instalador.
- Ao oferecer o Atlans, modificado ou não, como serviço para pessoas de fora
  da sua organização.

Nesses casos, use outro nome e outros logotipos. Dizer que a sua versão é
«baseada no Atlans» continua permitido, e a AGPL continua valendo para o código
(inclusive o dever de oferecer o código-fonte a quem usa pela rede, seção 13).

## Nunca, sem autorização por escrito

- Usar «Atlans», ou um nome parecido a ponto de confundir, no nome de uma
  empresa, produto, serviço ou domínio.
- Sugerir que o titular apoia, certifica ou mantém o seu produto ou serviço.
- Alterar os logotipos ou usá-los no seu material.

Para pedir uma autorização, abra uma issue no repositório oficial.

## Onde estão o nome e os logotipos

Para quem vai trocar:

- **Logotipos**: `web/app/icon.png`, `web/app/favicon.ico`, o glifo em
  `web/app/components/sidebar/marca.tsx`, a versão animada dele em
  `web/app/components/home/assistente/marca-animada.tsx`, e os ícones e a
  imagem do instalador em `desktop/build/`.
- **Nome**: o título do web (`web/app/layout.tsx`), a marca da barra lateral
  (`marca.tsx`), a tela de entrada, os modelos de e-mail
  (`app/templates/email/`), o remetente padrão (`EMAIL_FROM`) e o app desktop:
  o `productName` em `desktop/package.json` e, em
  `desktop/electron-builder.yml`, o `productName`, o `shortcutName`, o nome do
  protocolo («Atlans Studio») e a linha de `copyright`.
  `git grep -nw Atlans` acha o resto.
- **Os identificadores do app desktop**: o `appId` (`app.atlans.executor`, em
  `desktop/electron-builder.yml`) e o esquema dos links de matrícula,
  `atlans://` (o mesmo arquivo e o `PROTOCOLO` de
  `desktop/src/main/deeplink.ts`). Não aparecem como marca, mas um app
  distribuído com os mesmos se confunde com o oficial no Windows: um instala
  por cima do outro, e os links abrem o app errado. Um fork que distribui o
  próprio app troca os dois.

Os outros nomes técnicos (o pacote `atlans-*`, o volume, o provisioner da
step-ca, as variáveis `ATLANS_*`) não aparecem para quem usa e podem ficar.

## O nome na tela

O código publicado mostra «Atlans» na barra lateral, na tela de entrada e no
título da aba. A forma com o domínio é a instalação do titular, e não vai no
código: cada instalação define o nome que mostra em `NOME_NA_TELA`, no `.env`
([instalação própria](docs/instalacao-propria.md)). Quem precisa trocar o
nome, pelas regras acima, troca ali — e os logotipos, nos arquivos citados.
