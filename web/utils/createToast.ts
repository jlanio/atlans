import { toast } from "sonner"

interface ToastAction {
  /** Texto do botão de ação (ex: "Desfazer"). */
  label: string
  /** Callback chamado ao clicar — deve executar o rollback ou ação inversa. */
  onClick: () => void
}

export const createToast = {

  error: (title: string, description?: string, action?: ToastAction) => toast.error(
    title,
    {
      description,
      descriptionClassName: "!text-black",
      className: "!bg-red-200 !text-black",
      action,
    }
  ),

  info: (title: string, description?: string, action?: ToastAction) => toast.info(title, { description, action }),

  /** Aviso (âmbar): a ação foi concluída, mas com uma ressalva que o usuário
   *  precisa saber — ex.: salvou, mas o agendamento não foi aplicado. */
  warning: (title: string, description?: string, action?: ToastAction) => toast.warning(title, {
    description,
    descriptionClassName: "!text-black",
    className: "!bg-amber-100 !text-black",
    action,
  }),

  loading: (title: string, description?: string) => toast.loading(title, { description }),

  success: (title: string, description?: string, action?: ToastAction) => toast.success(title, {
    description,
    style: {
      color: "black"
    },
    descriptionClassName: "!text-black",
    className: "!bg-green-100 !text-black",
    action,
  }),
}