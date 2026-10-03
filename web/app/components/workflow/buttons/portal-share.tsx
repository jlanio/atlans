"use client"
import { useState } from "react"
import { useParams } from "next/navigation"
import { useStore } from "@xyflow/react"
import { Button } from "@/app/components/ui/button"
import { TbWorld } from "react-icons/tb"
import PortalSettingsDialog from "../PortalSettingsDialog"
import { IWorkflow } from "@/service/types"

interface PortalShareProps {
  workflow?: IWorkflow
}

const PortalShare = ({ workflow }: PortalShareProps) => {
  const { id } = useParams<{ id: string }>()
  // Boolean selector: the button only depends on a PublishMap EXISTING on the
  // canvas. Subscribing to `useNodes()` it re-rendered on every pointermove of a
  // drag to recompute the same answer.
  const hasPublishMap = useStore(s => {
    for (const no of s.nodeLookup.values()) {
      if ((no.data as { name?: string })?.name === "PublishMap") return true
    }
    return false
  })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [portalAccess, setPortalAccess] = useState<"disabled" | "public" | "private">(
    workflow?.portal_access ?? "disabled"
  )
  const [sharedWith, setSharedWith] = useState<string[] | null>(
    workflow?.portal_shared_with ?? null
  )

  if (!id || !hasPublishMap) return null

  return (
    <>
      <Button
        variant="outline"
        size="icon"
        title={
          portalAccess === "disabled"
            ? "Configurar portal de compartilhamento"
            : portalAccess === "public"
            ? "Portal publico ativo"
            : "Portal privado ativo"
        }
        onClick={() => setDialogOpen(true)}
      >
        <TbWorld
          className={portalAccess !== "disabled" ? "text-green-500" : undefined}
        />
      </Button>

      <PortalSettingsDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        workflowId={id}
        workflowName={workflow?.name ?? ""}
        initialAccess={portalAccess}
        initialSharedWith={sharedWith}
        onSaved={(access, shared) => {
          setPortalAccess(access)
          setSharedWith(shared)
        }}
      />
    </>
  )
}

export default PortalShare
