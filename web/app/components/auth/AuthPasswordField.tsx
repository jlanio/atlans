"use client";

import * as React from "react";
import { useState } from "react";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { TbAlertCircle, TbEye, TbEyeOff } from "react-icons/tb";
import { useTextos } from "@/app/components/home/i18n";

/* Campo de senha padronizado (login, cadastro, redefinição): mostrar/ocultar +
   aviso de Caps Lock. Antes só o login tinha os dois; cadastro e redefinição
   usavam `<Input type="password">` cru. Concentrar aqui garante paridade e uma
   fonte única para o comportamento.

   `labelRight` acomoda o "Esqueceu a senha?" do login; `children` acomoda o
   medidor de força e o aviso de divergência que ficam sob o campo. */
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

  // Caps Lock é lido do EVENTO, não de um estado global: não existe API para
  // consultar a tecla, só `getModifierState` durante um evento de teclado. Fica
  // no campo de senha porque é lá que a maiúscula involuntária não aparece na
  // tela — a falha que o usuário não consegue diagnosticar sozinho.
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
      {/* O botão fica DENTRO da moldura do campo, e o input ganha `pr-11` para o
          texto não correr por baixo dele. */}
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
          // `tabIndex={-1}`: quem navega por teclado quer sair da senha direto
          // para o botão de enviar, não parar num controle que só muda a
          // exibição. Alvo de 40px (h-10 w-10) para o toque no telefone.
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
