import { UseFormReturn } from "react-hook-form"
import z from "zod"
import { formCredentialSchema } from "../form-credential"
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { Input } from "@/app/components/ui/input"

interface NameInputProps {
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
}

const NameInput = ({ form }: NameInputProps) => {
  return (
    <FormField
      control={form.control}
      name="name"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Nome da credencial</FormLabel>
          <FormControl>
            <Input placeholder="Insira o nome da credencial" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}

export default NameInput