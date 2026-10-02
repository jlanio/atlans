import { redirect } from "next/navigation";
import { destinoDaEntrada } from "@/lib/entrada";

// O cadastro virou um painel do modal de entrada da Home (`components/home/
// entrada/`). Esta rota fica pelos links antigos: manda para a Home com o
// modal aberto no cadastro.
export default function RegisterPage() {
  redirect(destinoDaEntrada("cadastro"));
}
