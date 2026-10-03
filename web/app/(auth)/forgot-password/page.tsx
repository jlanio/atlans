import { redirect } from "next/navigation";
import { destinoDaEntrada } from "@/lib/entrada";

// The "Esqueceu a senha?" (forgot password) screen became a panel of the Home's
// sign-in modal (`components/home/entrada/painel-recuperar.tsx`). This route stays
// for old links — emails already sent, bookmarks, the "Solicitar novo link" of
// any old cached page: it sends to the Home with the panel open.
export default function ForgotPasswordPage() {
  redirect(destinoDaEntrada("recuperar"));
}
