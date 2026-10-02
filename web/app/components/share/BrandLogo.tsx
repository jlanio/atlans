import Link from "next/link";

/**
 * Identidade de marca do portal público (`/share`). O gradiente laranja é a
 * exceção de cor crua explicitamente permitida pelo contrato (§6 — logotipo de
 * marca como identidade), então fica isolado neste componente único para não
 * duplicar o hex entre a página de erro e o cabeçalho do visualizador. Sem
 * hooks: serve tanto no server component (`page.tsx`) quanto no client
 * (`WorkflowShareViewer`).
 */
export function BrandLogo({ size = "sm", href }: { size?: "sm" | "md"; href?: string }) {
  const marca = size === "md" ? "size-9 rounded-xl text-base" : "size-7 rounded-lg text-xs";
  const palavra = size === "md" ? "text-lg" : "text-sm";

  const conteudo = (
    <span className="inline-flex items-center gap-2">
      <span
        className={`flex items-center justify-center font-bold text-white ${marca}`}
        // Gradiente da marca (identidade permitida) — ver comentário do componente.
        style={{ background: "linear-gradient(135deg, #FF6A00, #FF9A00)" }}
        aria-hidden="true"
      >
        A
      </span>
      <span className={`font-semibold tracking-tight ${palavra}`}>
        atlans<span style={{ color: "#FF6A00" }}>.app</span>
      </span>
    </span>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="inline-flex items-center rounded-md outline-none transition-opacity hover:opacity-90 focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {conteudo}
      </Link>
    );
  }
  return conteudo;
}
