"use client";

import { useState } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { usePathname, useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import { TbCheck, TbChevronDown, TbCrown, TbHome, TbPlus, TbSettings, TbUserCheck } from "react-icons/tb";
import { cn } from "@/lib/utils";
import { useSession } from "next-auth/react";
import { WorkspaceBadge } from "./workspace-badge";
import { roleLabel } from "./role-labels";

export default function WorkspaceSwitcher() {
  const { workspaces, current, setCurrent } = useWorkspace();
  const { data: session } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const userId = session?.user?.id_hash ?? null;
  // Mesma regra do WorkspaceBadge: `my_role` distingue os cinco papéis, e a
  // comparação por `owner_id` fica como reserva. Sem isso, um admin de um
  // workspace compartilhado aparecia como "Convidado" em todas as linhas.
  function papelDe(ws: { my_role: string | null; owner_id: string | null }) {
    const dono =
      ws.my_role === "owner" || !!(ws.owner_id && userId && ws.owner_id === userId);
    return {
      dono,
      rotulo: dono ? "Proprietário" : ws.my_role ? roleLabel(ws.my_role) : "Convidado",
    };
  }

  // Ao selecionar um workspace no dropdown, redireciona para /projects.
  // Objetivo: mostrar imediatamente os workflows do workspace novo — evita
  // que o usuario troque estando em /observability e nao veja mudanca visivel
  // alem do header. Se ja estava em /projects, o router.push nao muda a URL mas
  // o useEffect da lista re-fetcha via dependencia em current.id_hash
  // (projects/index.tsx:127).
  //
  // /workflow/[id] nao entra mais nessa lista: la o cabecalho nao e renderizado
  // (ver FULLSCREEN_ROUTES em app-header) e este seletor nao esta montado. Quem
  // precisa trocar sai do editor — trocar no meio de uma edicao a descartaria.
  //
  // A excecao e /workspaces: la a troca JA tem efeito visivel (o card ativo
  // muda), e quem esta configurando um workspace era jogado para fora da tela
  // no meio da tarefa. A Home (/) e o mesmo caso: a lista de Artefatos re-escopa
  // por current.id_hash na hora, entao empurrar para /projects tiraria a pessoa
  // do globo sem ganho — a mudanca ja aparece onde ela esta.
  const handleSelect = (wsId: string) => {
    const ws = workspaces.find((w) => w.id_hash === wsId);
    if (!ws) return;
    setCurrent(ws);
    setOpen(false);
    if (pathname !== "/workspaces" && pathname !== "/") router.push("/projects");
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        {/* Botão comum, não `SidebarMenuButton`: o seletor saiu da sidebar e
            agora vive no cabeçalho, onde o primitivo da sidebar traria largura
            total e altura de item de menu. */}
        <button
          type="button"
          // O nome do workspace vem do WorkspaceBadge, mas `aria-label` no botão
          // SUBSTITUI o conteúdo no cálculo do nome acessível: com um rótulo
          // fixo, quem usa leitor de tela ouvia "clique para trocar" e nunca
          // qual workspace estava ativo — a única coisa que este cabeçalho
          // existe para dizer.
          aria-label={
            current
              ? `Workspace ativo: ${current.name}. Clique para trocar.`
              : "Nenhum workspace ativo. Clique para escolher."
          }
          // `app-region-no-drag`: no app desktop o AppHeader arrasta a janela;
          // este botão precisa seguir clicável. Sem efeito no navegador.
          className="app-region-no-drag flex min-w-0 max-w-xs items-center gap-2 rounded-md px-2 py-1 text-left transition-colors hover:bg-accent focus-visible:ring-ring data-[state=open]:bg-accent focus-visible:ring-2 focus-visible:outline-none"
        >
          {/* Chip de identidade LIGADO: a cor determinística do workspace é o
              sinal mais rápido de "em que escopo estou" — e este cabeçalho
              existe justamente para responder isso antes de uma ação
              destrutiva. Antes ficava desligado por parecer redundante ao lado
              do nome; a cor, porém, é reconhecível num relance que o texto não. */}
          <WorkspaceBadge
            workspace={current}
            size="md"
            showName
            showRole
            showAvatar
            currentUserId={userId}
            className="min-w-0"
          />
          <TbChevronDown className="size-4 shrink-0 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        // Largura própria, não a do gatilho: no cabeçalho o botão encolhe até o
        // nome do workspace, e amarrar o menu a ele espremia a lista a ponto de
        // cortar os nomes. Cresce com o conteúdo até um teto que ainda cabe na
        // tela do telefone.
        // O mínimo também cede na tela estreita: `min-width` vence `max-width`,
        // então um `min-w-72` cru estouraria de novo abaixo de ~312px.
        className="min-w-[min(18rem,calc(100vw-1.5rem))] max-w-[min(24rem,calc(100vw-1.5rem))] rounded-lg"
        align="start"
        sideOffset={4}
        // Sem folga de colisão o menu encostava na borda do telefone e comia o
        // próprio padding — o papel do último workspace ficava cortado na tela.
        collisionPadding={12}
      >
        <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Workspaces
        </DropdownMenuLabel>

        {workspaces.map((ws) => {
          const isActive = current?.id_hash === ws.id_hash;
          const papel = papelDe(ws);
          return (
            <DropdownMenuItem
              key={ws.id_hash}
              onSelect={() => handleSelect(ws.id_hash)}
              // `data-active` não era lido por CSS nenhum: o workspace ativo
              // não tinha marca alguma na lista. Marca agora com superfície,
              // peso, um check E a barra terracota à esquerda — o mesmo idioma
              // de "atual" do item ativo da sidebar A.
              className={cn(
                "gap-2",
                isActive &&
                  "bg-accent font-medium before:absolute before:left-1 before:top-1/2 before:h-4 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-primary before:content-['']",
              )}
            >
              <WorkspaceBadge workspace={ws} size="sm" />
              {/* `truncate` precisa ficar no elemento que contém o TEXTO: no
                  contêiner flex ele não recorta nada, e o nome longo avançava
                  por cima do check e do papel em vez de virar reticências. */}
              <span className="flex min-w-0 flex-1 items-center gap-1">
                {ws.is_default && <TbHome className="size-3 shrink-0 text-muted-foreground" />}
                <span className="truncate">{ws.name}</span>
              </span>
              {isActive && <TbCheck className="size-3.5 shrink-0 text-primary" />}
              <span className={`flex shrink-0 items-center gap-0.5 text-xs ${
                papel.dono ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground"
              }`}>
                {papel.dono ? <TbCrown className="size-3" /> : <TbUserCheck className="size-3" />}
                {papel.rotulo}
              </span>
            </DropdownMenuItem>
          );
        })}

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="group/act gap-2"
          onSelect={() => { router.push("/workspaces"); setOpen(false); }}
        >
          <div className="flex size-6 items-center justify-center rounded-md border bg-background transition-colors group-hover/act:border-primary/50">
            <TbSettings className="size-4 text-muted-foreground transition-colors group-hover/act:text-primary" />
          </div>
          <span>Gerenciar workspaces</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          className="group/act gap-2"
          onSelect={() => { router.push("/workspaces?new=1"); setOpen(false); }}
        >
          <div className="flex size-6 items-center justify-center rounded-md border bg-background transition-colors group-hover/act:border-primary/50">
            <TbPlus className="size-4 text-muted-foreground transition-colors group-hover/act:text-primary" />
          </div>
          <span>Novo workspace</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
