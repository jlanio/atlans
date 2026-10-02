import { z } from "zod"
import { nameField } from "@/utils/schemas"

export const formCredentialSchema = z.object({
  name: nameField({ max: 30, label: "da credencial" }),
  type: z.string(),
  data: z.record(z.string(), z.string()),
  // Metadados opcionais. `expires_at` NÃO fica aqui: vive dentro de `data`
  // (data.expires_at), do mesmo jeito que o backend armazena e o resolver aplica.
  description: z.string().max(200).optional(),
  tags: z.array(z.string()).optional(),
  // null = compartilhamento removido; string = id_hash do workspace com quem
  // compartilhar; undefined = não mexer (semântica PATCH do backend).
  workspace_id: z.string().nullable().optional(),
})
