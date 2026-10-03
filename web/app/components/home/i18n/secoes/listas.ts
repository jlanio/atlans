// web/app/components/home/i18n/secoes/listas.ts
//
// The three lists of the Meus group in the sidebar — Chats (with the rename
// dialog), Agendamentos and Artefatos — and what their hooks choose to say
// (toasts, the failure microcopy). The Portuguese is the usual text, byte for
// byte: whoever uses the Home in Portuguese sees no change at all, and the tests
// that check text keep checking the same text.
//
// What comes from the server (conversation title, workflow name, an error's
// `detail`) does not live here, nor do the generic words (Cancelar, Salvar,
// Apagar, Renomear, Tentar de novo), which belong to `comum`. The components
// shared with the administration panel (AvisoAmbar, RetencaoHint, DeleteDialog)
// stay in Portuguese by default — the Home passes them the texts from here.

/** 0 = Sunday … 6 = Saturday, as in cron (7 arrives here already as 0). */
const DAYS_PT = ["aos domingos", "às segundas", "às terças", "às quartas", "às quintas", "às sextas", "aos sábados"]
const DAYS_EN = ["Sundays", "Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays"]
const DAYS_ES = ["los domingos", "los lunes", "los martes", "los miércoles", "los jueves", "los viernes", "los sábados"]

/** "a las 6:00", but "a la 1:00": in Spanish the article agrees with the hour. */
const atHourEs = (hora: string) => (/^0?1:/.test(hora) ? `a la ${hora}` : `a las ${hora}`)

export const pt = {
  /** What the three lists repeat: the cut-off footer and the failure fallback. */
  geral: {
    mostrando: (n: string, total: string) => `mostrando ${n} de ${total}`,
    verMais: "Ver mais",
    tenteDeNovo: "Tente de novo.",
  },
  chats: {
    carregando: "Carregando as conversas",
    vazio: "Nenhuma conversa ainda.",
    semTitulo: "Sem título",
    carregarFalhou: "Não foi possível carregar as conversas.",
    carregarMaisFalhou: "Não foi possível carregar mais conversas.",
    apagar: {
      titulo: "Apagar conversa",
      descricao: (titulo: string) => `"${titulo}" sai da lista. O histórico fica no servidor.`,
      apagando: "Apagando…",
      falhou: "Não foi possível apagar a conversa",
    },
  },
  renomear: {
    titulo: "Renomear conversa",
    descricao: "Escolha um novo título para esta conversa.",
    campo: "Título",
    salvando: "Salvando…",
    falhou: "Não foi possível renomear a conversa. Tente de novo.",
  },
  agendamentos: {
    carregando: "Carregando os agendamentos",
    vazio: "Nenhum agendamento.",
    carregarFalhou: "Não foi possível carregar os agendamentos.",
    carregarMaisFalhou: "Não foi possível carregar mais agendamentos.",
    atualizarFalhou: "Não foi possível atualizar os agendamentos.",
    preparando: "Preparando a execução",
    doAssistente: "Fluxo do assistente",
    pausado: "pausado",
    pausadoPor: (motivo: string) => `pausado — ${motivo}`,
    calculando: "calculando",
    pausar: "Pausar",
    ativar: "Ativar",
    rodarAgora: "Rodar agora",
    ativou: "Agendamento ativado",
    pausou: "Agendamento pausado",
    alterarFalhou: "Não foi possível alterar o agendamento",
    executarFalhou: "Erro ao executar workflow",
    iniciou: (fluxo: string) => `Workflow "${fluxo}" iniciado!`,
    prepararFalhou: "Não foi possível preparar a execução.",
    lerParametrosFalhou: "Falha ao ler os parâmetros do workflow. Tente de novo.",
    /**
     * The summary sentences ("todo dia às 06:00 · amanhã, 06:00"). In Portuguese
     * the list uses `resumirAgendamento` from projects/gatilho as is; these keys
     * are the TEMPLATE for the other languages, and a test checks that, run
     * through the same path, they give exactly the trigger's text.
     */
    resumo: {
      aCadaSegundos: (n: number) => `a cada ${n} s`,
      aCadaMinutos: (n: number) => `a cada ${n} min`,
      aCadaHoras: (n: number) => `a cada ${n} h`,
      aCadaDias: (n: number) => `a cada ${n} ${n === 1 ? "dia" : "dias"}`,
      aCadaUnidade: (n: number, unidade: string) => `a cada ${n} ${unidade}`,
      aCada: (n: number) => `a cada ${n}`,
      intervalo: "intervalo",
      todoDia: (hora: string) => `todo dia às ${hora}`,
      segASex: (hora: string) => `seg–sex às ${hora}`,
      naSemana: (dia: number, hora: string) => `${DAYS_PT[dia]} às ${hora}`,
      noDia: (dia: number, hora: string) => `dia ${dia} às ${hora}`,
      recorrencia: "recorrência (RRULE)",
      agendamento: "agendamento",
      amanha: "amanhã",
      workflowInativo: "workflow inativo",
    },
  },
  artefatos: {
    carregando: "Carregando o acervo",
    carregarFalhou: "Não foi possível carregar o acervo.",
    atualizarFalhou: "Não foi possível atualizar o acervo.",
    driveFalhou: "Não foi possível listar o Drive.",
    artefatosFalharam: "Não foi possível listar os artefatos de execução.",
    semWorkspace: "Nenhum workspace ativo.",
    vazio: "Nenhum artefato ou arquivo.",
    vazioSemDrive: "Nenhum artefato de execução — o Drive não pôde ser lido.",
    vazioSemArtefatos: "Nenhum arquivo no Drive — os artefatos não puderam ser lidos.",
    exibirNoGlobo: "Exibir no globo",
    /** The end of the `title` of the row that goes to the globe: "nome · GEOJSON — exibir no globo". */
    dicaExibirNoGlobo: "exibir no globo",
    baixar: "Baixar",
    metadados: "Metadados",
    excluir: "Excluir",
    baixarFalhou: (nome: string) => `Não foi possível baixar "${nome}"`,
    baixarArquivoFalhou: "Não foi possível baixar o arquivo",
    excluirFalhou: "Não foi possível excluir",
    excluirDialogo: {
      tituloArquivo: "Excluir arquivo",
      tituloArtefato: "Excluir artefato",
      descricao: (nome: string) => `"${nome}" será removido. Esta ação não pode ser desfeita.`,
      excluindo: "Excluindo…",
    },
    /** Why the row does not go to the globe — the key is the `motivo` from `artefatos/normalizar`. */
    semPrevia: {
      executor: "o conteúdo ficou no executor e nunca subiu para a nuvem",
      cartaImagem: "carta imagem: sem prévia no globo — baixe o arquivo",
      semCamadaNoPortal: "a publicação deste formato não tem camada no portal",
      formatoSemPrevia: "formato sem prévia no globo — publique o mapa para exibi-lo",
      drive: "arquivo do Drive não vai ao globo nesta versão",
    },
    /** The ephemeral artifact's retention hint (`RetencaoHint`). `n` is `dias` already formatted. */
    retencao: {
      expirado: "expirado",
      expiraHoje: "expira hoje",
      expiraEm: (dias: number, n: string) => `expira em ${n} ${dias === 1 ? "dia" : "dias"}`,
      removidoEm: (quando: string) => `Removido automaticamente em ${quando}`,
    },
    /** The Drive metadata dialog (`MetadataDialog`); numbers and dates come from the Home's formatters. */
    metadadosDialogo: {
      descricao: "Metadados do arquivo",
      rotulos: {
        extensao: "Extensão",
        tamanho: "Tamanho",
        mime: "MIME type",
        enviadoEm: "Enviado em",
        atualizadoEm: "Atualizado em",
        id: "ID",
        geometria: "Geometria",
        crs: "CRS",
        feicoes: "Feições",
        colunas: "Colunas",
        extensaoEspacial: "Extensão",
      },
      semNuvemTitulo: "O conteúdo não está na nuvem.",
      semNuvemTexto:
        "Este arquivo foi catalogado por um executor e os bytes nunca saíram daquela máquina. " +
        "A plataforma conhece os metadados acima, mas não o conteúdo — por isso não há download. " +
        "Workflows que rodem nesse executor conseguem lê-lo normalmente.",
      executor: (id: string) => `executor ${id}`,
    },
    /** The marker for content that stayed on the executor (`LocalBadge`). */
    local: {
      rotulo: "Conteúdo apenas no executor",
      titulo: (executorId: string | null | undefined) =>
        `O conteúdo permanece no ${executorId ? `executor ${executorId.slice(0, 8)}…` : "executor de origem"} ` +
        "e nunca foi enviado para a nuvem. Não pode ser baixado pela plataforma, mas continua " +
        "disponível para workflows que rodem nesse executor.",
    },
    /** The download error (`baixarArtefato`); the server message, when present, passes through as it came. */
    download: {
      noExecutor: "Este arquivo permanece no executor e não pode ser baixado daqui.",
      tenteDeNovo: "Tente de novo.",
    },
  },
}

export const en: typeof pt = {
  geral: {
    mostrando: (n, total) => `showing ${n} of ${total}`,
    verMais: "Show more",
    tenteDeNovo: "Try again.",
  },
  chats: {
    carregando: "Loading chats",
    vazio: "No chats yet.",
    semTitulo: "Untitled",
    carregarFalhou: "Couldn’t load chats.",
    carregarMaisFalhou: "Couldn’t load more chats.",
    apagar: {
      titulo: "Delete chat",
      descricao: (titulo) => `"${titulo}" will be removed from the list. Its history stays on the server.`,
      apagando: "Deleting…",
      falhou: "Couldn’t delete the chat",
    },
  },
  renomear: {
    titulo: "Rename chat",
    descricao: "Choose a new title for this chat.",
    campo: "Title",
    salvando: "Saving…",
    falhou: "Couldn’t rename the chat. Try again.",
  },
  agendamentos: {
    carregando: "Loading schedules",
    vazio: "No schedules.",
    carregarFalhou: "Couldn’t load schedules.",
    carregarMaisFalhou: "Couldn’t load more schedules.",
    atualizarFalhou: "Couldn’t refresh schedules.",
    preparando: "Preparing the run",
    doAssistente: "Assistant workflow",
    pausado: "paused",
    pausadoPor: (motivo) => `paused — ${motivo}`,
    calculando: "calculating",
    pausar: "Pause",
    ativar: "Activate",
    rodarAgora: "Run now",
    ativou: "Schedule activated",
    pausou: "Schedule paused",
    alterarFalhou: "Couldn’t update the schedule",
    executarFalhou: "Couldn’t run the workflow",
    iniciou: (fluxo) => `Workflow "${fluxo}" started!`,
    prepararFalhou: "Couldn’t prepare the run.",
    lerParametrosFalhou: "Couldn’t read the workflow’s parameters. Try again.",
    resumo: {
      aCadaSegundos: (n) => `every ${n} s`,
      aCadaMinutos: (n) => `every ${n} min`,
      aCadaHoras: (n) => `every ${n} h`,
      aCadaDias: (n) => `every ${n} ${n === 1 ? "day" : "days"}`,
      aCadaUnidade: (n, unidade) => `every ${n} ${unidade}`,
      aCada: (n) => `every ${n}`,
      intervalo: "interval",
      todoDia: (hora) => `every day at ${hora}`,
      segASex: (hora) => `Mon–Fri at ${hora}`,
      naSemana: (dia, hora) => `${DAYS_EN[dia]} at ${hora}`,
      noDia: (dia, hora) => `monthly on day ${dia} at ${hora}`,
      recorrencia: "recurrence (RRULE)",
      agendamento: "schedule",
      amanha: "tomorrow",
      workflowInativo: "workflow inactive",
    },
  },
  artefatos: {
    carregando: "Loading artifacts and files",
    carregarFalhou: "Couldn’t load artifacts and files.",
    atualizarFalhou: "Couldn’t refresh artifacts and files.",
    driveFalhou: "Couldn’t list Drive files.",
    artefatosFalharam: "Couldn’t list run artifacts.",
    semWorkspace: "No active workspace.",
    vazio: "No artifacts or files.",
    vazioSemDrive: "No run artifacts — Drive couldn’t be read.",
    vazioSemArtefatos: "No files in Drive — artifacts couldn’t be read.",
    exibirNoGlobo: "Show on the globe",
    dicaExibirNoGlobo: "show on the globe",
    baixar: "Download",
    metadados: "Metadata",
    excluir: "Delete",
    baixarFalhou: (nome) => `Couldn’t download "${nome}"`,
    baixarArquivoFalhou: "Couldn’t download the file",
    excluirFalhou: "Couldn’t delete",
    excluirDialogo: {
      tituloArquivo: "Delete file",
      tituloArtefato: "Delete artifact",
      descricao: (nome) => `"${nome}" will be deleted. This can’t be undone.`,
      excluindo: "Deleting…",
    },
    semPrevia: {
      executor: "the content stayed on the executor and was never uploaded to the cloud",
      cartaImagem: "map image: no preview on the globe — download the file",
      semCamadaNoPortal: "this format’s publication has no layer on the portal",
      formatoSemPrevia: "no preview on the globe for this format — publish the map to show it",
      drive: "Drive files don’t go on the globe in this version",
    },
    retencao: {
      expirado: "expired",
      expiraHoje: "expires today",
      expiraEm: (dias, n) => `expires in ${n} ${dias === 1 ? "day" : "days"}`,
      removidoEm: (quando) => `Deleted automatically on ${quando}`,
    },
    metadadosDialogo: {
      descricao: "File metadata",
      rotulos: {
        extensao: "Extension",
        tamanho: "Size",
        mime: "MIME type",
        enviadoEm: "Uploaded",
        atualizadoEm: "Updated",
        id: "ID",
        geometria: "Geometry",
        crs: "CRS",
        feicoes: "Features",
        colunas: "Columns",
        extensaoEspacial: "Extent",
      },
      semNuvemTitulo: "The content isn’t in the cloud.",
      semNuvemTexto:
        "This file was cataloged by an executor and its bytes never left that machine. " +
        "The platform knows the metadata above, but not the content — so there’s no download. " +
        "Workflows that run on that executor can read it normally.",
      executor: (id) => `executor ${id}`,
    },
    local: {
      rotulo: "Content only on the executor",
      titulo: (executorId) =>
        `The content stays on ${executorId ? `executor ${executorId.slice(0, 8)}…` : "the source executor"} ` +
        "and was never uploaded to the cloud. It can’t be downloaded from the platform, but it’s " +
        "still available to workflows that run on that executor.",
    },
    download: {
      noExecutor: "This file stays on the executor and can’t be downloaded from here.",
      tenteDeNovo: "Try again.",
    },
  },
}

export const es: typeof pt = {
  geral: {
    mostrando: (n, total) => `mostrando ${n} de ${total}`,
    verMais: "Ver más",
    tenteDeNovo: "Inténtalo de nuevo.",
  },
  chats: {
    carregando: "Cargando las conversaciones",
    vazio: "Aún no hay conversaciones.",
    semTitulo: "Sin título",
    carregarFalhou: "No se pudieron cargar las conversaciones.",
    carregarMaisFalhou: "No se pudieron cargar más conversaciones.",
    apagar: {
      titulo: "Eliminar conversación",
      descricao: (titulo) => `"${titulo}" saldrá de la lista. El historial se queda en el servidor.`,
      apagando: "Eliminando…",
      falhou: "No se pudo eliminar la conversación",
    },
  },
  renomear: {
    titulo: "Renombrar conversación",
    descricao: "Elige un nuevo título para esta conversación.",
    campo: "Título",
    salvando: "Guardando…",
    falhou: "No se pudo renombrar la conversación. Inténtalo de nuevo.",
  },
  agendamentos: {
    carregando: "Cargando las programaciones",
    vazio: "No hay programaciones.",
    carregarFalhou: "No se pudieron cargar las programaciones.",
    carregarMaisFalhou: "No se pudieron cargar más programaciones.",
    atualizarFalhou: "No se pudieron actualizar las programaciones.",
    preparando: "Preparando la ejecución",
    doAssistente: "Flujo del asistente",
    pausado: "pausado",
    pausadoPor: (motivo) => `pausado — ${motivo}`,
    calculando: "calculando",
    pausar: "Pausar",
    ativar: "Activar",
    rodarAgora: "Ejecutar ahora",
    ativou: "Programación activada",
    pausou: "Programación pausada",
    alterarFalhou: "No se pudo cambiar la programación",
    executarFalhou: "No se pudo ejecutar el flujo",
    iniciou: (fluxo) => `¡Flujo "${fluxo}" iniciado!`,
    prepararFalhou: "No se pudo preparar la ejecución.",
    lerParametrosFalhou: "No se pudieron leer los parámetros del flujo. Inténtalo de nuevo.",
    resumo: {
      aCadaSegundos: (n) => `cada ${n} s`,
      aCadaMinutos: (n) => `cada ${n} min`,
      aCadaHoras: (n) => `cada ${n} h`,
      aCadaDias: (n) => `cada ${n} ${n === 1 ? "día" : "días"}`,
      aCadaUnidade: (n, unidade) => `cada ${n} ${unidade}`,
      aCada: (n) => `cada ${n}`,
      intervalo: "intervalo",
      todoDia: (hora) => `todos los días ${atHourEs(hora)}`,
      segASex: (hora) => `lun–vie ${atHourEs(hora)}`,
      naSemana: (dia, hora) => `${DAYS_ES[dia]} ${atHourEs(hora)}`,
      noDia: (dia, hora) => `el día ${dia} de cada mes ${atHourEs(hora)}`,
      recorrencia: "recurrencia (RRULE)",
      agendamento: "programación",
      amanha: "mañana",
      workflowInativo: "flujo inactivo",
    },
  },
  artefatos: {
    carregando: "Cargando los artefactos y archivos",
    carregarFalhou: "No se pudieron cargar los artefactos y archivos.",
    atualizarFalhou: "No se pudieron actualizar los artefactos y archivos.",
    driveFalhou: "No se pudieron listar los archivos del Drive.",
    artefatosFalharam: "No se pudieron listar los artefactos de ejecución.",
    semWorkspace: "No hay ningún workspace activo.",
    vazio: "No hay artefactos ni archivos.",
    vazioSemDrive: "No hay artefactos de ejecución — no se pudo leer el Drive.",
    vazioSemArtefatos: "No hay archivos en el Drive — no se pudieron leer los artefactos.",
    exibirNoGlobo: "Mostrar en el globo",
    dicaExibirNoGlobo: "mostrar en el globo",
    baixar: "Descargar",
    metadados: "Metadatos",
    excluir: "Eliminar",
    baixarFalhou: (nome) => `No se pudo descargar "${nome}"`,
    baixarArquivoFalhou: "No se pudo descargar el archivo",
    excluirFalhou: "No se pudo eliminar",
    excluirDialogo: {
      tituloArquivo: "Eliminar archivo",
      tituloArtefato: "Eliminar artefacto",
      descricao: (nome) => `"${nome}" se eliminará. Esta acción no se puede deshacer.`,
      excluindo: "Eliminando…",
    },
    semPrevia: {
      executor: "el contenido se quedó en el ejecutor y nunca se subió a la nube",
      cartaImagem: "mapa en imagen: sin vista previa en el globo — descarga el archivo",
      semCamadaNoPortal: "la publicación de este formato no tiene capa en el portal",
      formatoSemPrevia: "formato sin vista previa en el globo — publica el mapa para mostrarlo",
      drive: "los archivos del Drive no van al globo en esta versión",
    },
    retencao: {
      expirado: "expirado",
      expiraHoje: "expira hoy",
      expiraEm: (dias, n) => `expira en ${n} ${dias === 1 ? "día" : "días"}`,
      removidoEm: (quando) => `Eliminado automáticamente el ${quando}`,
    },
    metadadosDialogo: {
      descricao: "Metadatos del archivo",
      rotulos: {
        extensao: "Extensión",
        tamanho: "Tamaño",
        mime: "Tipo MIME",
        enviadoEm: "Subido el",
        atualizadoEm: "Actualizado el",
        id: "ID",
        geometria: "Geometría",
        crs: "CRS",
        feicoes: "Entidades",
        colunas: "Columnas",
        extensaoEspacial: "Extensión espacial",
      },
      semNuvemTitulo: "El contenido no está en la nube.",
      semNuvemTexto:
        "Este archivo lo catalogó un ejecutor y sus bytes nunca salieron de esa máquina. " +
        "La plataforma conoce los metadatos de arriba, pero no el contenido; por eso no hay descarga. " +
        "Los flujos que se ejecuten en ese ejecutor pueden leerlo normalmente.",
      executor: (id) => `ejecutor ${id}`,
    },
    local: {
      rotulo: "Contenido solo en el ejecutor",
      titulo: (executorId) =>
        `El contenido permanece en ${executorId ? `el ejecutor ${executorId.slice(0, 8)}…` : "el ejecutor de origen"} ` +
        "y nunca se subió a la nube. No se puede descargar desde la plataforma, pero sigue " +
        "disponible para los flujos que se ejecuten en ese ejecutor.",
    },
    download: {
      noExecutor: "Este archivo permanece en el ejecutor y no se puede descargar desde aquí.",
      tenteDeNovo: "Inténtalo de nuevo.",
    },
  },
}
