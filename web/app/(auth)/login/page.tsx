import { redirect } from "next/navigation";
import { caminhoInterno, destinoDaEntrada } from "@/lib/entrada";

// The login screen became the Home's sign-in modal (`components/home/entrada/`).
// This route stays for old links, for next-auth's `pages.signIn` and for the
// "Voltar para login" of the recover/reset/verify screens: it sends to the
// Home with the modal open, carrying the `callbackUrl` when it is internal.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaEntrada("entrar", caminhoInterno(sp.callbackUrl)));
}
