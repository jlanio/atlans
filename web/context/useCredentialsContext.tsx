'use client'
import { createContext, Dispatch, PropsWithChildren, SetStateAction, useContext, useMemo, useState } from "react";
import { ICredentials } from "@/service/types";

interface ICredentialsContext {
  credentials: ICredentials[]
  setCredentialsContext: Dispatch<SetStateAction<ICredentialsContext>>
}

const CredentialsContext = createContext<ICredentialsContext>({} as ICredentialsContext)

export const useCredentialsContext = () => {
  return useContext(CredentialsContext);
};

export const CredentialsContextProvider = ({ children }: PropsWithChildren) => {
  const [data, setData] = useState<ICredentialsContext>({ credentials: [], setCredentialsContext: () => {} });
  // useMemo: sem ele o `value` é um objeto novo a cada render do provider, e
  // todo consumidor de useCredentialsContext re-renderiza mesmo sem mudança.
  const value: ICredentialsContext = useMemo(
    () => ({ ...data, setCredentialsContext: setData }),
    [data],
  );

  return <CredentialsContext.Provider value={value}>{children}</CredentialsContext.Provider>;
};
