import { z } from "zod"
import { nameField } from "@/utils/schemas"

export const formCredentialSchema = z.object({
  name: nameField({ max: 30, label: "da credencial" }),
  type: z.string(),
  data: z.record(z.string(), z.string()),
  // Optional metadata. `expires_at` does NOT go here: it lives inside `data`
  // (data.expires_at), the same way the backend stores it and the resolver applies it.
  description: z.string().max(200).optional(),
  tags: z.array(z.string()).optional(),
  // null = sharing removed; string = id_hash of the workspace to share
  // with; undefined = leave untouched (the backend's PATCH semantics).
  workspace_id: z.string().nullable().optional(),
})
