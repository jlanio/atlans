import { z } from "zod"
import { nameField } from "@/utils/schemas"

export const formConfigureProjectSchema = z.object({
  name: nameField({ max: 50, label: "do projeto" }),
  description: z.string().optional(),
})

