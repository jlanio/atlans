# Atlans — Design System

Extraído dos componentes existentes em `web/app/components/`.
Framework: Tailwind CSS v4 + shadcn/ui + Radix primitives.

---

## Spacing

Base unit: **4px** (Tailwind rem/4 system)

| Token     | Value | Uso principal                        |
|-----------|-------|--------------------------------------|
| `gap-0.5` | 2px   | Entre ícone e texto inline           |
| `gap-1`   | 4px   | Itens compactos                      |
| `gap-1.5` | 6px   | Card header rows, sheet header       |
| `gap-2`   | 8px   | Botões em footer, dialog header/desc |
| `gap-4`   | 16px  | Seções dentro de card/dialog/sheet   |
| `gap-6`   | 24px  | Seções de página (PageRoot)          |

| Contexto       | Horizontal | Vertical   |
|----------------|------------|------------|
| Page (PageRoot)| `px-8`(32) | `py-8`(32) |
| Card content   | `px-6`(24) | `py-5`(20) |
| Dialog content | `p-6` (24) | `p-6` (24) |
| Sheet header   | `p-4` (16) | `p-4` (16) |
| EntityCard     | `px-3`(12) | `py-3.5`(14) |
| Table cell     | `px-4-6`   | `py-2-2.5` |

**Regra:** Espaçamentos devem estar no grid de 4px. Exceções toleradas: `py-3.5`(14px) no EntityCard, `py-0.5`(2px) em badges.

---

## Radius

Base CSS variable: `--radius: 0.5rem` (8px)

| Token        | Value | Cálculo                  | Uso                          |
|--------------|-------|--------------------------|------------------------------|
| `rounded-sm` | 4px   | `var(--radius) - 4px`    | Select items, separators     |
| `rounded-md` | 6px   | `var(--radius) - 2px`    | Button, Input, Select, Skeleton |
| `rounded-lg` | 8px   | `var(--radius)`          | Card, Dialog, EntityCard     |
| `rounded-xl` | 12px  | `var(--radius) + 4px`    | Containers maiores           |
| `rounded-full`| pill | —                        | Badge, StatusBadge, Avatar   |

**Regra:** Não usar valores arbitrários de radius (`rounded-[Xpx]`). Usar apenas os tokens acima.

---

## Depth (Elevação)

Estratégia: **Borders-first** com sombras mínimas para elevação.

| Nível     | Estilo                 | Componentes                |
|-----------|------------------------|----------------------------|
| Nível 0   | sem border/shadow      | Backgrounds, content areas |
| Nível 1   | `border` + `shadow-xs` | Card, EntityCard           |
| Nível 2   | `border` + `shadow-md` | Select popover, Dropdown   |
| Nível 3   | `border` + `shadow-lg` | Dialog, Sheet              |

**Regras:**
- Ring shadows (`ring-[3px]`, `0 0 0 Xpx`) são permitidos para focus states.
- `shadow-xl` e `shadow-2xl` não são usados — evitar.
- Overlays usam `bg-black/50`.

---

## Colors

Sistema de tokens OKLCH via CSS custom properties. Dois temas: light e dark.

### Tokens semânticos

| Token                  | Light (oklch)              | Dark (oklch)               |
|------------------------|----------------------------|----------------------------|
| `--background`         | `0.985 0.003 75`           | `0.188 0.008 55`           |
| `--foreground`         | `0.18 0.02 65`             | `0.93 0.004 70`            |
| `--primary`            | `0.57 0.17 43` (terracota) | `0.68 0.16 44`             |
| `--primary-foreground` | `1 0 0` (branco)           | `0.99 0 0`                 |
| `--secondary`          | `0.96 0.006 72`            | `0.285 0.008 55`           |
| `--muted`              | `0.96 0.006 72`            | `0.270 0.008 55`           |
| `--muted-foreground`   | `0.50 0.03 68`             | `0.60 0.008 60`            |
| `--accent`             | `0.95 0.008 70`            | `0.270 0.008 55`           |
| `--destructive`        | `0.577 0.245 27.325`       | `0.65 0.21 22`             |
| `--card`               | `1 0 0`                    | `0.215 0.008 55`           |
| `--border`             | `0.90 0.012 70`            | `1 0 0 / 9%`               |

### Status colors (hardcoded no StatusBadge)

| Status    | Background      | Text            |
|-----------|-----------------|-----------------|
| success   | `bg-green-100`  | `text-green-700` |
| failed    | `bg-red-100`    | `text-red-700`   |
| error     | `bg-red-100`    | `text-red-700`   |
| running   | `bg-blue-100`   | `text-blue-700`  |
| pending   | `bg-yellow-100` | `text-yellow-700`|
| cached    | `bg-purple-100` | `text-purple-700`|
| cancelled | `bg-amber-100`  | `text-amber-700` |
| fallback  | `bg-muted`      | `text-muted-foreground` |

Cada par acima vem sempre acompanhado da variante `dark:` no código (ex.: `dark:bg-green-500/15 dark:text-green-400`, `cancelled` → `dark:bg-amber-500/15 dark:text-amber-400`); a tabela lista só o tom claro. Fonte: `StatusBadge.tsx`.

### Execução no canvas (`--exec-*`)

Fonte única do estado de execução, consumida pelo card do nó **e** pela aresta que sai dele. Antes cada um trazia o próprio hex, os dois discordavam (`unknown` deixava o card âmbar e a aresta cinza) e nenhum trocava com o tema.

| Token           | Light (oklch)      | Dark (oklch)      | Uso                        |
|-----------------|--------------------|-------------------|----------------------------|
| `--exec-idle`   | `0.62 0.020 68`    | `0.56 0.015 62`   | neutro; ramo perdedor      |
| `--exec-running`| `0.58 0.160 254`   | `0.70 0.145 250`  | nó em `started`            |
| `--exec-success`| `0.62 0.145 152`   | `0.74 0.150 152`  | `completed`; ramo `true`   |
| `--exec-error`  | `0.575 0.205 27`   | `0.68 0.190 24`   | `failed`; ramo `false`     |
| `--exec-unknown`| `0.70 0.140 72`    | `0.80 0.140 76`   | `unknown`                  |
| `--exec-cache`  | `0.74 0.150 88`    | `0.85 0.140 90`   | badge de `cache_hit`       |

Disponíveis como utilitários (`text-exec-running`, `bg-exec-error/10`) via `@theme inline`. `--exec-halo-near` / `--exec-halo-far` calibram a intensidade do halo por tema.

**Regras do canvas:**
- O anel de estado vive em `.exec-card::after` (`outline`), **nunca** em `ring-*`. `ring-*`, `shadow-sm` e keyframes de brilho disputam a mesma propriedade `box-shadow`, e um keyframe substitui a declaração inteira — foi o que apagava o anel de seleção durante o pulso.
- O halo vive em `.exec-card::before` e anima só `opacity`/`transform` (compositor). Animar blur ou spread repinta a sombra a cada quadro, em todo nó ativo.
- Estados se distinguem também por **forma**, não só por matiz: `unknown` e "pendente" usam anel tracejado, porque a 0.42 de zoom dois âmbares viram a mesma mancha.

### Chart colors

`chart-1` a `chart-5` definidos em `globals.css`. Usar via tokens `--chart-N`.

**Regras:**
- Usar sempre tokens semânticos (`text-foreground`, `bg-primary`, etc.) — nunca cores brutas (`text-gray-900`) para conteúdo geral.
- Status colors (green/red/blue/yellow/purple-100/700) são a exceção aceita para indicadores de status no `StatusBadge`. No canvas de workflow use os tokens `--exec-*`.
- `text-[10px]` nos trend badges é a única exceção de tamanho fora do grid.

---

## Typography

Fontes: Inter (body; `--font-sans`, via next/font em `app/layout.tsx` → `--font-inter`) / pilha monoespaçada do sistema (code/IDs; `--font-mono`: SF Mono, Consolas, Liberation Mono…). A Inter carrega os pesos 400–700; a mono do sistema só tem 400 e 700, então `font-medium` em `font-mono` sai regular.

| Nível           | Classes                               | Uso                              |
|-----------------|---------------------------------------|----------------------------------|
| Page title      | `text-2xl font-semibold`              | h1 de página                    |
| Section title   | `text-base font-medium` ou `font-semibold` | CardTitle de seção         |
| Body            | `text-sm`                             | Texto geral, labels, inputs     |
| Description     | `text-sm text-muted-foreground`       | CardDescription, DialogDescription |
| Meta            | `text-xs text-muted-foreground`       | Timestamps, IDs, stats          |
| Micro           | `text-[10px]`                         | Trend badges (exceção)          |
| Mono            | `font-mono text-xs`                   | Run IDs, hashes                 |

**Regras:**
- `font-semibold` para títulos de Card/Dialog.
- `font-medium` para labels, badges, items de lista.
- Não usar `font-bold` fora de valores numéricos em destaque (`text-2xl font-bold` no MetricCard).

---

## Patterns

### Button

Definido em `ui/button.tsx` via CVA.

| Size      | Height | Padding          | Radius      |
|-----------|--------|------------------|-------------|
| `default` | h-9    | `px-4 py-2`      | `rounded-md`|
| `sm`      | h-8    | `px-3`           | `rounded-md`|
| `lg`      | h-10   | `px-6`           | `rounded-md`|
| `icon`    | size-9 | —                | `rounded-md`|

Variantes: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`.

**Regra:** Não criar botões ad-hoc com `<button className="...">`. Usar sempre `<Button>` do componente.

### Card

Definido em `ui/card.tsx`.

- Container: `rounded-lg border shadow-xs bg-card text-card-foreground`
- Vertical gap: `gap-4` entre seções
- Header/Content/Footer: `px-6`
- Card vertical padding: `py-5`

**EntityCard** (variante compacta para listas):
- `px-3 py-3.5 rounded-lg gap-0`
- Title: `text-sm font-medium`
- Description: `text-xs`

**MetricCard** (variante para KPIs):
- Usa Card padrão
- Header: `flex-row items-center justify-between pb-2`
- Valor: `text-2xl font-bold`

### Input

Definido em `ui/input.tsx`.

- Height: `h-9` (36px)
- Padding: `px-3 py-1`
- Radius: `rounded-md`
- Border: `border border-input`
- Focus: `focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]`

### Badge

Definido em `ui/badge.tsx`.

- Shape: `rounded-full`
- Padding: `px-2.5 py-0.5`
- Text: `text-xs font-semibold`
- Border: `border` (transparent para variantes preenchidas)

**StatusBadge** (variante para status de execução):
- Mesma forma do Badge mas com cores hardcoded por status
- Inclui ícone inline (TbCheck, TbX)

### Dialog

Definido em `ui/dialog.tsx`.

- Max width: `sm:max-w-lg`
- Padding: `p-6`
- Radius: `rounded-lg`
- Depth: `border shadow-lg`
- Gap: `gap-4` entre header/content/footer
- Overlay: `bg-black/50`

### Sheet

Definido em `ui/sheet.tsx`.

- Default side: `right`
- Max width: `sm:max-w-sm`
- Depth: `shadow-lg` + border lateral
- Header/Footer: `p-4`
- Gap: `gap-4`

---

## Layout

### Page container (PageRoot)

```
<main className="flex justify-center w-full px-safe">
  <div className="flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out">
```

### Grid patterns

| Contexto          | Mobile          | Desktop              |
|-------------------|-----------------|----------------------|
| Indicadores/stat  | `grid-cols-2`   | `lg:grid-cols-4`     |
| Content/lateral   | `grid-cols-1`   | `lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]` |
| Cards/linhas      | `sm:grid-cols-2`| `xl:grid-cols-3`     |
| Gaps              | `gap-3`/`gap-4` | `gap-3`/`gap-4`      |

### Trilho de colunas (listagem densa)

Uma grade de colunas fixas — o trilho de `/executores` — não sobrevive ao
telefone: as colunas somam ~360px antes do nome, e o `overflow-x: clip` do body
**corta** o excesso em vez de rolar, levando junto a coluna de ações.

Padrão em três faixas, com UMA declaração de grade compartilhada por cabeçalho e
linhas:

| Faixa   | Forma                                                              |
|---------|--------------------------------------------------------------------|
| `< md`  | duas linhas por item; cabeçalho de colunas `hidden`; o bloco de metadados vira uma linha `flex-wrap` |
| `md`    | trilho enxuto — saem as colunas que só qualificam (tipo, versão)   |
| `lg`    | trilho inteiro                                                     |

**Regras:**
- O mesmo markup serve as duas formas: o bloco de metadados usa `md:contents`,
  então de `md` para cima ele some do layout e os filhos voltam a ser células.
- Célula que só existe no trilho inteiro: `md:hidden lg:block` (ou
  `lg:inline-flex`, conforme o display do elemento).
- Traço de "sem valor" (`—`) é **marcador de coluna**: esconda-o onde não há
  coluna, senão ele vira um símbolo solto no empilhamento.

### Tabela empilhada (`<table>` no telefone)

`overflow-x-auto` + `min-w-[N]` mantém a tabela alcançável, mas ler o status de
uma execução passa a exigir arrastar a lista de lado. O padrão do repo é
`app/components/shared/tabela-empilhada.ts`: abaixo de `md` a `<tr>` deixa de ser
linha e vira uma faixa `flex-wrap` de fatos, na mesma ordem das colunas.

| Constante              | Onde                | O que faz                                   |
|------------------------|---------------------|---------------------------------------------|
| `CABECALHO_DE_COLUNAS` | `<thead>`           | some onde não há colunas                     |
| `LINHA_EMPILHADA`      | `<tr>` de dados     | vira ficha; zera o padding das células       |
| `DESTAQUE_DA_FICHA`    | `<td>` que identifica | ocupa a primeira linha sozinho             |
| `CELULA_COM_ROTULO`    | `<td>` numérico     | leva o rótulo junto (`data-rotulo`)          |
| `LINHA_EXPANDIDA`      | `<tr>` com `colSpan` | bloco, não ficha                            |

**Regras:**
- Todas as classes são `max-md:`. De `md` para cima a tabela é a de antes —
  nenhum `<td>` precisa ser editado, e não há como regredir o desktop.
- O `min-w-[N]` da tabela passa a ser `md:min-w-[N]`: sem colunas não há o que
  forçar.
- Número sem coluna é número solto: `0` pode ser falhas ou cache hits, `1,2 GB`
  pode ser Drive ou total. Esses ganham `data-rotulo`.

### Toque (`coarse:`)

Variante declarada em `globals.css` como `@media (pointer: coarse)`. É do
PONTEIRO, não da largura: um tablet de 1280px com toque precisa da regra e um
notebook estreito não.

**Regra:** tudo o que só aparece sob `hover:` (a seta que diz que a linha leva a
algum lugar, o botão de copiar de um bloco de código) precisa de um
`coarse:opacity-*` — no telefone o `hover:` nunca acontece, e a affordance
simplesmente não existe.

### Sidebar

- Background: `bg-sidebar` (token dedicado, mais escuro que card)
- Content area: `bg-card`
- Drawer (workflow): `min-w-[26rem] w-[26rem] bg-card`

---

## Animações

| Nome               | Duração  | Easing          | Uso                     |
|--------------------|----------|-----------------|-------------------------|
| `animate-in`       | default  | ease            | Dialog/Sheet/Select open |
| `fade-in-0`        | default  | ease            | Overlays, popovers      |
| `zoom-in-95`       | default  | ease            | Dialog/Tooltip scale-in |
| `slide-in-from-*`  | default  | ease            | Sheet/Select direção    |
| `theme-appear`     | 400ms    | ease-in-out     | Theme toggle            |
| `animate-pulse`    | default  | —               | Skeleton loading        |
| `animate-spin`     | default  | linear          | Loading spinner         |

### Canvas de workflow

Todas em `.exec-card::before` (halo), exceto onde indicado. Ver "Execução no canvas" em Colors.

| Nome                | Duração | Easing                       | Estado                      |
|---------------------|---------|------------------------------|-----------------------------|
| `exec-breathe`      | 2.4s    | `cubic-bezier(.45,0,.55,1)` ∞ | `started` — respiração      |
| `exec-settle`       | 620ms   | `cubic-bezier(.22,1,.36,1)`  | `completed` — a luz pousa   |
| `exec-alert`        | 760ms   | `cubic-bezier(.22,1,.36,1)`  | `failed` — entrada, e para  |
| `exec-idle-breathe` | 2.8s    | `ease-in-out` ∞              | pendente, run de pé         |
| `exec-arrive`       | 2.4s    | `cubic-bezier(.22,1,.36,1)`  | nó recém-adicionado         |
| `edge-flow-fast`    | 420ms   | `linear` ∞                   | aresta ativa — camada miúda |
| `edge-flow-slow`    | 1.5s    | `linear` ∞                   | aresta ativa — camada graúda|
| `edge-glow-pulse`   | 1.6s    | `ease-in-out` ∞              | brilho sob a aresta ativa   |
| `edge-flow-hint`    | 1.05s   | `linear` ∞                   | aresta sob o cursor         |
| `exec-activity-wave`| 1s      | `ease-in-out` ∞              | badge do nó em execução     |

**Regras:**
- Sheet usa `duration-300` (close) / `duration-500` (open). Dialog usa `duration-200`.
- `failed` **não** anima em loop. Um anel vermelho parado já é alto; o que precisa chamar é a entrada. Vários nós piscando fora de fase deixavam o canvas ilegível, e o painel de problemas já persegue o usuário.
- A aresta ativa usa **duas** correntes de pontos em paralaxe (`fast` miúda e veloz, `slow` graúda e espaçada) mais o brilho pulsante. Uma corrente só, de pontos iguais, lê como pontilhado escorregando; duas de calibre diferente leem como tráfego.
- Hover numa aresta parada usa `edge-flow-hint` — **uma** corrente e sem brilho. É o que separa "direção sob demanda" de "aresta viva", agora que a ativa ganhou densidade.
- O badge do nó em execução usa `ExecActivity` (barras oscilando), **não** um spinner girando: rotação é o glifo universal de "aguarde", e o que o badge precisa dizer é que há trabalho acontecendo.
- Toda animação do canvas degrada sob `prefers-reduced-motion: reduce` para o **quadro informativo**, nunca para nada: cada estado precisa continuar distinguível sem movimento.

---

## Focus & Accessibility

- Focus ring: `focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring`
- Invalid state: `aria-invalid:ring-destructive/20 aria-invalid:border-destructive`
- Disabled: `disabled:pointer-events-none disabled:opacity-50`
- Screen reader: `<span className="sr-only">` para botões de fechar
- SVGs: `[&_svg]:pointer-events-none [&_svg]:shrink-0`
