# Revisão obrigatória em `main`

A `main` é protegida por um **ruleset** do GitHub. A definição fica versionada
em [`.github/rulesets/main.json`](../.github/rulesets/main.json): para mudar a
regra, edite o arquivo num PR e reaplique com o comando abaixo. O ruleset:

- vale para a branch padrão (`~DEFAULT_BRANCH`) e fica `active`;
- exige PR para entrar em `main`, com **0 aprovações**. O repositório tem uma
  identidade só (dono e agentes publicam como `jlanio`), e o GitHub não deixa o
  autor aprovar o próprio PR. Com 1 aprovação obrigatória, nenhum PR entraria.
  Quem faz o papel do revisor é o check `Revisão (QA)`;
- exige estes checks verdes: `Secrets scan (detect-secrets)`, `Backend (Python)`,
  `Backend sem extensões (núcleo)`, `Frontend (Next.js)`,
  `Frontend sem extensões (núcleo)`, `Desktop (typecheck + testes + lock)` e
  `Revisão (QA)`. A `Auditoria de dependências (informativa)` fica de fora de
  propósito: ela avisa, não bloqueia. A branch não precisa estar atualizada com
  a `main` para o merge (`strict` desligado);
- bloqueia force-push (`non_fast_forward`) e a exclusão da `main` (`deletion`);
- deixa o papel **Repository admin** pular as regras **só por PR**
  (`bypass_mode: pull_request`): o bypass fica registrado no PR, e push direto
  continua bloqueado até para o admin.

## O que muda no seu dia

1. Abra um PR para `main`.
2. O CI roda.
3. O QA revisa o PR.
4. Com a aprovação do QA, o check `Revisão (QA)` fica verde.
5. Com todos os checks verdes, faça o merge.

Push direto em `main` deixa de funcionar, e o seu também.

## Como aplicar / atualizar o ruleset

> **Antes da primeira aplicação:** o job `Revisão (QA)` (ATL-13) precisa já
> estar na `main` e rodando nos PRs. Um check obrigatório que nunca é publicado
> deixa todo PR esperando para sempre.

Rode na raiz do repositório, com o `gh` logado como admin.

Primeira vez (cria o ruleset):

```sh
gh api -X POST repos/jlanio/atlans/rulesets --input .github/rulesets/main.json
```

Depois de mudar o JSON (atualiza o ruleset que já existe):

```sh
ID=$(gh api repos/jlanio/atlans/rulesets --jq '.[] | select(.name == "main") | .id')
gh api -X PUT "repos/jlanio/atlans/rulesets/$ID" --input .github/rulesets/main.json
```

Pela interface: **Settings → Rules → Rulesets → New ruleset → Import a ruleset**
e escolha o `main.json`. Para atualizar, abra o ruleset `main` e edite os mesmos
campos. Se usar a interface, confira depois que o resultado bate com o arquivo:

```sh
ID=$(gh api repos/jlanio/atlans/rulesets --jq '.[] | select(.name == "main") | .id')
gh api "repos/jlanio/atlans/rulesets/$ID" --jq '{enforcement, bypass_actors, rules}'
```

## Caminho de emergência

Use só quando o merge não pode esperar a revisão (produção quebrada, correção de
segurança).

**a) Bypass no PR.** No PR, marque *"Merge without waiting for requirements to
be met (bypass rules)"* e faça o merge. Só o admin vê essa opção, e o GitHub
registra o bypass no PR.

**b) Revisão pós-fato.** Na mesma hora, abra uma issue
`Revisão pós-fato PR #<N>` atribuída ao QA. O QA revisa em até 24h.
Se achar problema, a correção entra por um PR normal.

**c) Último recurso: desligar o ruleset.** Só se o bypass não resolver (por
exemplo, se a mudança não cabe num PR). Desligue:

```sh
ID=$(gh api repos/jlanio/atlans/rulesets --jq '.[] | select(.name == "main") | .id')
gh api -X PUT "repos/jlanio/atlans/rulesets/$ID" -f enforcement=disabled
```

Ao terminar, religue com o mesmo comando:

```sh
ID=$(gh api repos/jlanio/atlans/rulesets --jq '.[] | select(.name == "main") | .id')
gh api -X PUT "repos/jlanio/atlans/rulesets/$ID" -f enforcement=active
```

Pela interface: **Settings → Rules → Rulesets → main → Enforcement status →
Disabled**, e de volta para **Active**.

**Não apague o ruleset.** Desligado, ele guarda a configuração e o histórico, e
volta com um comando. Apagado, some o histórico e quem religar depende de o
JSON do repositório estar em dia. Abra também a issue de revisão pós-fato do
passo (b) para o que entrou enquanto ele esteve desligado.

## Limitação conhecida

O check `Revisão (QA)` é publicado sob a mesma identidade do autor do PR
(`jlanio`). Na prática, a regra garante que o fluxo passe pelo QA, mas o GitHub
não tem como saber se foi mesmo o QA que deixou o check verde. O reforço real é
uma GitHub App exclusiva do QA, que publicaria o check com identidade própria.
Isso está em avaliação na ATL-4.

## Checks futuros

Estes entram na lista de checks obrigatórios quando estiverem estáveis na
`main` (edite o `main.json` num PR e reaplique):

- `E2E (Playwright)`: o teste de navegador da M3 (ATL-6);
- a checagem de atribuição de commits da ATL-11.
