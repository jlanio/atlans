import { useState, useEffect } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Label } from "@/app/components/ui/label"
import { TbDatabaseImport, TbRefresh, TbInbox } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { GisFlowService } from "@/service/GisFlowService"
import type { IDriveFile, IDriveFileList } from "@/service/types"
import { dadoOuAviso } from "@/lib/respostas"
import type { FieldProps } from "./types"

type DriveFieldProps = FieldProps

/** Teto do backend (`page_size` <= 200). O seletor pedia a página padrão de 50
 *  e filtrava extensões no cliente: um arquivo enviado depois do 50º do
 *  workspace simplesmente não aparecia para configurar o nó. */
const MAX_POR_PAGINA = 200

const DriveField = ({ field, values, setNodeField }: DriveFieldProps) => {
  const { current: workspace } = useWorkspace()
  const [files, setFiles] = useState<IDriveFile[]>([])
  const [loading, setLoading] = useState(false)
  const [truncado, setTruncado] = useState(false)
  // A lista não chegou: o aviso de "nenhum arquivo" seria uma afirmação falsa.
  const [falhou, setFalhou] = useState(false)

  const driveExtensions = field.drive_extensions ?? []

  async function fetchFiles() {
    if (!workspace) return
    setLoading(true)
    // O `ext` do backend aceita UMA extensão, então várias viram várias
    // chamadas em paralelo — e não um filtro no cliente sobre uma página
    // cortada, que era o que escondia arquivos.
    const filtros: (string | undefined)[] =
      driveExtensions.length > 0 ? [...driveExtensions] : [undefined]
    const respostas = await Promise.all(
      filtros.map(ext => GisFlowService.getDriveFiles({
        workspace_id: workspace.id_hash,
        ext,
        page: 1,
        page_size: MAX_POR_PAGINA,
      })),
    )

    // Uma extensão que falhou deixaria a lista incompleta sem dizer nada: a
    // falha de qualquer uma é a falha da lista — e o aviso sai uma vez só.
    const listas: IDriveFileList[] = []
    for (const res of respostas) {
      const dados = dadoOuAviso(res, "Erro ao carregar arquivos do Drive")
      if (dados === null) break
      listas.push(dados)
    }
    const completa = listas.length === respostas.length

    const porId = new Map<string, IDriveFile>()
    let cortou = false
    for (const lista of completa ? listas : []) {
      const itens = lista.items ?? []
      if ((lista.total ?? 0) > itens.length) cortou = true
      for (const f of itens) porId.set(f.id_hash, f)
    }
    setFiles([...porId.values()].sort((a, b) => a.original_name.localeCompare(b.original_name)))
    setTruncado(cortou)
    setFalhou(!completa)
    setLoading(false)
  }

  const extensionsKey = driveExtensions.join(",")

  useEffect(() => {
    fetchFiles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace?.id_hash, extensionsKey])

  const selected = (values?.[field.name] as string) ?? ""

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <Label htmlFor={field.name} className="flex items-center gap-1">
          <TbDatabaseImport className="h-3.5 w-3.5" />
          {field.description ?? "Arquivo do Drive"}
        </Label>
        <button
          type="button"
          onClick={fetchFiles}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Recarregar lista"
        >
          <TbRefresh className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <Select
        value={selected || "__none__"}
        onValueChange={value => setNodeField(field.name, value === "__none__" ? "" : value)}
      >
        <SelectTrigger id={field.name} className="w-full">
          <SelectValue placeholder={loading ? "Carregando..." : "Selecione um arquivo"} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__">
            <span className="text-muted-foreground">Nenhum arquivo</span>
          </SelectItem>
          {files.map(file => (
            <SelectItem key={file.id_hash} value={file.id_hash}>
              <div className="flex flex-col">
                <span>{file.original_name}</span>
                <span className="text-xs text-muted-foreground uppercase">{file.extension}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* O workspace tem mais arquivos do que cabe numa página: dizer isso é
          melhor que deixar a pessoa procurar um arquivo que existe e não está
          na lista. */}
      {truncado && !loading && (
        <p className="text-xs text-muted-foreground mt-1">
          Mostrando os {MAX_POR_PAGINA} arquivos mais recentes. Se o que procura não
          estiver aqui, localize-o pelo Drive.
        </p>
      )}

      {files.length === 0 && !loading && (
        <div className="flex items-start gap-2 mt-1 px-2 py-1.5 rounded-md bg-muted/40">
          <TbInbox className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            {falhou
              ? "Não foi possível carregar os arquivos do Drive. Recarregue a lista para tentar de novo."
              : "Nenhum arquivo no Drive deste workspace. Faça upload na tela do Drive para usá-lo aqui."}
          </p>
        </div>
      )}
    </div>
  )
}

export default DriveField
