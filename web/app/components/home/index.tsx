"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import { TbAlertTriangle, TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"
import { usePrefereMenosMovimento } from "@/app/hooks/usePrefereMenosMovimento"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useIsMobile } from "@/hooks/use-mobile"
import { useHomeStore } from "@/app/stores/homeStore"
import { useAssistente } from "@/app/hooks/home/useAssistente"
import { useAnexos } from "@/app/hooks/home/useAnexos"
import { useArrasteDeArquivos } from "@/app/hooks/home/useArrasteDeArquivos"
import { useCamadas } from "@/app/hooks/home/useCamadas"
import Globo from "./globo"
import Painel from "./assistente/painel"
import Barra from "./assistente/barra"
import { etapaDaConversa } from "./assistente/etapa"
import Pilha from "./assistente/pilha"
import PainelCamadas from "./painel-camadas"
import ModalDeEntrada from "./entrada/modal-de-entrada"
import { ehPainelDeEmail, type ModoDeEntrada } from "@/lib/entrada"
import { baixarArtefato } from "@/lib/baixar-artefato"
import { createToast } from "@/utils/createToast"
import { useIdiomaDaTela, useTextos } from "./i18n"

/** A barra leva 900 ms do centro ao rodapé e o véu 15% a mais (globals.css). */
export const DURACAO_DA_TRANSICAO_MS = 1050
/** A faixa e a barra saindo quando o painel abre: `--home-dur × .33` (globals.css). */
export const SAIDA_MS = 300

/**
 * A Home: o globo em tela cheia com a conversa flutuante sobre ele. `className=
 * "home dark"` na raiz veste a paleta quase preta (globals.css) e fixa o tema
 * escuro — a Home é SEMPRE escura, independente do tema do app. É full-bleed
 * `h-svh` como o canvas do editor; o AppHeader devolve null em `/`.
 *
 * Esta raiz é `relative` E é o quadro de referência das superfícies flutuantes
 * (painel, barra, camadas), que são `absolute` dentro dela: ela começa depois
 * do sidebar, então nada mais pinta — nem recebe clique — por cima dele.
 *
 * A conversa vive no `useAssistente` (SSE do `/assistente`); as camadas que ela põe no
 * globo, no `useCamadas` (derivadas dos turnos, com o ciclo de vida da conversa
 * ativa).
 *
 * O HERO é o estado inicial de todo acesso: o globo velado rumo ao sul, a barra
 * grande ao centro com sugestões digitadas e chips. Termina no primeiro token
 * visível da primeira resposta — a barra escorrega para o rodapé, o véu some e
 * a última troca da conversa aparece ao centro (a pilha). O painel lateral é
 * sob demanda.
 *
 * SEM SESSÃO a Home abre do mesmo jeito (globo, hero, barra com as sugestões e
 * os chips) e não faz requisição nenhuma: o `useAssistente` não consulta o
 * `/estado` (`anonimo`) e o sidebar não monta as listas. O primeiro envio abre
 * o MODAL DE ENTRADA (`entrada/`) sobre o globo, com a mensagem pendente; o
 * login bem-sucedido troca a sessão da aba sem navegar, o modal fecha e a
 * mensagem vai sozinha — fechar o modal sem entrar desiste dela (o texto fica
 * na barra). `?entrar=1`/`?cadastro=1` (o destino de /login, /register e do
 * middleware) abrem o modal na chegada; `?verificar=1&token=…`,
 * `?recuperar=1` e `?redefinir=1&token=…` (os destinos de /verify-email,
 * /forgot-password e /reset-password) abrem os painéis do e-mail, com sessão
 * ou sem ela; `callbackUrl` leva o admin de volta à página que pediu.
 */
export default function HomeView({
  entrada,
  tokenDoLink,
  callbackUrl,
  paisDaConexao,
}: {
  /** O modal de entrada nasce aberto neste painel (`?entrar=1`, `?redefinir=1`…). */
  entrada?: ModoDeEntrada
  /** O token do link do e-mail (`?redefinir=1&token=…`, `?verificar=1&token=…`). */
  tokenDoLink?: string
  /** Para onde ir depois do login (interno; vem sanitizado da página). */
  callbackUrl?: string
  /** O país da conexão (`CF-IPCountry`): a reserva do globo quando o navegador esconde o fuso. */
  paisDaConexao?: string | null
} = {}) {
  const conversaId = useHomeStore((s) => s.conversaId)
  const painel = useHomeStore((s) => s.painel)
  const hidratado = useHomeStore((s) => s.hidratado)
  const idioma = useIdiomaDaTela()
  const t = useTextos()
  const hidratar = useHomeStore((s) => s.hidratar)
  const alternar = useHomeStore((s) => s.alternarPainel)
  const selecionar = useHomeStore((s) => s.selecionarConversa)
  const pedidosDeCamada = useHomeStore((s) => s.pedidosDeCamada)
  const consumirFila = useHomeStore((s) => s.consumirFila)
  useEffect(() => { hidratar() }, [hidratar])

  // Sem sessão — ou com a sessão vencida, no instante entre este render e o
  // `signOut` do SessionSync — a Home é a anônima: nada aqui pode bater no
  // `/terra` (o /estado sairia sem token, ou com o vencido, e viraria 401). O
  // SessionProvider recebe a sessão do servidor (`null` inclusive), então o
  // status é conhecido já no primeiro render.
  const { data: sessao, status: statusDaSessao } = useSession()
  const anonimo = statusDaSessao === "unauthenticated" || sessao?.error === "RefreshTokenExpired"
  const router = useRouter()
  const entradaPedida = useHomeStore((s) => s.entrada)
  const envioPendente = useHomeStore((s) => s.envioPendente)
  const pedirEntrada = useHomeStore((s) => s.pedirEntrada)
  const fecharEntrada = useHomeStore((s) => s.fecharEntrada)
  const concluirEntrada = useHomeStore((s) => s.concluirEntrada)
  const definirEnvioPendente = useHomeStore((s) => s.definirEnvioPendente)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // A localização: o globo escreve a última posição (aoLocalizar), o "+" liga o
  // compartilhar, o chip mostra e o × desliga. A HomeView NÃO se inscreve na
  // posição — cada tick do modo seguir re-renderizava a árvore inteira (globo,
  // pilha, painel, barra) só para repassar um valor que o useAssistente lê da
  // store na hora do envio. Só ações (estáveis) entram aqui.
  const definirLocalizacao = useHomeStore((s) => s.definirLocalizacao)
  const ligarLocalizacao = useHomeStore((s) => s.ligarLocalizacao)
  const limparLocalizacao = useHomeStore((s) => s.limparLocalizacao)

  // O idioma da página para leitor de tela e hifenização. O `lang` na raiz da
  // Home cobre a árvore dela; o do <html> cobre o que o Radix porta para o
  // <body> (menus, diálogos) — e volta ao de antes quando a Home sai, porque o
  // resto do app segue em português.
  useEffect(() => {
    const anterior = document.documentElement.lang
    document.documentElement.lang = idioma
    return () => { document.documentElement.lang = anterior }
  }, [idioma])
  // A falha de localização vira toast AQUI porque o único outro sinal é o botão
  // do controle, no canto do globo — invisível no telefone com o painel aberto.
  const aoErroDeLocalizacao = useCallback((codigo: number) => {
    if (codigo === 1) {
      // Permissão negada: o pedido de compartilhar não vai se realizar — desliga
      // para o estado não ficar armado à espera de um fix que nunca vem.
      limparLocalizacao()
      createToast.error(t.casca.localizacao.negada, t.casca.localizacao.negadaDica)
    } else {
      createToast.error(t.casca.localizacao.falhou, t.casca.localizacao.falhouDica)
    }
  }, [limparLocalizacao, t])

  const { current, canEdit } = useWorkspace()

  // ── Arrastar arquivos para o Drive ─────────────────────────────────────────
  // A janela inteira aceita o arquivo; quem acende é a caixa do assistente
  // (`data-arraste`). Os filtros são os do backend — este caminho manda ao
  // mesmo `POST /drive/upload` e traduz a recusa. O estado vive na store porque
  // Ctrl+I desmonta a barra e os chips iriam junto.
  const definirArrastandoArquivo = useHomeStore((s) => s.definirArrastandoArquivo)
  const receberAnexos = useAnexos({
    workspaceId: current?.id_hash ?? null,
    // `canEdit` espelha o papel `editor` que o Drive exige: prever o 403 poupa a rede
    // de quem só é leitor. Anônimo é `false` aqui, mas o `receber` já desvia
    // para o login antes de olhar isto.
    podeEnviar: canEdit,
    anonimo,
    aoExigirLogin: () => pedirEntrada("entrar"),
    aoAvisar: (titulo, detalhe) => createToast.error(titulo, detalhe),
  })
  useArrasteDeArquivos({
    // Sem sessão o arraste ainda é escutado: soltar abre o login (a mesma
    // porta do primeiro envio), em vez de o navegador abrir o arquivo.
    ativo: true,
    aoArrastar: definirArrastandoArquivo,
    aoSoltar: receberAnexos.receber,
  })

  // Trocar o workspace ativo esvazia os anexos: eles são "o que acabei de
  // mandar ao Drive DESTE workspace", e a referência da mensagem casa com o
  // workspace da conversa. Mantê-los apontaria para arquivos de outro Drive,
  // que o assistente do novo workspace não acha. Só na TROCA — o null→ws
  // inicial (nada para limpar) não conta.
  const limparAnexos = useHomeStore((s) => s.limparAnexos)
  const workspaceAnterior = useRef(current?.id_hash ?? null)
  useEffect(() => {
    const agora = current?.id_hash ?? null
    if (workspaceAnterior.current !== null && workspaceAnterior.current !== agora) limparAnexos()
    workspaceAnterior.current = agora
  }, [current?.id_hash, limparAnexos])

  // O id que o STREAM anunciou (1º quadro `conversa`). Guardado porque é o que
  // distingue "a conversa nova ganhou um id" de "a pessoa abriu outro chat":
  // nos dois casos o `conversaId` vai de null para um id. É marcador de USO
  // ÚNICO: a comparação abaixo o consome. Guardado para sempre, ele passava a
  // significar "qualquer id que o stream já anunciou nesta sessão", e reabrir
  // essa conversa pelos Chats mais tarde não trocava o escopo das camadas.
  const idDoStream = useRef<string | null>(null)
  const anunciar = useHomeStore((s) => s.anunciarConversa)
  const assistente = useAssistente({
    conversaId,
    workspaceId: current?.id_hash ?? null,
    // O anúncio inteiro (id, título, nova) vai à store ANTES da seleção: a
    // lista de Chats, no sidebar, insere a linha e o `aria-current` acende nela
    // no mesmo ciclo. Ver `anunciarConversa`.
    onConversa: (info) => { anunciar(info); idDoStream.current = info.id; selecionar(info.id) },
    anonimo,
  })

  // O escopo das camadas do globo: muda quando a pessoa abre OUTRA conversa (ou
  // começa uma nova), e não quando a conversa em curso aprende o próprio id —
  // aí as camadas que estão na tela são dela mesma.
  const escopo = useRef("nova:0")
  const conversaAnterior = useRef<string | null | undefined>(undefined)
  const novas = useRef(0)
  if (conversaAnterior.current !== conversaId) {
    const anunciado = idDoStream.current
    idDoStream.current = null // consumido: vale para ESTA troca, e só para ela
    if (!conversaId || conversaId !== anunciado) {
      escopo.current = conversaId ?? `nova:${++novas.current}`
    }
    conversaAnterior.current = conversaId
  }

  const camadas = useCamadas(assistente.turnos, escopo.current)
  const { adicionar: adicionarCamada } = camadas

  // O "Usar minha localização" do "+" liga o compartilhar E aciona o MESMO
  // controle do globo (o botão do canto): o globo segue a pessoa e o `geolocate`
  // sobe a coordenada por `aoLocalizar`. A ordem importa: ligar antes, para o
  // primeiro fix já entrar compartilhado. Já seguindo, o `localizar()` só
  // reemite a última posição (nunca desliga o rastreio — trigger é alternador).
  // `refMapa` é estável (useRef do useCamadas), então o callback não se recria.
  const refMapa = camadas.refMapa
  const pedirLocalizacao = useCallback(() => {
    ligarLocalizacao()
    refMapa.current?.localizar()
  }, [ligarLocalizacao, refMapa])

  // ── A entrada: o primeiro envio sem sessão ─────────────────────────────────
  // A mensagem fica pendente, volta à caixa (o submeter() da barra a esvaziou
  // — vazia no hero, ela recomeçaria a digitar a sugestão da vez) e o modal de
  // entrada abre sobre o globo. Quando o login der certo, ela vai sozinha (o
  // efeito abaixo). Fechar o modal sem entrar desiste do envio, mas o texto
  // fica na barra.
  const exigirLogin = useCallback((texto: string) => {
    definirRascunho(texto)
    definirEnvioPendente(texto)
    pedirEntrada("entrar")
  }, [definirRascunho, definirEnvioPendente, pedirEntrada])

  // `?entrar=1`/`?cadastro=1`: o modal nasce aberto — uma vez, e só sem sessão
  // (logado, a query é ignorada). Os painéis que vêm de um LINK DE E-MAIL
  // (senha e verificação) são a exceção — ver `ehPainelDeEmail`, que explica
  // por quê.
  const pediuDaUrl = useRef(false)
  const doEmail = ehPainelDeEmail(entrada)
  useEffect(() => {
    if (pediuDaUrl.current || !entrada || (!anonimo && !doEmail)) return
    pediuDaUrl.current = true
    pedirEntrada(entrada)
  }, [anonimo, entrada, doEmail, pedirEntrada])

  // A sessão chegou (pelo modal, ou por um login noutra aba) com o modal
  // aberto: fecha, mantendo o pendente. Os painéis do e-mail ficam, pelo mesmo
  // motivo — fechar por baixo de quem está usando o link é queimar um token de
  // uso único.
  useEffect(() => {
    if (!anonimo && entradaPedida && !ehPainelDeEmail(entradaPedida)) concluirEntrada()
  }, [anonimo, entradaPedida, concluirEntrada])

  // O login deu certo dentro do modal. Com `callbackUrl` (o admin que pediu
  // /projects sem sessão) a pessoa vai para lá — e o pendente não faz sentido
  // fora da Home.
  const aoEntrar = useCallback(() => {
    concluirEntrada()
    if (callbackUrl && callbackUrl !== "/") {
      definirEnvioPendente(null)
      router.push(callbackUrl)
      router.refresh()
    }
  }, [concluirEntrada, callbackUrl, definirEnvioPendente, router])

  // O envio sozinho — um efeito, não um callback: o login troca o status para
  // "authenticated" (signIn sem redirect), `anonimo` cai, o useAssistente consulta
  // o /estado e só ENTÃO dá para enviar. A cota estourada segue a regra da
  // barra: a mensagem fica na caixa, com o aviso.
  const { enviar: enviarAoAgente, correndo, parar, estado } = assistente
  useEffect(() => {
    if (anonimo || !envioPendente || correndo || estado?.ativo !== true) return
    const cota = estado.cota
    if (cota && cota.gasto >= cota.teto) return
    definirEnvioPendente(null)
    definirRascunho("")
    void enviarAoAgente(envioPendente)
  }, [anonimo, envioPendente, correndo, estado, enviarAoAgente, definirEnvioPendente, definirRascunho])

  // Logout feito noutra aba durante um stream: a Home vira anônima sem
  // remontar, e um stream que continuasse correndo iria contra uma sessão que
  // já não existe. A conversa que estava na tela fica até recarregar.
  useEffect(() => {
    if (anonimo) parar()
  }, [anonimo, parar])

  // ── O hero do primeiro acesso ──────────────────────────────────────────────
  // Estado inicial de TODO acesso (carregar a página), sem flag nem
  // localStorage. Termina assim que a pessoa ENVIA — no instante em que o
  // stream começa (`correndo`), e não só no primeiro token visível: a barra
  // escorrega para o rodapé e a faixa carrega já com o indicador de raciocínio
  // (a `Conversa` desenha «Pensando» para o turno ainda sem bloco).
  //
  // Antes o gatilho era o primeiro token TEXTO — raciocínio e ferramentas não
  // contavam, e a barra ficava centrada "processando". Com o assistente
  // consultando o catálogo e o WFS (várias ferramentas) antes de escrever, essa
  // fase é longa: a barra parecia travada no meio da tela, sem carregar o
  // diálogo (relato do dono). Deslizar no envio dá retorno imediato — a
  // pergunta e o "Pensando" aparecem na faixa, e a barra ganha o "Parar".
  //
  // Replay (abrir um chat antigo), o painel (Ctrl+I) e um artefato posto no
  // globo pela lista também encerram: nos três há conversa/camada para ver.
  // Uma vez encerrado não volta nesta carga — "nova conversa" cai no layout
  // normal, vazio.
  const [hero, setHero] = useState(true)
  const heroAcaba =
    assistente.correndo || assistente.turnos.length > 0 || assistente.carregandoReplay ||
    painel === "aberto" || pedidosDeCamada.length > 0
  useEffect(() => {
    if (hero && heroAcaba) setHero(false)
  }, [hero, heroAcaba])

  // O título e a frase saem do DOM depois da transição, ou na hora sem
  // movimento: montados e invisíveis, seriam alvos de foco fantasmas.
  const reduzMovimento = usePrefereMenosMovimento()
  const [heroNoDom, setHeroNoDom] = useState(true)
  useEffect(() => {
    if (hero) return
    if (reduzMovimento) { setHeroNoDom(false); return }
    const t = setTimeout(() => setHeroNoDom(false), DURACAO_DA_TRANSICAO_MS)
    return () => clearTimeout(t)
  }, [hero, reduzMovimento])

  // Esc interrompe a resposta em curso (o "Esc para parar" do status). Não de
  // dentro de um diálogo ou menu: lá o Esc já tem dono, e fechar os dois de uma
  // vez seria surpresa.
  useEffect(() => {
    if (!correndo) return
    function aoEscapar(e: KeyboardEvent) {
      if (e.key !== "Escape" || e.defaultPrevented) return
      const alvo = e.target as HTMLElement | null
      if (alvo?.closest?.('[role="dialog"], [role="menu"], [role="listbox"]')) return
      parar()
    }
    window.addEventListener("keydown", aoEscapar)
    return () => window.removeEventListener("keydown", aoEscapar)
  }, [correndo, parar])

  // Ctrl+I alterna aberto/barra. O efeito mora AQUI, e não no Painel: recolher
  // desmonta o Painel, e com ele ia o listener — o atalho anunciado no próprio
  // tooltip ("Recolher (Ctrl+I)") só funcionava uma vez e nunca reabria.
  //
  // Não há guarda de foco, e não precisa: o campo do assistente é a posição
  // padrão do cursor nesta tela, e barrar o atalho ali seria barrá-lo quase
  // sempre. O que o atalho não pode é custar o texto já digitado — por isso o
  // rascunho vive no homeStore (partilhado pelo painel e pela barra) e não no
  // `useState` de quem a troca desmonta.
  useEffect(() => {
    function aoTeclar(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return
      if (e.key.toLowerCase() !== "i") return
      // Dentro do modal de entrada (ou de qualquer diálogo) o atalho não
      // alterna o painel por trás dele.
      const alvo = e.target as HTMLElement | null
      if (alvo?.closest?.('[role="dialog"]')) return
      e.preventDefault()
      alternar()
    }
    window.addEventListener("keydown", aoTeclar)
    return () => window.removeEventListener("keydown", aoTeclar)
  }, [alternar])

  // Drena os pedidos "exibir no globo" que a lista de Artefatos (no sidebar)
  // enfileira: sidebar e globo são irmãos na árvore, então o pedido passa pela
  // store. `adicionar` deduplica (art:<id>), então um repetido só re-enquadra.
  // Consome só o que despachou — um clique que caia entre o render e o efeito
  // seria apagado sem nunca ter ido ao globo.
  useEffect(() => {
    if (pedidosDeCamada.length === 0) return
    const despachados = pedidosDeCamada.length
    for (const p of pedidosDeCamada) void adicionarCamada(p.artifactId, p.nome)
    consumirFila(despachados)
  }, [pedidosDeCamada, adicionarCamada, consumirFila])

  // No telefone o painel é opaco e cobre a tela inteira: a camada nova era
  // enquadrada no globo ATRÁS dele, e nada dizia que havia resultado. Recolher
  // à barra mostra a entrega; o cartão "X no globo" continua na conversa e a
  // barra a traz de volta num toque. Sem gravar a preferência — quem decidiu
  // foi a tela.
  // Baixar o arquivo de origem de uma camada, do próprio painel do globo — sem
  // ir procurar a mesma coisa na lista de Artefatos. O painel só oferece a ação
  // quando o servidor disse que há arquivo (`baixavel`), então chegar aqui e
  // falhar é exceção, não rotina: daí o toast em vez de um estado na linha.
  const baixarCamada = useCallback(async (artifactId: string, nome: string) => {
    const erro = await baixarArtefato(artifactId, t.listas.artefatos.download)
    if (erro) createToast.error(t.casca.baixarCamadaFalhou(nome), erro)
  }, [t])

  const isMobile = useIsMobile()
  const recolherBarra = useHomeStore((s) => s.recolherBarra)
  const quantasCamadas = camadas.camadas.length
  const camadasAntes = useRef(0)
  useEffect(() => {
    if (isMobile && quantasCamadas > camadasAntes.current) recolherBarra()
    camadasAntes.current = quantasCamadas
  }, [isMobile, quantasCamadas, recolherBarra])

  // Alternar painel/barra desmonta quem tinha o foco e ele cai no <body>. Só a
  // troca PEDIDA devolve o foco — na carga da página seria roubo de foco.
  const painelAnterior = useRef<string | null>(null)
  const autoFoco = painelAnterior.current !== null && painelAnterior.current !== painel
  if (hidratado) painelAnterior.current = painel

  return (
    <div lang={idioma} className="home dark relative h-svh w-full overflow-hidden bg-background text-foreground">
      {/* O `<h1>` é o que o leitor de tela anuncia primeiro e o que o buscador
          indexa — então ele diz o que a página FAZ, não o que ela mostra. */}
      <h1 className="sr-only">{t.casca.titulo}</h1>

      {/* Girando devagar no hero; no primeiro token volta à região de quem abriu (o `center` do Globo). */}
      <Globo
        layers={camadas.camadas}
        mapaRef={camadas.refMapa}
        girando={hero}
        pais={paisDaConexao}
        aoLocalizar={definirLocalizacao}
        aoErroDeLocalizacao={aoErroDeLocalizacao}
      />

      {/* O véu: o globo à vista ao norte, apagando-se rumo ao sul. Some com o hero. */}
      <div className="home-veu" data-visivel={hero} aria-hidden="true" />
      {heroNoDom && (
        <div className="home-hero-texto" data-visivel={hero} aria-hidden={!hero}>
          {/* A segunda metade na terracota da marca (`--primary`, o mesmo
              laranja do botão e do anel de foco): "Menos ferramentas" sozinho
              pode ser lido como plataforma mais pobre, e é o contraste entre as
              metades que desfaz isso — elas precisam ser vistas como um par,
              não como uma frase que continua. `text-wrap:balance` equilibra as
              linhas quando a tela estreita quebra o par.

              A troca do cinza por ela é do DONO, e tem um custo medido: a
              terracota (#e7723b) tem quase a mesma luminância da nuvem velada
              (#9e9c96), então sobre nuvem o contraste cai de 1,64:1 para
              1,11:1 — sobre oceano ele SOBE, de 5,41:1 para 6,19:1. Nenhum dos
              dois chegava aos 3:1 do WCAG, e lá o que separa glifo de imagem é
              o halo, não a razão; quem precisar do número tem de mexer no
              FUNDO. Ver `.home-hero-texto` em globals.css. */}
          {/* A legibilidade sobre a imagem de satélite (o halo) é do CSS, não
              daqui: ela precisa de `@supports`, que utilitária arbitrária não
              expressa. Ver `.home-hero-texto h2, p` em globals.css. */}
          <h2 className="mb-2.5 text-[clamp(24px,3.2vw,32px)] font-semibold leading-[1.22] tracking-tight text-foreground [text-wrap:balance]">
            {t.casca.hero.antes} <span className="text-primary">{t.casca.hero.destaque}</span>
          </h2>
          <p className="mx-auto max-w-[48ch] text-[15px] text-[#c2c2c2]">
            {t.casca.hero.subtitulo}
          </p>
        </div>
      )}

      <PainelCamadas
        camadas={camadas.camadas}
        avisos={camadas.avisos}
        carregando={camadas.carregando}
        onAlternar={camadas.alternarVisivel}
        onRemover={camadas.remover}
        onEnquadrar={camadas.enquadrar}
        onDispensarAviso={camadas.dispensarAviso}
        onBaixar={baixarCamada}
      />

      <AssistenteOuAviso
        assistente={assistente}
        painel={painel}
        autoFoco={autoFoco}
        hero={hero}
        anonimo={anonimo}
        enviar={anonimo ? exigirLogin : assistente.enviar}
        aoAnexar={receberAnexos.receber}
        aoPedirLocalizacao={pedirLocalizacao}
      />

      {/* A entrada (login, cadastro, verificação e o caminho da senha), em
          portal no <body> com a paleta da Home. */}
      <ModalDeEntrada
        modo={entradaPedida}
        tokenDoLink={tokenDoLink}
        comEnvioPendente={envioPendente !== null}
        onFechar={fecharEntrada}
        onEntrou={aoEntrar}
      />
    </div>
  )
}

/**
 * Painel, barra — ou o motivo de não haver nenhum dos dois.
 *
 * São TRÊS estados, e antes só havia um gate `ativo === true`: um 502 de dois
 * segundos no `/assistente/estado` deixava a pessoa com o globo e literalmente mais
 * nada — sem campo, sem aviso, sem "tentar de novo", e sem como distinguir
 * "desligado nesta instalação" de "a rede caiu".
 *
 * E um quarto, SEM SESSÃO: nada foi consultado (`estado` nulo, de propósito),
 * e a barra aparece do mesmo jeito — `enviar` aí é o portão que abre o modal
 * de entrada, não o stream.
 */
function AssistenteOuAviso({
  assistente, painel, autoFoco, hero, anonimo, enviar, aoAnexar, aoPedirLocalizacao,
}: {
  assistente: ReturnType<typeof useAssistente>
  painel: "aberto" | "barra"
  autoFoco: boolean
  hero: boolean
  /** Sem sessão: pula os avisos e mostra a barra; `enviar` é o portão do login. */
  anonimo: boolean
  enviar: (mensagem: string) => Promise<void> | void
  /** Anexa arquivos escolhidos no "+" (o mesmo caminho do arraste). */
  aoAnexar: (arquivos: File[]) => void
  /** Aciona o controle de localização do globo (o "Usar minha localização" do "+"). */
  aoPedirLocalizacao: () => void
}) {
  // Abrir o painel não desmonta a faixa e a barra na hora: elas ficam por um
  // instante, saindo (a faixa desliza para a lateral, a barra apaga), enquanto
  // o painel entra da direita. Sem movimento o prazo é zero. Hooks ANTES dos
  // retornos antecipados abaixo (a ordem tem de ser a mesma em todo render).
  const t = useTextos()
  const idiomaDaTela = useIdiomaDaTela()
  const reduzMovimento = usePrefereMenosMovimento()
  const { montado: centroMontado, saindo } = useSaida(painel === "aberto", reduzMovimento ? 0 : SAIDA_MS)

  // A altura dos extras da barra (chips/convite/aviso de recusados/passo),
  // medida por ela e repassada à faixa como folga: sem isso a barra cresceria
  // para cima e cobriria o "Expandir" da faixa (o mesmo bug do pill de cota).
  const [folgaExtras, setFolgaExtras] = useState(0)

  // O passo da vez (raciocínio ou a ferramenta em curso), para a barra mostrar
  // no rodapé enquanto o assistente trabalha. `null` quando parado ou escrevendo.
  const etapa = etapaDaConversa(assistente.turnos, assistente.correndo, idiomaDaTela)

  if (!anonimo) {
    if (assistente.consultando) {
      return (
        <div
          className={cn(
            "absolute left-1/2 z-30 w-[min(560px,calc(100%-2rem))] -translate-x-1/2 animate-pulse rounded-full border border-border bg-background/60 pb-safe",
            hero ? "top-1/2 h-14 -translate-y-1/2" : "bottom-6 h-11",
          )}
          aria-hidden="true"
        />
      )
    }

    if (assistente.falhou) {
      return (
        <Aviso
          texto={t.casca.assistenteFalhou}
          acao={<Button size="sm" variant="outline" className="gap-1.5 max-md:h-10" onClick={assistente.reconsultar}>
            <TbRefresh size={14} aria-hidden="true" /> {t.comum.tentarDeNovo}
          </Button>}
        />
      )
    }

    if (assistente.estado?.ativo !== true) {
      // O `motivo` do servidor é para quem administra, e em português ("defina
      // OPENROUTER_API_KEY"): nos outros idiomas vale o aviso do dicionário.
      const motivo = idiomaDaTela === "pt-BR" ? assistente.estado?.motivo : null
      return <Aviso texto={motivo || t.casca.assistenteIndisponivel} />
    }
  }

  return (
    <>
      {painel === "aberto" && (
        <Painel
          estado={assistente.estado}
          turnos={assistente.turnos}
          correndo={assistente.correndo}
          carregandoReplay={assistente.carregandoReplay}
          autoFoco={autoFoco}
          enviar={enviar}
          confirmar={assistente.confirmar}
          parar={assistente.parar}
          aoAnexar={aoAnexar}
          aoPedirLocalizacao={aoPedirLocalizacao}
        />
      )}
      {centroMontado && (
        <>
          {/* A última troca ao centro. Não durante o hero: lá o que se vê é o status. */}
          {!hero && (
            <Pilha
              turnos={assistente.turnos}
              correndo={assistente.correndo}
              confirmar={assistente.confirmar}
              enviar={enviar}
              saindo={saindo}
              // Com a cota estourada a barra cresce para cima (o pill âmbar) e
              // cobriria o rodapé da faixa — a faixa sobe junto (o bug do
              // "Expandir" encoberto, captura do dono de 2026-09-19).
              comAvisoDeCota={
                assistente.estado?.cota != null && assistente.estado.cota.gasto >= assistente.estado.cota.teto
              }
              // Os chips de anexo e o aviso de recusados crescem a barra para
              // cima do mesmo jeito; a folga é MEDIDA porque a altura deles
              // varia (quebram linha, o card de recusados é alto).
              folgaExtras={folgaExtras}
            />
          )}
          <Barra
            enviar={enviar}
            correndo={assistente.correndo}
            estado={assistente.estado}
            // Saindo, a barra NÃO pode focar: o efeito dela roda depois do do
            // painel (ordem dos irmãos) e roubaria o cursor recém-posto lá.
            autoFoco={autoFoco && !saindo}
            variante={hero ? "hero" : "rodape"}
            parar={assistente.parar}
            saindo={saindo}
            aoMedirExtras={setFolgaExtras}
            etapa={etapa}
            aoAnexar={aoAnexar}
            aoPedirLocalizacao={aoPedirLocalizacao}
          />
        </>
      )}
    </>
  )
}

/**
 * A saída animada da faixa e da barra quando o painel abre: as duas ficam
 * montadas por `ms` com `saindo` ligado (o CSS desliza e apaga), e só então
 * desmontam. Abrir e recolher dentro do prazo cancela — o timer é limpo e elas
 * ficam, sem `saindo`. Com `ms = 0` (sem movimento) desmontam no tick seguinte,
 * sem quadro visível. Nascem desmontadas se o painel já está aberto ao montar.
 *
 * `saindo` é DERIVADO (`aberto && montado`), não estado: vale já no render em
 * que o painel abre. Num estado posto por efeito ele chegaria um render depois
 * — e nesse render a barra ainda receberia `autoFoco` e roubaria o foco do
 * painel recém-montado.
 */
function useSaida(aberto: boolean, ms: number): { montado: boolean; saindo: boolean } {
  const [montado, setMontado] = useState(!aberto)
  useEffect(() => {
    if (!aberto) {
      setMontado(true)
      return
    }
    if (!montado) return
    const timer = setTimeout(() => setMontado(false), ms)
    return () => clearTimeout(timer)
  }, [aberto, montado, ms])
  return { montado, saindo: aberto && montado }
}

/** No lugar da barra de comando, com o mesmo enquadramento. */
function Aviso({ texto, acao }: { texto: string; acao?: React.ReactNode }) {
  return (
    <div
      role="status"
      className="home dark absolute bottom-6 left-1/2 z-30 flex w-[min(560px,calc(100%-2rem))] -translate-x-1/2 items-center gap-2 rounded-full border border-border bg-background/95 px-4 py-2 pb-safe text-sm text-muted-foreground shadow-2xl backdrop-blur"
    >
      <TbAlertTriangle size={16} className="shrink-0 text-amber-400" aria-hidden="true" />
      <span className="min-w-0 flex-1">{texto}</span>
      {acao}
    </div>
  )
}
