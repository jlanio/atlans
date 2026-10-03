"use client";

import { TbCheck, TbX } from "react-icons/tb";
import { useTextos } from "@/app/components/home/i18n";

/* Password strength meter (sign-up and reset). Rules met in green (status
   literal, allowed); the pending ones used `text-muted-foreground` — the only
   theme token that leaked into the dark authentication scene — replaced by
   `auth-muted`, the supporting color of the auth pattern itself. */
export function AuthPasswordStrength({ password }: { password: string }) {
  const t = useTextos().entrada.auth.regrasDaSenha;
  const rules = [
    { label: t.minimo, ok: password.length >= 8 },
    { label: t.maiuscula, ok: /[A-Z]/.test(password) },
    { label: t.minuscula, ok: /[a-z]/.test(password) },
    { label: t.numero, ok: /[0-9]/.test(password) },
  ];
  if (!password) return null;
  return (
    <ul className="mt-1 space-y-0.5">
      {rules.map((r) => (
        <li
          key={r.label}
          className={`flex items-center gap-1.5 text-xs ${r.ok ? "text-green-400" : "auth-muted"}`}
        >
          {r.ok ? <TbCheck size={11} aria-hidden="true" /> : <TbX size={11} aria-hidden="true" />}
          {r.label}
        </li>
      ))}
    </ul>
  );
}
