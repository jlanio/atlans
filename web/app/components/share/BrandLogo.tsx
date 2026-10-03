import Link from "next/link";

/**
 * Brand identity of the public portal (`/share`). The orange gradient is the
 * raw-color exception explicitly allowed by the contract (§6 — brand logo as
 * identity), so it is isolated in this single component to avoid duplicating
 * the hex between the error page and the viewer header. No hooks: it works both
 * in the server component (`page.tsx`) and in the client
 * (`WorkflowShareViewer`).
 */
export function BrandLogo({ size = "sm", href }: { size?: "sm" | "md"; href?: string }) {
  const marca = size === "md" ? "size-9 rounded-xl text-base" : "size-7 rounded-lg text-xs";
  const palavra = size === "md" ? "text-lg" : "text-sm";

  const conteudo = (
    <span className="inline-flex items-center gap-2">
      <span
        className={`flex items-center justify-center font-bold text-white ${marca}`}
        // Brand gradient (allowed identity) — see the component comment.
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
