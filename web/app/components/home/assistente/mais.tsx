"use client"

// web/app/components/home/assistente/mais.tsx
//
// O "+" do compositor e o chip de localização — as duas peças novas do
// "localizar no assistente". Montados pela barra E pelo painel, como os anexos,
// porque Ctrl+I troca uma superfície pela outra e o recurso não pode sumir com a
// troca (o achado 4 da revisão 3: um recurso numa superfície e não na outra).
//
// - `BotaoMais`: o menu do "+". Reúne o que ENTRA na conversa fora do texto —
//   hoje "Anexar arquivo" (o mesmo caminho do arrasta-e-solta, agora com um lar
//   descobrível) e "Usar minha localização" (aciona o controle do globo). Um
//   menu, e não dois botões soltos, para não inchar a pílula da barra.
// - `ChipDeLocalizacao`: a localização anexada, à vista e removível — o espelho
//   dos `ChipsDeAnexo`. Lê a store direto (como os anexos), então não precisa de
//   prop; o × só tira da conversa, não desliga o seguir no globo.

import { useRef } from "react"
import { TbCurrentLocation, TbMapPin, TbPaperclip, TbPlus, TbX } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { useHomeStore } from "@/app/stores/homeStore"
import { cn } from "@/lib/utils"
import { useTextos } from "../i18n"

/** lat/lon com 4 casas (~11 m) — o resto é ruído para o assistente. */
function coord(n: number): string {
  return n.toFixed(4)
}

/**
 * O "+" do compositor: um menu com o que se pode juntar ao turno além do texto.
 * `aoAnexar`/`aoLocalizar` vêm da HomeView (o upload e o acionar do globo). Sem
 * nenhum dos dois a barra não o monta (é o que mantém os testes existentes
 * intactos), então aqui eles são opcionais só por segurança de tipos.
 */
export function BotaoMais({
  aoAnexar, aoLocalizar, className,
}: {
  aoAnexar?: (arquivos: File[]) => void
  aoLocalizar?: () => void
  className?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const t = useTextos().assistente.mais

  return (
    <>
      {/* O mesmo caminho do arrasta-e-solta (useAnexos.receber); o servidor é
          quem filtra, então nada de `accept` aqui — igual ao arraste. */}
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        tabIndex={-1}
        aria-hidden="true"
        data-testid="entrada-de-arquivo"
        onChange={(e) => {
          const arquivos = Array.from(e.target.files ?? [])
          // Zera para que soltar/escolher o MESMO arquivo de novo redispare o change.
          e.target.value = ""
          if (arquivos.length) aoAnexar?.(arquivos)
        }}
      />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={cn("shrink-0 text-muted-foreground", className)}
            aria-label={t.rotulo}
            title={t.titulo}
          >
            <TbPlus size={16} aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        {/* `home-portal`: o menu é portado ao <body>, FORA da árvore `home dark` —
            sem a classe ele sairia claro sobre a Home sempre-escura quando o tema
            do app é claro (o mesmo idioma do menu dos Chats). */}
        <DropdownMenuContent align="start" side="top" className="home-portal min-w-56">
          <DropdownMenuItem onSelect={() => inputRef.current?.click()}>
            <TbPaperclip size={15} aria-hidden="true" />
            {t.anexar}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => aoLocalizar?.()}>
            <TbCurrentLocation size={15} aria-hidden="true" />
            {t.localizacao}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  )
}

/**
 * A localização anexada — à vista, na mesma fileira dos chips de anexo. Lê a
 * store direto (a coordenada pode mudar ao vivo no modo seguir). Só aparece com
 * o COMPARTILHAR ligado: o × desliga a intenção — e ela fica desligada, mesmo
 * com o seguir do globo ainda emitindo posições — até um novo gesto no "+".
 * O seguir no globo continua até a pessoa desligá-lo lá.
 */
export function ChipDeLocalizacao({ className }: { className?: string }) {
  const compartilhar = useHomeStore((s) => s.compartilharLocalizacao)
  const localizacao = useHomeStore((s) => s.localizacao)
  const limpar = useHomeStore((s) => s.limparLocalizacao)
  const t = useTextos().assistente.mais
  if (!compartilhar || !localizacao) return null

  const precisao = localizacao.precisao_m != null && Number.isFinite(localizacao.precisao_m)
    ? `±${Math.round(localizacao.precisao_m)} m`
    : null

  return (
    <div
      data-testid="chip-de-localizacao"
      className={cn("flex list-none flex-wrap gap-1.5 p-0", className)}
    >
      <span className="flex min-w-0 max-w-full items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-2 py-1 text-[11.5px]">
        <TbMapPin size={13} className="shrink-0 text-primary" aria-hidden="true" />
        <span className="min-w-0 truncate font-mono tabular-nums text-foreground">
          {coord(localizacao.lat)}, {coord(localizacao.lon)}
        </span>
        {precisao && <span className="shrink-0 font-mono text-muted-foreground">{precisao}</span>}
        <button
          type="button"
          onClick={limpar}
          aria-label={t.tirarLocalizacao}
          className="shrink-0 rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <TbX size={12} aria-hidden="true" />
        </button>
      </span>
    </div>
  )
}
