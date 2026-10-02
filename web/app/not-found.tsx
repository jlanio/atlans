import Link from "next/link"

export default function NotFound() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6 text-white"
      style={{ background: "#07070F" }}
    >
      {/* Grid bg sutil */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,106,0,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,106,0,0.035) 1px, transparent 1px)",
          backgroundSize: "52px 52px",
        }}
      />

      {/* Glow central */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(255,106,0,0.07) 0%, transparent 70%)" }}
      />

      <div className="relative text-center max-w-md">
        {/* Logo */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-10 group">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white text-base"
            style={{ background: "linear-gradient(135deg,#FF6A00,#FF9A00)" }}
          >
            A
          </div>
          <span className="font-semibold text-lg tracking-tight">
            atlans<span style={{ color: "#FF6A00" }}>.app</span>
          </span>
        </Link>

        {/* Código de erro */}
        <div
          className="text-[7rem] font-black leading-none tracking-tighter mb-2 select-none"
          style={{
            background: "linear-gradient(135deg, #FF6A00 0%, #FF9A00 50%, rgba(255,106,0,0.3) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          404
        </div>

        <h1 className="text-xl font-semibold text-white mb-3">Página não encontrada</h1>

        <p className="text-muted-foreground text-sm leading-relaxed mb-8">
          O endereço que você tentou acessar não existe ou foi movido.
          <br className="hidden sm:block" />
          Verifique o link ou volte para a página inicial.
        </p>

        {/* Ações */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 font-semibold text-white rounded-xl px-6 py-3 transition-all duration-200 hover:-translate-y-0.5"
            style={{ background: "linear-gradient(135deg,#FF6A00,#FF8F00)", boxShadow: "0 4px 20px rgba(255,106,0,0.3)" }}
          >
            Ir para a página inicial
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 font-medium rounded-xl px-6 py-3 transition-all duration-200 hover:-translate-y-0.5"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "rgba(255,255,255,0.8)",
            }}
          >
            Entrar
          </Link>
        </div>
      </div>
    </div>
  )
}
