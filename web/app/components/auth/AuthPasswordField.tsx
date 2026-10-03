"use client";

import * as React from "react";
import { useState } from "react";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { TbAlertCircle, TbEye, TbEyeOff } from "react-icons/tb";
import { useTextos } from "@/app/components/home/i18n";

/* Standardized password field (login, sign-up, reset): show/hide + Caps Lock
   warning. Before, only login had both; sign-up and reset used a raw
   `<Input type="password">`. Concentrating it here guarantees parity and a
   single source for the behavior.

   `labelRight` accommodates login's "Esqueceu a senha?"; `children`
   accommodates the strength meter and the mismatch warning that sit under the field. */
interface AuthPasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  disabled?: boolean;
  required?: boolean;
  minLength?: number;
  labelRight?: React.ReactNode;
  children?: React.ReactNode;
}

export function AuthPasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  disabled,
  required,
  minLength,
  labelRight,
  children,
}: AuthPasswordFieldProps) {
  const t = useTextos().entrada.auth;
  const [show, setShow] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  // Caps Lock is read from the EVENT, not from a global state: there is no API to
  // query the key, only `getModifierState` during a keyboard event. It lives in
  // the password field because that is where the involuntary uppercase does not
  // show on screen — the failure the user cannot diagnose alone.
  function sincronizarCapsLock(e: React.KeyboardEvent<HTMLInputElement>) {
    setCapsLock(e.getModifierState?.("CapsLock") ?? false);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id} className="auth-label text-sm">
          {label}
        </Label>
        {labelRight}
      </div>
      {/* The button sits INSIDE the field's frame, and the input gets `pr-11` so
          the text does not run under it. */}
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          disabled={disabled}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyUp={sincronizarCapsLock}
          onKeyDown={sincronizarCapsLock}
          onBlur={() => setCapsLock(false)}
          className="auth-input h-11 pr-11 text-sm"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          disabled={disabled}
          // `tabIndex={-1}`: keyboard users want to go from the password straight
          // to the submit button, not stop at a control that only changes the
          // display. A 40px target (h-10 w-10) for touch on the phone.
          tabIndex={-1}
          aria-label={show ? t.ocultarSenha : t.mostrarSenha}
          className="absolute right-1 top-1/2 -translate-y-1/2 flex h-10 w-10 items-center justify-center rounded-md text-white/45 transition-colors hover:text-white/80 disabled:opacity-40"
        >
          {show ? <TbEyeOff size={17} aria-hidden="true" /> : <TbEye size={17} aria-hidden="true" />}
        </button>
      </div>

      {capsLock && (
        <p className="flex items-center gap-1.5 text-xs text-amber-400/90" role="status">
          <TbAlertCircle size={13} className="shrink-0" aria-hidden="true" />
          {t.capsLock}
        </p>
      )}

      {children}
    </div>
  );
}
