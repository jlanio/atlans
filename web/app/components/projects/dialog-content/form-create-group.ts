import { z } from "zod"
import { nameField } from "@/utils/schemas"

export const formCreateGroupSchema = z.object({
  name: nameField({ min: 1, max: 50, label: "do grupo" }),
  description: z.string().nullable(),
  workflowId: z.array(z.string())
})

