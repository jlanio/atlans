import { toast } from "sonner"

interface ToastAction {
  /** Action button text (e.g. "Desfazer"). */
  label: string
  /** Callback called on click — must perform the rollback or inverse action. */
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

  /** Warning (amber): the action completed, but with a caveat the user needs
   *  to know — e.g. it saved, but the schedule was not applied. */
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