/**
 * O grupo Meu na store da Home: o aberto/fechado dos três itens é lembrado no
 * navegador (`atlans:home:meu`) porque, num estado local do item, ele morria a
 * cada abertura da gaveta no telefone, ao sair de `/` e ao cruzar 768px.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { useHomeStore, MEU_PADRAO } from "@/app/stores/homeStore"

const CHAVE = "atlans:home:meu"
const estado = () => useHomeStore.getState()

beforeEach(() => {
  window.localStorage.clear()
  useHomeStore.setState({ meu: { ...MEU_PADRAO }, hidratado: false })
})
afterEach(() => vi.restoreAllMocks())

describe("homeStore — o grupo Meu", () => {
  it("nasce com só Chats aberto — o default do SSR e do primeiro render", () => {
    expect(estado().meu).toEqual({ agendamentos: false, artefatos: false, chats: true })
  })

  it("alternar abre/fecha e grava a preferência", () => {
    estado().alternarItemDoMeu("artefatos")
    expect(estado().meu.artefatos).toBe(true)
    expect(JSON.parse(window.localStorage.getItem(CHAVE)!)).toEqual({ agendamentos: false, artefatos: true, chats: true })
    estado().alternarItemDoMeu("artefatos")
    expect(estado().meu.artefatos).toBe(false)
  })

  it("abrir é idempotente: já aberto, não muda nem regrava", () => {
    estado().abrirItemDoMeu("chats")
    expect(estado().meu.chats).toBe(true)
    expect(window.localStorage.getItem(CHAVE)).toBeNull()
    estado().abrirItemDoMeu("agendamentos")
    expect(estado().meu.agendamentos).toBe(true)
  })

  it("hidratar lê o lembrado e marca hidratado — sem gravar nada", () => {
    window.localStorage.setItem(CHAVE, JSON.stringify({ agendamentos: true, artefatos: false, chats: false }))
    estado().hidratar()
    expect(estado().meu).toEqual({ agendamentos: true, artefatos: false, chats: false })
    expect(estado().hidratado).toBe(true)

    window.localStorage.clear()
    estado().hidratar()
    expect(window.localStorage.getItem(CHAVE)).toBeNull()
    expect(estado().meu).toEqual(MEU_PADRAO)
  })

  it("JSON corrompido, parcial ou com lixo cai no padrão chave a chave", () => {
    window.localStorage.setItem(CHAVE, "{{")
    estado().hidratar()
    expect(estado().meu).toEqual(MEU_PADRAO)

    window.localStorage.setItem(CHAVE, JSON.stringify({ artefatos: true, chats: "sim" }))
    estado().hidratar()
    expect(estado().meu).toEqual({ agendamentos: false, artefatos: true, chats: true })
  })

  it("um localStorage que lança (janela privada) não derruba a store", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("cota") })
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("privada") })
    expect(() => estado().alternarItemDoMeu("chats")).not.toThrow()
    expect(estado().meu.chats).toBe(false)
    expect(() => estado().hidratar()).not.toThrow()
    expect(estado().hidratado).toBe(true)
  })
})

describe("homeStore — a entrada (o modal) e o envio pendente", () => {
  beforeEach(() => useHomeStore.setState({ entrada: null, envioPendente: null, rascunho: "" }))

  it("nasce fechado e sem pendente; pedir abre no modo pedido", () => {
    expect(estado().entrada).toBeNull()
    expect(estado().envioPendente).toBeNull()
    estado().pedirEntrada("cadastro")
    expect(estado().entrada).toBe("cadastro")
    estado().pedirEntrada("entrar")
    expect(estado().entrada).toBe("entrar")
  })

  it("fechar SEM entrar desiste do envio pendente — o texto continua no rascunho", () => {
    // Um login mais tarde não pode disparar uma mensagem esquecida.
    estado().definirRascunho("focos em MT")
    estado().definirEnvioPendente("focos em MT")
    estado().pedirEntrada("entrar")
    estado().fecharEntrada()
    expect(estado().entrada).toBeNull()
    expect(estado().envioPendente).toBeNull()
    expect(estado().rascunho).toBe("focos em MT")
  })

  it("concluir a entrada fecha e MANTÉM o pendente (o HomeView o envia)", () => {
    estado().definirEnvioPendente("focos em MT")
    estado().pedirEntrada("entrar")
    estado().concluirEntrada()
    expect(estado().entrada).toBeNull()
    expect(estado().envioPendente).toBe("focos em MT")
    estado().definirEnvioPendente(null)
    expect(estado().envioPendente).toBeNull()
  })
})

describe("homeStore — o anúncio de conversa", () => {
  // A lista de Chats só reage à TROCA DE IDENTIDADE do slot: "a mesma conversa
  // ganhou outra mensagem" tem de ser outro objeto, senão o efeito não roda.
  it("nasce vazio e grava um objeto NOVO a cada anúncio, mesmo repetindo o mesmo", () => {
    useHomeStore.setState({ anuncioDeConversa: null })
    expect(estado().anuncioDeConversa).toBeNull()

    const a = { id: "c1", titulo: "Focos", nova: true }
    estado().anunciarConversa(a)
    const primeiro = estado().anuncioDeConversa
    expect(primeiro).toEqual(a)
    expect(primeiro).not.toBe(a)

    estado().anunciarConversa(a)
    expect(estado().anuncioDeConversa).toEqual(a)
    expect(estado().anuncioDeConversa).not.toBe(primeiro)
  })
})

describe("homeStore — os anexos soltos sobre a Home", () => {
  beforeEach(() => useHomeStore.setState({ anexos: [], arrastandoArquivo: false }))

  const enviando = (id: string, nome: string) =>
    ({ id, nome, bytes: 1024, estado: "enviando" as const })

  it("o arraste só grava quando MUDA — não notifica à toa", () => {
    expect(estado().arrastandoArquivo).toBe(false)
    estado().definirArrastandoArquivo(true)
    expect(estado().arrastandoArquivo).toBe(true)
    // Idempotente: um segundo `true` não é uma mudança.
    const antes = estado().anexos
    estado().definirArrastandoArquivo(true)
    expect(estado().anexos).toBe(antes)
  })

  it("adiciona na ordem e corrige a linha por id (uploads terminam fora de ordem)", () => {
    estado().adicionarAnexos([enviando("a", "um.csv"), enviando("b", "dois.geojson")])
    expect(estado().anexos.map((x) => x.nome)).toEqual(["um.csv", "dois.geojson"])

    // O segundo termina primeiro.
    estado().atualizarAnexo("b", { estado: "pronto" })
    estado().atualizarAnexo("a", { estado: "recusado", motivo: "Extensão '.csv' não permitida.", tipo: "extension" })
    expect(estado().anexos.find((x) => x.id === "b")).toMatchObject({ estado: "pronto" })
    expect(estado().anexos.find((x) => x.id === "a")).toMatchObject({ estado: "recusado", tipo: "extension" })
  })

  it("atualizar um id que não existe não inventa linha", () => {
    estado().adicionarAnexos([enviando("a", "um.csv")])
    estado().atualizarAnexo("fantasma", { estado: "pronto" })
    expect(estado().anexos).toHaveLength(1)
  })

  it("limpar PRONTOS tira só os que já foram na mensagem — sobem e recusados ficam", () => {
    estado().adicionarAnexos([enviando("a", "um.csv"), enviando("b", "dois.geojson"), enviando("c", "big.tif")])
    estado().atualizarAnexo("a", { estado: "pronto" })
    estado().atualizarAnexo("c", { estado: "recusado", motivo: "grande", tipo: "size" })
    // b continua enviando.
    estado().limparAnexosProntos()
    expect(estado().anexos.map((x) => x.id)).toEqual(["b", "c"])
  })

  it("remover tira da barra e não toca no resto; descartar recusados limpa só eles", () => {
    estado().adicionarAnexos([enviando("a", "um.csv"), enviando("b", "dois.geojson")])
    estado().atualizarAnexo("a", { estado: "pronto" })
    estado().atualizarAnexo("b", { estado: "recusado", motivo: "x", tipo: "other" })
    estado().removerAnexo("a")
    expect(estado().anexos.map((x) => x.id)).toEqual(["b"])
    estado().descartarAnexosRecusados()
    expect(estado().anexos).toHaveLength(0)
  })

  it("limparAnexos esvazia tudo — a troca de workspace usa isto", () => {
    estado().adicionarAnexos([enviando("a", "um.csv"), enviando("b", "dois.geojson")])
    estado().atualizarAnexo("a", { estado: "pronto" })
    estado().limparAnexos()
    expect(estado().anexos).toHaveLength(0)
    // Idempotente: já vazio, não devolve objeto novo (não re-renderiza à toa).
    const antes = estado().anexos
    estado().limparAnexos()
    expect(estado().anexos).toBe(antes)
  })
})

describe("homeStore — a localização", () => {
  beforeEach(() => useHomeStore.setState({ localizacao: null, compartilharLocalizacao: false }))

  it("nasce sem posição e sem compartilhar", () => {
    expect(estado().localizacao).toBeNull()
    expect(estado().compartilharLocalizacao).toBe(false)
  })

  it("definir guarda a posição mas NÃO liga o compartilhar — só o gesto do '+' liga", () => {
    // É o que impede o botão nativo do globo (só "me achar no mapa") de anexar
    // a coordenada à conversa sem a pessoa pedir.
    estado().definirLocalizacao({ lat: -23.5505, lon: -46.6333, precisao_m: 18 })
    expect(estado().localizacao).toEqual({ lat: -23.5505, lon: -46.6333, precisao_m: 18 })
    expect(estado().compartilharLocalizacao).toBe(false)
  })

  it("histerese: o jitter de GPS parado (<~25 m) não troca o objeto", () => {
    estado().definirLocalizacao({ lat: -23.55, lon: -46.63, precisao_m: 20 })
    const antes = estado().localizacao
    // ~11 m de deslocamento e precisão parecida: ruído de quem está parado.
    estado().definirLocalizacao({ lat: -23.5501, lon: -46.63, precisao_m: 22 })
    expect(estado().localizacao).toBe(antes) // mesma referência
  })

  it("um deslocamento real (>~25 m) atualiza — o modo seguir acompanha", () => {
    estado().definirLocalizacao({ lat: 1, lon: 2, precisao_m: 10 })
    estado().definirLocalizacao({ lat: 1.001, lon: 2, precisao_m: 10 })
    expect(estado().localizacao).toEqual({ lat: 1.001, lon: 2, precisao_m: 10 })
  })

  it("parado, uma melhora FRANCA de precisão passa (o fix grosseiro vira fino)", () => {
    estado().definirLocalizacao({ lat: 1, lon: 2, precisao_m: 900 })
    estado().definirLocalizacao({ lat: 1.0001, lon: 2, precisao_m: 15 })
    expect(estado().localizacao).toEqual({ lat: 1.0001, lon: 2, precisao_m: 15 })
  })

  it("ligar/limpar comandam SÓ a intenção; a última posição fica", () => {
    estado().definirLocalizacao({ lat: 1, lon: 2, precisao_m: null })
    estado().ligarLocalizacao()
    expect(estado().compartilharLocalizacao).toBe(true)

    estado().limparLocalizacao()
    expect(estado().compartilharLocalizacao).toBe(false)
    // A posição continua: religar pelo "+" volta na hora, sem novo fix de GPS.
    expect(estado().localizacao).toEqual({ lat: 1, lon: 2, precisao_m: null })
  })

  it("o × PERSISTE: ticks do seguir depois de limpar não religam o compartilhar", () => {
    // O bug que esta separação mata: com o × zerando a posição, o próximo tick
    // do watchPosition regravava e o chip ressuscitava sozinho — a coordenada
    // voltava ao turno sem gesto da pessoa.
    estado().ligarLocalizacao()
    estado().definirLocalizacao({ lat: 1, lon: 2, precisao_m: 10 })
    estado().limparLocalizacao()

    estado().definirLocalizacao({ lat: 1.01, lon: 2.01, precisao_m: 8 }) // o tick seguinte
    expect(estado().compartilharLocalizacao).toBe(false)
    expect(estado().localizacao).toEqual({ lat: 1.01, lon: 2.01, precisao_m: 8 })
  })
})
