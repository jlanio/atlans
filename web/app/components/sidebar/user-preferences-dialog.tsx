"use client"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog"
import { Separator } from "@/app/components/ui/separator"
import { Avatar, AvatarFallback } from "@/app/components/ui/avatar"
import { TbMoon, TbSun, TbUser, TbPalette, TbLanguage } from "react-icons/tb"
import { useTheme } from "@/context/ThemeContext"
import { useIdioma } from "@/context/IdiomaContext"
import { useSession } from "next-auth/react"
import { cn } from "@/lib/utils"
import { IDIOMAS, NOME_DO_IDIOMA, type Idioma } from "@/lib/idioma"
import { useTextosDaCasca } from "../home/i18n/da-casca"

interface UserPreferencesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** A Home passa `home-portal`: o conteúdo é portado ao <body>, fora da paleta dela. */
  className?: string
}

export function UserPreferencesDialog({ open, onOpenChange, className }: UserPreferencesDialogProps) {
  const { theme, setTheme } = useTheme()
  const { detectado, escolhido, escolher } = useIdioma()
  const { data: session } = useSession()
  const textos = useTextosDaCasca()
  const t = textos.casca.preferencias

  const username = session?.user?.username ?? textos.casca.conta.usuario
  const email    = session?.user?.email ?? "—"
  const role     = session?.user?.role ?? "user"
  const initials = username.slice(0, 2).toUpperCase()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn("max-w-md", className)} closeLabel={textos.comum.fechar}>
        <DialogHeader>
          <DialogTitle>{t.titulo}</DialogTitle>
        </DialogHeader>

        {/* ── Conta ─────────────────────────────────────────────────────── */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <TbUser size={13} />
            {t.conta}
          </div>

          <div className="flex items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
            <Avatar className="h-10 w-10 rounded-lg shrink-0">
              <AvatarFallback className="rounded-lg text-sm font-semibold">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{username}</p>
              <p className="text-xs text-muted-foreground truncate">{email}</p>
              <p className="text-[11px] text-muted-foreground/60 capitalize mt-0.5">{role}</p>
            </div>
          </div>
        </section>

        <Separator />

        {/* ── Aparência ─────────────────────────────────────────────────── */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            <TbPalette size={13} />
            {t.aparencia}
          </div>

          <div className="grid grid-cols-2 gap-2">
            {/* Tema claro */}
            <button
              onClick={() => setTheme("light")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border-2 p-3 transition-colors",
                theme === "light"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:bg-accent/50"
              )}
            >
              {/* Preview */}
              <div className="w-full rounded-md border bg-white overflow-hidden shadow-sm">
                <div className="h-2 bg-secondary border-b" />
                <div className="flex gap-1 p-1.5">
                  <div className="h-4 w-2/3 rounded bg-muted" />
                  <div className="h-4 w-1/3 rounded bg-secondary" />
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <TbSun size={13} className={theme === "light" ? "text-primary" : "text-muted-foreground"} />
                <span className={theme === "light" ? "text-primary" : "text-muted-foreground"}>{t.claro}</span>
              </div>
            </button>

            {/* Tema escuro */}
            <button
              onClick={() => setTheme("dark")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border-2 p-3 transition-colors",
                theme === "dark"
                  ? "border-primary bg-primary/5"
                  : "border-border hover:bg-accent/50"
              )}
            >
              {/* Preview */}
              <div className="w-full rounded-md border border-zinc-700 bg-zinc-900 overflow-hidden shadow-sm">
                <div className="h-2 bg-zinc-800 border-b border-zinc-700" />
                <div className="flex gap-1 p-1.5">
                  <div className="h-4 w-2/3 rounded bg-zinc-700" />
                  <div className="h-4 w-1/3 rounded bg-zinc-800" />
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <TbMoon size={13} className={theme === "dark" ? "text-primary" : "text-muted-foreground"} />
                <span className={theme === "dark" ? "text-primary" : "text-muted-foreground"}>{t.escuro}</span>
              </div>
            </button>
          </div>

          <p className="text-[11px] text-muted-foreground/60">
            {t.salvaAutomaticamente}
          </p>
        </section>

        <Separator />

        {/* ── Idioma ────────────────────────────────────────────────────── */}
        {/* Automático é uma opção de verdade, e não a ausência de escolha: é o
            único caminho de volta para quem escolheu um idioma e quer que a
            Home volte a seguir o navegador. Cada idioma aparece no próprio
            nome ("English", "Español") — é assim que quem não lê português o
            encontra numa lista. */}
        <section className="space-y-3">
          <div
            id="preferencias-idioma"
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground"
          >
            <TbLanguage size={13} />
            {t.idioma}
          </div>

          <div role="group" aria-labelledby="preferencias-idioma" className="grid grid-cols-2 gap-2">
            <OpcaoDeIdioma
              marcada={escolhido === null}
              onEscolher={() => escolher(null)}
              rotulo={t.automatico}
              detalhe={t.detectado(NOME_DO_IDIOMA[detectado])}
            />
            {IDIOMAS.map((idioma: Idioma) => (
              <OpcaoDeIdioma
                key={idioma}
                marcada={escolhido === idioma}
                onEscolher={() => escolher(idioma)}
                rotulo={NOME_DO_IDIOMA[idioma]}
                lang={idioma}
              />
            ))}
          </div>

          <p className="text-[11px] text-muted-foreground/60">
            {t.notaDoIdioma}
          </p>
        </section>

      </DialogContent>
    </Dialog>
  )
}

function OpcaoDeIdioma({
  marcada,
  onEscolher,
  rotulo,
  detalhe,
  lang,
}: {
  marcada: boolean
  onEscolher: () => void
  rotulo: string
  detalhe?: string
  /** O nome do idioma no próprio idioma: o leitor de tela o pronuncia certo. */
  lang?: string
}) {
  return (
    <button
      type="button"
      aria-pressed={marcada}
      onClick={onEscolher}
      className={cn(
        "flex flex-col items-start gap-0.5 rounded-lg border-2 px-3 py-2 text-left transition-colors",
        marcada ? "border-primary bg-primary/5" : "border-border hover:bg-accent/50",
      )}
    >
      <span lang={lang} className={cn("text-xs font-medium", marcada ? "text-primary" : "text-foreground")}>
        {rotulo}
      </span>
      {detalhe && <span className="text-[11px] text-muted-foreground">{detalhe}</span>}
    </button>
  )
}
