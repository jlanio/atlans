"use client";

import { TbAlertCircle, TbLock, TbMailExclamation } from "react-icons/tb";
import { useTexts } from "@/app/components/home/i18n";

/* Inline error surface of the authentication screens, extracted from login. It
   is a persistent block with `role="alert"` (sign-up used an ephemeral toast,
   which vanished before the user could read it) and three variants by status:
   - `locked`  (429 / locked account) → orange + padlock
   - `emailNotVerified` (403) → yellow + mailbag, with a resend shortcut
   - default → red + alert
   The colors are status literals (documented exception of contract §6). */
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
  /* The 403 shortcut: switches to the verification panel of the same modal. It
     was a `<Link href="/verify-email">` — navigating leads outside the Home and
     throws away the message waiting for login, the same reason that removed the
     link from "Esqueceu a senha?". Without the callback the shortcut does not
     appear: whoever has nowhere to send it should not offer the path. */
  onReenviarVerificacao?: () => void;
}) {
  const t = useTexts().entrada.auth;
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
