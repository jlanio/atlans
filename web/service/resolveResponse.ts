import { IResponse } from "./types"
import { AxiosError } from "axios"

export const resolveResponse = <T>(data?: T) => {
  return {
    status: 200,
    data,
    success: true
  } satisfies IResponse<T>
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const resolveAxiosError = (e: AxiosError<any, any>) => {
  // FastAPI retorna { detail: "..." }; outros backends podem usar { message: "..." }
  const msg: string | undefined =
    e.response?.data?.detail ??
    e.response?.data?.message ??
    undefined

  if (msg) {
    const corpo = e.response?.data ?? {}
    return {
      status: e.response?.status ?? 500,
      error: {
        name: "AxiosError",
        message: msg,
        // O código e a lista seguem para a tela: e o que permite oferecer
        // "remover mesmo assim" num 409 da politica de execucao.
        ...(typeof corpo.error === "string" ? { code: corpo.error } : {}),
        ...(Array.isArray(corpo.workspaces) ? { workspaces: corpo.workspaces } : {}),
      },
      success: false,
    } as IResponse<undefined>
  }

  return {
    error: { name: "AxiosError", message: "Erro inesperado." },
    status: e.response?.status ?? 500,
    success: false,
  } as IResponse<undefined>
}