import { redirect } from "next/navigation";
import { destinoDaEntrada } from "@/lib/entrada";

// A tela de "Esqueceu a senha?" virou um painel do modal de entrada da Home
// (`components/home/entrada/painel-recuperar.tsx`). Esta rota fica pelos links
// antigos — e-mails já enviados, favoritos, o "Solicitar novo link" de
// qualquer página velha em cache: ela manda para a Home com o painel aberto.
export default function ForgotPasswordPage() {
  redirect(destinoDaEntrada("recuperar"));
}
