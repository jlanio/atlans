import { redirect } from "next/navigation";
import { destinoDaRedefinicao } from "@/lib/entrada";

// A tela de "Nova senha" virou um painel do modal de entrada da Home
// (`components/home/entrada/painel-redefinir.tsx`). Esta rota fica porque é o
// que está escrito nos e-mails JÁ ENVIADOS: ela leva o token para a Home, onde
// o painel o usa no POST. Sem token, cai no painel que pede um link novo — o
// que a tela "Link inválido" oferecia, em um passo a menos.
//
// O token continua na query, como sempre esteve: ele é de uso único e curto, e
// quem o valida é o backend.
export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  redirect(destinoDaRedefinicao(typeof sp.token === "string" ? sp.token : undefined));
}
