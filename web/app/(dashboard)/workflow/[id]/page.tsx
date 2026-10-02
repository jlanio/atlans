"use client"
import ReactFlowComponent from "@/app/components/workflow"
import { FlowContextProvider } from "@/context/useFlowContext"
import { IWorkflow } from "@/service/types"
import { ReactFlowProvider } from "@xyflow/react"
import { useParams } from "next/navigation"
import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import '@xyflow/react/dist/style.css';
import { GisFlowService } from "@/service/GisFlowService"
import { ErroDeCarga } from "@/app/components/shared/estados"

export default function WorkFlowCreatePage() {

  const { id } = useParams<{ id: string }>()
  const { status } = useSession()
  const [workflow, setWorkflow] = useState<IWorkflow>()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (status === "authenticated") {
      getWorkflow()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, id])

  async function getWorkflow() {
    setError(null)
    const res = await GisFlowService.getWorkflowById(id)
    if (!res.success || !res.data) {
      setError(res.error?.message ?? "Não foi possível carregar o workflow.")
      return
    }
    setWorkflow(res.data)
  }

  if (error) {
    // Cartão de erro do §3.2 do contrato: só toma a tela na 1ª carga (o canvas
    // ainda não existe aqui). "Tentar de novo" refaz a mesma busca.
    return (
      <div className="w-full h-full flex items-center justify-center p-4">
        <ErroDeCarga
          titulo="Não foi possível carregar o workflow"
          mensagem={error}
          onTentar={getWorkflow}
          className="w-full max-w-sm"
        />
      </div>
    )
  }

  return (
    <div className='w-full h-full'>

      <ReactFlowProvider>
        <FlowContextProvider>
          <ReactFlowComponent workflow={workflow} reloadWorkflow={getWorkflow} />
        </FlowContextProvider>
      </ReactFlowProvider>

    </div>
  )
}
