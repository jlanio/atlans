"use client"

import { useId, useRef, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import {
  DialogClose, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"

interface DeleteDialogProps {
  /** Pode trazer um ícone junto (a revogação em lote traz o escudo). */
  title: React.ReactNode
  /** Pode trazer marcação: o nome em destaque, o bloco com o texto a digitar. */
  description: React.ReactNode
  /**
   * Aviso DISCRETO abaixo da descrição (ex: "em uso em N nós"). De propósito uma
   * linha muted, não um painel colorido — o contexto extra não deve gritar mais
   * que a própria confirmação.
   */
  note?: React.ReactNode
  /**
   * Avisos entre a descrição e a confirmação: o que a ação leva junto (os crons
   * que param, os arquivos que não voltam) ou o conflito que pede o «mesmo
   * assim». Ao contrário do `note`, são painéis — e o painel é de quem chama.
   */
  children?: React.ReactNode
  /**
   * Confirmação por digitação: o botão só libera quando o campo traz EXATAMENTE
   * este texto (o nome do recurso, «REVOGAR»). Reservada ao que não se desfaz.
   * Enter no campo confirma pelo mesmo caminho do botão, com a mesma trava — era
   * no Enter que o duplo envio escapava nas cópias que cada diálogo tinha disto.
   */
  confirmarDigitando?: string
  /**
   * O pedido acima do campo («Para confirmar, digite …»). Sem ele o pedido fica
   * na `description`, com o texto em bloco copiável.
   */
  rotuloDigitando?: React.ReactNode
  /** Pode ser async — o diálogo aguarda e trava os botões enquanto executa. */
  onConfirm: () => void | Promise<void>
  /**
   * Verbo do botão de confirmação. Nem toda ação destrutiva é uma exclusão:
   * "Remover" um membro e "Sair" de um workspace precisam da mesma trava contra
   * duplo clique, mas rotulá-las como "Excluir" descreveria a ação errada.
   */
  confirmLabel?: string
  /**
   * Rótulo enquanto executa — passe o gerúndio ("Removendo…", "Saindo…").
   * Sem ele o fallback é `${confirmLabel}…`, que não é português correto para
   * verbo nenhum além do caso já coberto do "Excluir".
   */
  loadingLabel?: string
  /**
   * Rótulo do botão que FECHA sem agir. O default serve a quase tudo, mas há
   * casos em que «Cancelar» ao lado de «Cancelar assinatura» diz duas coisas
   * opostas com a mesma palavra — ali passe o que a pessoa está escolhendo
   * («Manter plano»).
   */
  cancelLabel?: string
  /**
   * O nome do `X` para leitor de tela, repassado ao `DialogContent`. Sem ele, o
   * "Fechar" de sempre; a Home, que fala três idiomas, passa o do idioma dela.
   */
  closeLabel?: string
  /**
   * Classe do `DialogContent`. A Home abre este diálogo sobre uma tela quase
   * preta e passa `home-portal` (o conteúdo é portado ao <body>, fora da árvore
   * que declara a paleta dela); os diálogos de ação passam a largura.
   */
  className?: string
}

// Dialog de confirmação de exclusão genérico.
//
// O estado de "excluindo" é INTERNO de propósito: os consumidores só entregam um
// `onConfirm` (que pode ser async) e ganham a trava de graça, sem mudar assinatura.
// Sem ela, duplo clique em "Excluir" disparava dois DELETEs — e como as ações de
// exclusão removem o item da lista otimistamente, o segundo request batia num
// recurso já removido.
export function DeleteDialog({ onConfirm, className, closeLabel, ...resto }: DeleteDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  // Ref e não só estado: o Enter do campo e o clique podem chegar no mesmo
  // tique, antes de o "excluindo" ser desenhado.
  const emVoo = useRef(false)

  async function handleConfirm() {
    if (emVoo.current) return
    emVoo.current = true
    setIsDeleting(true)
    try {
      await onConfirm()
    } finally {
      // Se o onConfirm fechou o diálogo, este setState cai num componente
      // desmontado e o React ignora; se ele falhou, o botão volta a funcionar.
      emVoo.current = false
      setIsDeleting(false)
    }
  }

  return (
    // Fechar no meio da exclusão deixa o usuário sem saber se ela aconteceu:
    // `bloqueado` trava as três saídas (Esc, clique-fora e o X).
    <DialogContent className={className} bloqueado={isDeleting} closeLabel={closeLabel}>
      <Confirmacao {...resto} isDeleting={isDeleting} onConfirmar={handleConfirm} />
    </DialogContent>
  )
}

/**
 * O miolo do diálogo, montado DENTRO do portal: desmonta quando o diálogo fecha,
 * e o que foi digitado não sobrevive a uma reabertura. O `DeleteDialog` em si
 * continua montado quando quem o usa o deixa dentro de um `Dialog` fechado — é o
 * caso dos diálogos abertos por um item de menu.
 */
function Confirmacao({
  title, description, note, children, confirmarDigitando, rotuloDigitando,
  isDeleting, onConfirmar,
  cancelLabel = "Cancelar",
  confirmLabel = "Excluir",
  loadingLabel = confirmLabel === "Excluir" ? "Excluindo…" : `${confirmLabel}…`,
}: Omit<DeleteDialogProps, "onConfirm" | "className" | "closeLabel"> & {
  isDeleting: boolean
  onConfirmar: () => void
}) {
  const [digitado, setDigitado] = useState("")
  const campoId = useId()
  const liberado = confirmarDigitando === undefined || digitado === confirmarDigitando

  function confirmar() {
    if (liberado) onConfirmar()
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>
      {note && (
        <p className="-mt-1 text-xs text-muted-foreground">{note}</p>
      )}
      {children}
      {confirmarDigitando !== undefined && (
        <div className="grid gap-1.5">
          {rotuloDigitando && <Label htmlFor={campoId}>{rotuloDigitando}</Label>}
          <Input
            id={campoId}
            value={digitado}
            onChange={e => setDigitado(e.target.value)}
            // `repeat`: segurar o Enter não pode virar uma segunda confirmação
            // quando a primeira volta com o 409 do «mesmo assim».
            onKeyDown={e => { if (e.key === "Enter" && !e.repeat) confirmar() }}
            placeholder={confirmarDigitando}
            autoComplete="off"
            // Só leitura, e não `disabled`: o navegador tira o foco de um campo
            // desabilitado, e depois de uma falha (ou do 409) o Enter não fazia
            // nada até a pessoa clicar de volta nele. O Enter no meio da ação
            // cai na trava de `handleConfirm`.
            readOnly={isDeleting}
            className="max-md:h-10"
          />
        </div>
      )}
      <DialogFooter>
        <DialogClose asChild>
          <Button variant="outline" disabled={isDeleting} className="max-md:h-10">{cancelLabel}</Button>
        </DialogClose>
        <Button onClick={confirmar} variant="destructive" disabled={isDeleting || !liberado} className="gap-1 max-md:h-10">
          {isDeleting && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
          {isDeleting ? loadingLabel : confirmLabel}
        </Button>
      </DialogFooter>
    </>
  )
}
