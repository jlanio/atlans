import { redirect } from "next/navigation";
import { destinoDaRedefinicao } from "@/lib/entrada";

// The "Nova senha" (new password) screen became a panel of the Home's sign-in
// modal (`components/home/entrada/painel-redefinir.tsx`). This route stays because
// it is what is written in emails ALREADY SENT: it carries the token to the Home,
// where the panel uses it in the POST. Without a token, it lands on the panel that
// asks for a new link — what the "Link inválido" screen offered, in one step fewer.
//
// The token stays in the query, as it always was: it is single-use and short-lived,
// and the backend is what validates it.
export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaRedefinicao(typeof sp.token === "string" ? sp.token : undefined));
}
