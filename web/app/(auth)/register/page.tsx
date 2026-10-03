import { redirect } from "next/navigation";
import { destinoDaEntrada } from "@/lib/entrada";

// Sign-up became a panel of the Home's sign-in modal (`components/home/
// entrada/`). This route stays for old links: it sends to the Home with the
// modal open on sign-up.
export default function RegisterPage() {
  redirect(destinoDaEntrada("cadastro"));
}
