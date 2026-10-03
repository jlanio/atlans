import { redirect } from "next/navigation";
import { destinoDaVerificacao } from "@/lib/entrada";

// The "Verifique seu e-mail" (verify your email) screen became a panel of the
// Home's sign-in modal (`components/home/entrada/painel-verificar.tsx`). This route
// stays because it is what is written in emails ALREADY SENT (`auth_router.py`
// builds `{FRONTEND_URL}/verify-email?token=…` on account creation and on resend):
// it carries the token to the Home, where the panel spends it in the GET.
//
// Without a token, it lands on the same panel without a token — the "open the
// email link" screen, with resend — which is what the page showed to whoever
// arrived directly.
//
// It was the last page of the old model (`AuthShell`) in this flow: with it, the
// whole account path (sign in, sign up, verify, forget and reset the password)
// happens without leaving the globe.
export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaVerificacao(typeof sp.token === "string" ? sp.token : undefined));
}
