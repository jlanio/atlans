import { redirect } from "next/navigation";
import { destinoDaVerificacao } from "@/lib/entrada";

// A tela de "Verifique seu e-mail" virou um painel do modal de entrada da Home
// (`components/home/entrada/painel-verificar.tsx`). Esta rota fica porque é o
// que está escrito nos e-mails JÁ ENVIADOS (`auth_router.py` monta
// `{FRONTEND_URL}/verify-email?token=…` na criação da conta e no reenvio): ela
// leva o token para a Home, onde o painel o gasta no GET.
//
// Sem token, cai no mesmo painel sem token — a tela de "abra o link do e-mail",
// com o reenvio —, que é o que a página mostrava a quem chegava direto.
//
// Era a última página do modelo antigo (`AuthShell`) neste fluxo: com ela, todo
// o caminho de conta (entrar, criar, verificar, esquecer e redefinir a senha)
// acontece sem sair do globo.
export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaVerificacao(typeof sp.token === "string" ? sp.token : undefined));
}
