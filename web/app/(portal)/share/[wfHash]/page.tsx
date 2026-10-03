import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { TbAlertTriangle } from "react-icons/tb";
import { Button } from "@/app/components/ui/button";
import { BrandLogo } from "@/app/components/share/BrandLogo";
import WorkflowShareViewer from "@/app/components/share/WorkflowShareViewer";
import type { PortalData } from "@/app/components/share/WorkflowShareViewer";

export const dynamic = "force-dynamic";

export default async function SharePage({
  params,
}: {
  params: Promise<{ wfHash: string }>;
}) {
  const { wfHash } = await params;
  const session = await auth();

  const headers: Record<string, string> = {};
  if (session?.user?.access_token) {
    headers["Authorization"] = `Bearer ${session.user.access_token}`;
  }

  const apiUrl = `${process.env.API_INTERNA}/artifacts/portal/${wfHash}`;
  let res: Response;
  try {
    res = await fetch(apiUrl, { headers, cache: "no-store" });
  } catch {
    return (
      <ErrorPage
        title="Servidor indisponível"
        message="Não foi possível conectar ao servidor. Tente novamente em instantes."
      />
    );
  }

  if (res.status === 401) {
    redirect(`/login?callbackUrl=/share/${wfHash}`);
  }

  if (res.status === 403) {
    return (
      <ErrorPage title="Acesso negado" message="Você não tem permissão para ver este portal.">
        <Button asChild variant="outline" size="sm" className="max-md:h-10">
          <Link href="/login">Entrar com outra conta</Link>
        </Button>
      </ErrorPage>
    );
  }

  if (!res.ok) {
    return (
      <ErrorPage title="Portal indisponível" message="Este portal não foi encontrado ou não está disponível." />
    );
  }

  const data: PortalData = await res.json();
  return <WorkflowShareViewer data={data} workflowHash={wfHash} />;
}

/**
 * The portal's error page (contract §3.2): `bg-background` background, a
 * centered `rounded-lg border bg-card shadow-xs` card with the destructive alert
 * circle. The brand stays at the top as identity; actions in an outline `Button`.
 * The 401 `redirect` does not go through here — only the snags that bring down
 * the portal's 1st (and only) load.
 */
function ErrorPage({ title, message, children }: { title: string; message: string; children?: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-6">
      <BrandLogo size="md" href="/" />
      <section
        aria-labelledby="portal-erro-titulo"
        className="flex w-full max-w-sm flex-col items-center justify-center gap-3 rounded-lg border border-destructive/20 bg-card px-6 py-14 text-center shadow-xs"
      >
        <div className="rounded-full border border-destructive/20 bg-destructive/10 p-3">
          <TbAlertTriangle size={26} className="text-destructive" aria-hidden="true" />
        </div>
        <div className="flex max-w-[360px] flex-col items-center gap-0.5">
          <h1 id="portal-erro-titulo" className="text-sm font-medium">{title}</h1>
          <p className="text-xs text-muted-foreground">{message}</p>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
            <Button asChild variant="outline" size="sm" className="max-md:h-10">
              <Link href="/">Ir para a página inicial</Link>
            </Button>
            {children}
          </div>
        </div>
      </section>
    </div>
  );
}
