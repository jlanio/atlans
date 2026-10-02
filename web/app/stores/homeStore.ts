import { create } from "zustand"
import type { ModoDeEntrada } from "@/lib/entrada"
import type { UploadErrorType } from "@/app/components/drive/resultado-upload"

/**
 * Estado da Home partilhado pela casca (Chats no HomeSidebar), pelo painel
 * flutuante e pelo globo. Numa store porque esses três não têm ancestral comum
 * barato — o HomeSidebar é irmão do painel na árvore da casca, e o atalho de
 * teclado vive num efeito global.
 *
 * - `conversaId`: a conversa ativa (destacada nos Chats; o painel a abre). Fica
 *   em memória — a seleção é da sessão, não uma preferência a lembrar.
 * - `painel`: "aberto" (a conversa flutuante na lateral) ou "barra" (a barra de
 *   comando, com a última troca da conversa ao centro). Começa em "barra" em
 *   TODO acesso — o painel é sob demanda (Ctrl+I, o chevron, "Expandir") — e
 *   não é gravado: a preferência saiu junto com o hero do primeiro acesso, que
 *   ignoraria qualquer estado lembrado.
 * - `pedidosDeCamada`: uma FILA de pedidos "põe este artefato no globo", escrita
 *   pela lista de Artefatos (no HomeSidebar) e drenada pelo HomeView, que é quem
 *   tem o `useCamadas`. Fila, não um slot só, para não perder cliques rápidos em
 *   artefatos diferentes; o HomeView consome só o que despachou. O estado das
 *   camadas em si vive no `useCamadas` (no HomeView) — a store só carrega o
 *   PEDIDO de um irmão da árvore para o outro, que não têm ancestral comum barato.
 * - `decididos`: as confirmações já clicadas. Fica AQUI, e não no painel, porque
 *   recolher o painel o desmonta e os turnos (com o token) sobrevivem: guardar a
 *   decisão no componente deixava o cartão de novo clicável ao reabrir, e o
 *   segundo clique bate num token já consumido (409).
 * - `expirados`: as confirmações que o servidor recusou com 409 (chave já
 *   consumida ou vencida). Continuam decididas — não há o que refazer —, só que
 *   o cartão troca "Decidido." pela microcópia que explica o porquê.
 * - `rascunho`: o texto em edição do assistente, partilhado pelo painel e pela
 *   barra. Fica AQUI porque Ctrl+I troca um pelo outro e DESMONTA quem estava na
 *   tela: num `useState` de cada caixa, o atalho apagava o que já tinha sido
 *   digitado. Em memória — rascunho é da sessão, não preferência a gravar.
 * - `meu`: quais itens do grupo Meu do HomeSidebar (Agendamentos, Artefatos,
 *   Chats) estão abertos. Persiste em `atlans:home:meu` porque, num `useState`
 *   do item, o aberto/fechado morria a cada abertura da gaveta no telefone (o
 *   Sheet desmonta os filhos ao fechar), ao sair de `/` e voltar (a casca troca
 *   de sidebar) e ao cruzar 768px — e a pessoa reabria tudo de novo.
 * - `anuncioDeConversa`: o último "esta conversa ganhou atividade" que o stream
 *   do assistente anunciou — o 1º quadro `conversa` de cada mensagem (id,
 *   título, se é nova) e a confirmação aceita. A lista de Chats mora no
 *   HomeSidebar, IRMÃO do HomeView: é por aqui que ela fica sabendo, sem GET.
 *   É um SLOT, e não uma fila como `pedidosDeCamada`: a lista pode estar
 *   desmontada (a gaveta do telefone fechada) e uma fila cresceria sem ninguém
 *   para drená-la. O slot guarda um objeto NOVO a cada anúncio, e a lista
 *   compara identidade com o que já existia quando montou — a carga de
 *   montagem traz a verdade. Em memória.
 * - `entrada`: o modal de entrada (login/cadastro) pedido — pela barra, no
 *   primeiro envio sem sessão, ou pelos botões Entrar/Criar conta do
 *   HomeSidebar, irmão do HomeView na árvore (o mesmo motivo de
 *   `pedidosDeCamada`). `null` = fechado. Em memória.
 * - `envioPendente`: a mensagem que o primeiro envio sem sessão deixou
 *   esperando o login — o HomeView a manda sozinho quando a sessão chega.
 *   Fechar o modal sem entrar a descarta (o texto continua em `rascunho`, à
 *   vista na barra); concluir a entrada a mantém. Em memória: disparar num F5
 *   uma mensagem guardada seria surpresa.
 * - `anexos` e `arrastandoArquivo`: os arquivos soltos sobre a Home, a caminho
 *   do Drive do workspace. Ficam AQUI pelo mesmo motivo do `rascunho`: Ctrl+I
 *   troca a barra pelo painel e DESMONTA quem estava na tela — num `useState`
 *   da caixa, os chips (e o `arrastando` que acende a caixa) sumiam no atalho,
 *   enquanto os uploads seguiam correndo sem nada na tela. Em memória: um F5
 *   perde o `File` de qualquer jeito, e o que já subiu está no Drive.
 */

const CHAVE_MEU = "atlans:home:meu"

type Painel = "aberto" | "barra"

/** Os três itens do grupo Meu, na ordem em que aparecem na barra. */
export type ItemDoMeu = "agendamentos" | "artefatos" | "chats"
export type EstadoDoMeu = Record<ItemDoMeu, boolean>
/** O de sempre: só Chats nasce aberto. Também é o default do SSR. */
export const MEU_PADRAO: EstadoDoMeu = { agendamentos: false, artefatos: false, chats: true }

/** Um pedido para exibir um artefato no globo. `nome` é o rótulo sugerido. */
export interface PedidoDeCamada {
  artifactId: string
  nome?: string
}

/**
 * "Esta conversa ganhou atividade": o 1º quadro `conversa` de cada mensagem
 * (id, título, se acabou de nascer) ou uma confirmação aceita (só o id). A
 * mesma forma do `info` do `onConversa` do `useAssistente`.
 */
export interface AnuncioDeConversa {
  id: string
  titulo?: string
  nova: boolean
}

/** Onde um arquivo solto sobre a Home está na viagem até o Drive. */
export type EstadoDoAnexo = "enviando" | "pronto" | "recusado"

/**
 * Um arquivo solto sobre a Home.
 *
 * `recusado` é sempre veredito do SERVIDOR — os filtros do Drive (extensão
 * permitida, extensão interna perigosa, teto em MB, arquivo vazio, papel no
 * workspace) vivem todos lá, e o cliente não os reescreve. `motivo` é o texto
 * que o servidor devolveu e `tipo` é a classificação de `classifyUploadError`,
 * a mesma da tela `/drive` — por isso os dois rótulos nunca divergem.
 */
export interface Anexo {
  /** Chave de render. Não é o id do Drive: o arquivo pode nem chegar lá. */
  id: string
  nome: string
  bytes: number
  estado: EstadoDoAnexo
  /** O detalhe que o servidor devolveu, quando `recusado`. */
  motivo?: string
  tipo?: UploadErrorType
}

/**
 * A ÚLTIMA posição conhecida da pessoa, vinda do controle do MapLibre no globo
 * (o evento `geolocate`). Fica na store pelo mesmo motivo do `rascunho`: o chip
 * que a mostra vive nos DOIS compositores (barra e painel), e Ctrl+I desmonta
 * quem está na tela. Em memória — é a posição física da sessão, não preferência
 * a gravar, e um F5 relocaliza. As chaves espelham o corpo que o backend recebe.
 *
 * Posição e INTENÇÃO são estados separados de propósito: o globo escreve a
 * posição a cada tick do seguir, mas ela só vai ao turno do assistente quando
 * `compartilharLocalizacao` está ligado — o que SÓ um gesto da pessoa liga
 * ("Usar minha localização" no "+") e o × do chip desliga. Sem a separação, o
 * próximo tick de GPS desfazia o × sozinho e a coordenada voltava ao turno sem
 * gesto nenhum (achado da revisão adversarial de 2026-09-24).
 */
export interface Localizacao {
  lat: number
  lon: number
  /** Raio de precisão em metros (o `accuracy` do navegador); `null` se ausente. */
  precisao_m: number | null
}

/**
 * Lê o grupo Meu lembrado. Começa do padrão e só copia as chaves cujo valor é
 * booleano: um JSON parcial (versão antiga), corrompido ou com lixo não quebra
 * nada — cai no padrão chave a chave.
 */
function meuLembrado(): EstadoDoMeu | null {
  if (typeof window === "undefined") return null
  try {
    const cru = window.localStorage.getItem(CHAVE_MEU)
    if (!cru) return null
    const lido: unknown = JSON.parse(cru)
    if (!lido || typeof lido !== "object") return null
    const meu = { ...MEU_PADRAO }
    for (const nome of Object.keys(MEU_PADRAO) as ItemDoMeu[]) {
      const valor = (lido as Record<string, unknown>)[nome]
      if (typeof valor === "boolean") meu[nome] = valor
    }
    return meu
  } catch {
    return null
  }
}

function lembrarMeu(meu: EstadoDoMeu): void {
  try {
    window.localStorage.setItem(CHAVE_MEU, JSON.stringify(meu))
  } catch {
    /* preferência descartável */
  }
}

interface HomeState {
  conversaId: string | null
  painel: Painel
  /** Falso até o efeito de hidratação rodar — antes disso, só o default do SSR. */
  hidratado: boolean
  /** Pedidos pendentes de "exibir no globo", drenados pelo HomeView. */
  pedidosDeCamada: PedidoDeCamada[]
  /** `tool_use_id` → decidido. Sobrevive a recolher/reabrir o painel. */
  decididos: Record<string, true>
  /** `tool_use_id` → o servidor respondeu 409: decidido, porém sem efeito. */
  expirados: Record<string, true>
  /** O texto em edição, partilhado pelo painel e pela barra. */
  rascunho: string
  /** Aberto/fechado de cada item do grupo Meu. Persiste em `atlans:home:meu`. */
  meu: EstadoDoMeu
  /** O último anúncio do stream; `null` até a primeira mensagem. Ver o cabeçalho. */
  anuncioDeConversa: AnuncioDeConversa | null
  /** O modal de entrada pedido (login ou cadastro); `null` = fechado. */
  entrada: ModoDeEntrada | null
  /** A mensagem do primeiro envio sem sessão, esperando o login. */
  envioPendente: string | null
  /** Os arquivos soltos sobre a Home, na ordem em que chegaram. */
  anexos: Anexo[]
  /** Há um arraste COM ARQUIVOS sobre a Home: a caixa acende e convida. */
  arrastandoArquivo: boolean
  /** A ÚLTIMA posição conhecida (do globo); só vai ao turno com `compartilharLocalizacao`. */
  localizacao: Localizacao | null
  /** A pessoa PEDIU para a localização ir na conversa ("+ → Usar minha localização"); o × desliga. */
  compartilharLocalizacao: boolean
}

interface HomeActions {
  selecionarConversa(id: string | null): void
  /** Começa uma conversa nova: limpa a seleção. A superfície fica como está. */
  novaConversa(): void
  abrirPainel(): void
  /** Recolhe o painel à barra (a conversa volta ao centro). */
  recolherBarra(): void
  alternarPainel(): void
  /**
   * Marca o fim do SSR (a partir daqui a troca de superfície devolve o foco) e
   * lê o grupo Meu lembrado no navegador. NÃO grava.
   */
  hidratar(): void
  /** Enfileira um artefato para o globo (da lista de Artefatos, no sidebar). */
  pedirCamada(artifactId: string, nome?: string): void
  /**
   * Tira da frente da fila os `n` pedidos já despachados. Não é `limparFila`:
   * um clique que caia entre o render do HomeView e o efeito dele seria apagado
   * sem nunca ter ido ao globo — o artefato simplesmente não apareceria.
   */
  consumirFila(n: number): void
  /** Marca uma confirmação como decidida (o cartão trava). */
  marcarDecidido(toolUseId: string): void
  /** Devolve o cartão ao estado clicável — a confirmação falhou no servidor. */
  desmarcarDecidido(toolUseId: string): void
  /**
   * A chave já tinha sido consumida (ou venceu) quando o clique chegou: o
   * cartão CONTINUA travado — refazer só renderia outro 409 —, e a microcópia
   * passa a dizer o porquê.
   */
  marcarExpirado(toolUseId: string): void
  /** Guarda o texto em edição (painel e barra escrevem no mesmo rascunho). */
  definirRascunho(texto: string): void
  /** Abre/fecha um item do grupo Meu e lembra a preferência. */
  alternarItemDoMeu(nome: ItemDoMeu): void
  /** Abre um item do grupo Meu (idempotente) — o clique no trilho de 3rem usa. */
  abrirItemDoMeu(nome: ItemDoMeu): void
  /** Registra um anúncio. Sempre um objeto novo: a identidade é o contrato. */
  anunciarConversa(anuncio: AnuncioDeConversa): void
  /** Abre o modal de entrada no modo pedido (a barra e o sidebar pedem). */
  pedirEntrada(modo: ModoDeEntrada): void
  /**
   * Fecha o modal SEM entrar (Esc, X, clique fora): desiste do envio pendente
   * — um login mais tarde não pode disparar uma mensagem esquecida. O texto
   * continua em `rascunho`.
   */
  fecharEntrada(): void
  /** O login deu certo: fecha o modal e MANTÉM o envio pendente para o HomeView mandar. */
  concluirEntrada(): void
  definirEnvioPendente(texto: string | null): void
  /** Um arraste com arquivos entrou na Home (ou saiu dela). */
  definirArrastandoArquivo(arrastando: boolean): void
  /** Enfileira os arquivos recém-soltos, já em `enviando`. */
  adicionarAnexos(novos: Anexo[]): void
  /** O upload de um anexo terminou (ou foi recusado): corrige a linha dele. */
  atualizarAnexo(id: string, mudanca: Partial<Omit<Anexo, "id">>): void
  /** O × do chip. Não apaga nada do Drive — só tira da barra. */
  removerAnexo(id: string): void
  /**
   * A mensagem foi enviada: os PRONTOS saem (a referência a eles já viajou
   * junto). Os que ainda sobem ficam, porque não estavam na mensagem; os
   * recusados também, porque nunca tiveram nada a ver com ela e a pessoa ainda
   * precisa ler o motivo.
   */
  limparAnexosProntos(): void
  /** Fecha o aviso dos recusados. */
  descartarAnexosRecusados(): void
  /**
   * Esvazia a lista inteira — usado quando o WORKSPACE ativo muda: os anexos
   * são "o que acabei de mandar ao Drive DESTE workspace", e a referência da
   * mensagem (`comReferencia`) casa com o workspace da conversa. Trocado o
   * workspace, os chips passariam a apontar para arquivos que estão noutro
   * Drive — o assistente do novo workspace não os acha.
   */
  limparAnexos(): void
  /** Guarda a última posição conhecida (do evento `geolocate` do globo). NÃO liga o compartilhar. */
  definirLocalizacao(loc: Localizacao): void
  /** O gesto do "+": a localização passa a ir nos turnos. */
  ligarLocalizacao(): void
  /**
   * O × do chip: a localização SAI da conversa e FICA fora — os ticks do seguir
   * continuam atualizando a posição, mas nada volta ao turno até um novo gesto.
   * Não desliga o seguir no globo e não apaga a última posição (religar pelo
   * "+" volta na hora, sem esperar novo fix de GPS).
   */
  limparLocalizacao(): void
}

export const useHomeStore = create<HomeState & HomeActions>((set) => ({
  conversaId: null,
  painel: "barra",
  hidratado: false,
  pedidosDeCamada: [],
  decididos: {},
  expirados: {},
  rascunho: "",
  meu: MEU_PADRAO,
  anuncioDeConversa: null,
  entrada: null,
  envioPendente: null,
  anexos: [],
  arrastandoArquivo: false,
  localizacao: null,
  compartilharLocalizacao: false,

  // A conversa que troca leva junto as decisões: os tokens são de turnos que
  // saíram da tela. Um id NOVO vindo do stream (nula → id) é a MESMA conversa,
  // mas aí não há decisão anterior a perder. O rascunho FICA: é o que a pessoa
  // acabou de digitar, e sumir com ele por trocar de chat é perder texto dela.
  selecionarConversa: (id) =>
    set((state) => (state.conversaId === id ? {} : { conversaId: id, decididos: {}, expirados: {} })),
  novaConversa: () => set(() => ({ conversaId: null, decididos: {}, expirados: {} })),

  abrirPainel: () => set(() => ({ painel: "aberto" })),
  recolherBarra: () => set(() => ({ painel: "barra" })),
  alternarPainel: () => set((state) => ({ painel: state.painel === "aberto" ? "barra" : "aberto" })),

  // Lê o grupo Meu lembrado no navegador. NÃO grava: só o gesto da pessoa
  // grava. O `painel` não entra: começa em "barra" em todo acesso (o hero).
  hidratar: () => set(() => ({ meu: meuLembrado() ?? MEU_PADRAO, hidratado: true })),

  pedirCamada: (artifactId, nome) =>
    set((state) => ({ pedidosDeCamada: [...state.pedidosDeCamada, { artifactId, nome }] })),
  consumirFila: (n) =>
    set((state) => (n <= 0 ? {} : { pedidosDeCamada: state.pedidosDeCamada.slice(n) })),

  marcarDecidido: (toolUseId) =>
    set((state) => ({ decididos: { ...state.decididos, [toolUseId]: true } })),
  desmarcarDecidido: (toolUseId) =>
    set((state) => {
      if (!(toolUseId in state.decididos)) return {}
      const copia = { ...state.decididos }
      delete copia[toolUseId]
      return { decididos: copia }
    }),
  marcarExpirado: (toolUseId) =>
    set((state) => ({
      decididos: { ...state.decididos, [toolUseId]: true },
      expirados: { ...state.expirados, [toolUseId]: true },
    })),

  definirRascunho: (texto) => set(() => ({ rascunho: texto })),

  alternarItemDoMeu: (nome) =>
    set((state) => {
      const meu = { ...state.meu, [nome]: !state.meu[nome] }
      lembrarMeu(meu)
      return { meu }
    }),
  abrirItemDoMeu: (nome) =>
    set((state) => {
      if (state.meu[nome]) return {}
      const meu = { ...state.meu, [nome]: true }
      lembrarMeu(meu)
      return { meu }
    }),

  // Sempre um objeto novo, mesmo com o mesmo id: a lista de Chats só reage à
  // troca de identidade, e "a mesma conversa ganhou outra mensagem" É outro
  // anúncio.
  anunciarConversa: (anuncio) => set(() => ({ anuncioDeConversa: { ...anuncio } })),

  pedirEntrada: (modo) => set(() => ({ entrada: modo })),
  fecharEntrada: () => set(() => ({ entrada: null, envioPendente: null })),
  concluirEntrada: () => set(() => ({ entrada: null })),
  definirEnvioPendente: (texto) => set(() => ({ envioPendente: texto })),

  definirArrastandoArquivo: (arrastando) =>
    set((state) => (state.arrastandoArquivo === arrastando ? {} : { arrastandoArquivo: arrastando })),

  adicionarAnexos: (novos) =>
    set((state) => (novos.length === 0 ? {} : { anexos: [...state.anexos, ...novos] })),

  // Por id, e não por índice: os uploads terminam fora de ordem e a pessoa
  // pode remover um chip no meio do caminho.
  atualizarAnexo: (id, mudanca) =>
    set((state) => {
      if (!state.anexos.some((a) => a.id === id)) return {}
      return { anexos: state.anexos.map((a) => (a.id === id ? { ...a, ...mudanca } : a)) }
    }),

  removerAnexo: (id) =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.id !== id)
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  limparAnexosProntos: () =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.estado !== "pronto")
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  descartarAnexosRecusados: () =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.estado !== "recusado")
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  limparAnexos: () => set((state) => (state.anexos.length === 0 ? {} : { anexos: [] })),

  // O `geolocate` do globo dispara a cada atualização de posição (o modo
  // seguir). Histerese de ~25 m (0,00025° ≈ 25 m no equador): o jitter de GPS
  // de quem está PARADO não troca o valor — o que estabiliza o texto que vai ao
  // prompt entre turnos (senão cada mensagem invalidava o cache do histórico) e
  // poupa re-render do chip —, e um deslocamento real atualiza normalmente. Uma
  // melhora franca de precisão também passa (o primeiro fix grosseiro do IP/wifi
  // vira o fino do GPS mesmo sem sair do lugar).
  definirLocalizacao: (loc) =>
    set((state) => {
      const a = state.localizacao
      if (a) {
        const parado = Math.abs(a.lat - loc.lat) < 0.00025 && Math.abs(a.lon - loc.lon) < 0.00025
        const precisaoMelhorou =
          loc.precisao_m != null && (a.precisao_m == null || loc.precisao_m < a.precisao_m / 2)
        if (parado && !precisaoMelhorou) return {}
      }
      return { localizacao: loc }
    }),
  ligarLocalizacao: () => set((s) => (s.compartilharLocalizacao ? {} : { compartilharLocalizacao: true })),
  // Desliga SÓ a intenção: a posição fica como última conhecida. É o que faz o
  // × persistir — antes, com o valor zerado, o próximo tick do seguir regravava
  // e o chip ressuscitava sozinho.
  limparLocalizacao: () => set((s) => (s.compartilharLocalizacao ? { compartilharLocalizacao: false } : {})),
}))
