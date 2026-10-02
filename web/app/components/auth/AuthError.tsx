"use client";

import { TbAlertCircle, TbLock, TbMailExclamation } from "react-icons/tb";
import { useTextos } from "@/app/components/home/i18n";

/* Superfície de erro inline das telas de autenticação, extraída do login. É um
   bloco persistente com `role="alert"` (o cadastro usava toast efêmero, que
   some antes do usuário ler) e três variantes por status:
   - `locked`  (429 / conta bloqueada) → laranja + cadeado
   - `emailNotVerified` (403) → amarelo + malote, com atalho de reenvio
   - padrão → vermelho + alerta
   As cores são literais de status (exceção documentada do contrato §6). */
export interface AuthErrorInfo {
  message: string;
  locked?: boolean;
  emailNotVerified?: boolean;
}

export function AuthError({
  error,
  onReenviarVerificacao,
}: {
  error: AuthErrorInfo;
  /* O atalho do 403: troca para o painel de verificação do mesmo modal. Era um
     `<Link href="/verify-email">` — navegar leva para fora da Home e joga fora
     a mensagem que espera o login, o mesmo motivo que tirou o link do "Esqueceu
     a senha?". Sem a callback o atalho não aparece: quem não tem para onde
     mandar não deve oferecer o caminho. */
  onReenviarVerificacao?: () => void;
}) {
  const t = useTextos().entrada.auth;
  return (
    <div
      role="alert"
      className={`flex flex-col gap-2 rounded-lg px-3 py-2.5 text-sm ${
        error.locked
          ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
          : error.emailNotVerified
            ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
            : "bg-red-500/10 text-red-400 border border-red-500/20"
      }`}
    >
      <div className="flex items-start gap-2">
        {error.locked ? (
          <TbLock className="shrink-0 mt-0.5" size={14} aria-hidden="true" />
        ) : error.emailNotVerified ? (
          <TbMailExclamation className="shrink-0 mt-0.5" size={14} aria-hidden="true" />
        ) : (
          <TbAlertCircle className="shrink-0 mt-0.5" size={14} aria-hidden="true" />
        )}
        <span>{error.message}</span>
      </div>
      {error.emailNotVerified && onReenviarVerificacao && (
        <button
          type="button"
          onClick={onReenviarVerificacao}
          className="ml-5 inline-flex items-center min-h-10 self-start rounded-sm text-xs underline underline-offset-2 text-yellow-400 hover:text-yellow-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {t.reenviarVerificacao}
        </button>
      )}
    </div>
  );
}
