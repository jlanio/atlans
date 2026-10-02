import { useUrlParam } from "@/app/hooks/useUrlParam"

export const useConfigNodeParams = () => {
  const { value: configNodeIdParam, set: setConfigNodeParam, remove: removeConfigNodeParam } =
    useUrlParam('cn')

  return { configNodeIdParam, setConfigNodeParam, removeConfigNodeParam }
}

