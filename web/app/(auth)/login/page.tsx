import { redirect } from "next/navigation";
import { caminhoInterno, destinoDaEntrada } from "@/lib/entrada";

// A tela de login virou o modal de entrada da Home (`components/home/entrada/`).
// Esta rota fica pelos links antigos, pelo `pages.signIn` do next-auth e pelo
// "Voltar para login" das telas de recuperar/redefinir/verificar: ela manda
// para a Home com o modal aberto, levando o `callbackUrl` quando é interno.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaEntrada("entrar", caminhoInterno(sp.callbackUrl)));
}
