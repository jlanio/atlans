// Mapa de estilos visuais por tipo de credencial — fonte única de verdade.
// Usado pela listagem em /credentials para dar uma âncora visual a cada linha.
//
// Os tipos aqui espelham CREDENTIAL_TYPE_SCHEMAS em app/core/credentials/schemas.py.
// Se um tipo novo entrar no backend sem entrada aqui, a UI cai no DEFAULT em vez
// de quebrar — e o teste em __tests__/consts/credential-type-styles.test.ts
// aponta a divergência.
//
// Ícone de marca (react-icons/si) onde existe, Tabler no resto. Misturar
// conjuntos é prática estabelecida no repo (ver WorkflowIcons.ts, que combina
// oito), e reconhecer "esta é minha credencial do Postgres" de relance é o
// ponto principal desta tela. O container colorido normaliza a diferença de
// traço entre os conjuntos.
//
// O S3 é o balde do Tabler: o Simple Icons tirou as marcas da Amazon, e o
// `SiAmazons3` sumiu do react-icons 5.7. Importado, ele vinha `undefined` e
// derrubava a lista inteira de credenciais no primeiro cartão de S3.
//
// As classes são escritas por extenso de propósito: o Tailwind varre o código
// estaticamente e não enxerga classe montada por interpolação.

import { IconType } from "react-icons";
import { SiPostgresql, SiMysql } from "react-icons/si";
import { TbBucket, TbKey, TbUserShield, TbWebhook, TbMail, TbMap2, TbMapPin, TbPlugConnected } from "react-icons/tb";

export interface CredentialTypeStyle {
  icon: IconType;
  /** Fundo do container do ícone. */
  bg: string;
  /** Cor do traço do ícone. Sempre com variante dark: `text-<cor>-600` sozinho
   *  fica abaixo de 4.5:1 sobre `bg-<cor>-500/10` no tema escuro. */
  fg: string;
}

export const CREDENTIAL_TYPE_STYLES: Record<string, CredentialTypeStyle> = {
  postgresql:    { icon: SiPostgresql, bg: "bg-blue-500/10",    fg: "text-blue-600 dark:text-blue-400"       },
  mysql:         { icon: SiMysql,      bg: "bg-amber-500/10",   fg: "text-amber-600 dark:text-amber-400"     },
  s3:            { icon: TbBucket,     bg: "bg-violet-500/10",  fg: "text-violet-600 dark:text-violet-400"   },
  http_bearer:   { icon: TbKey,        bg: "bg-emerald-500/10", fg: "text-emerald-600 dark:text-emerald-400" },
  http_basic:    { icon: TbUserShield, bg: "bg-cyan-500/10",    fg: "text-cyan-600 dark:text-cyan-400"       },
  webhook_token: { icon: TbWebhook,    bg: "bg-rose-500/10",    fg: "text-rose-600 dark:text-rose-400"       },
  smtp:          { icon: TbMail,       bg: "bg-sky-500/10",     fg: "text-sky-600 dark:text-sky-400"         },
  wfs:           { icon: TbMap2,       bg: "bg-teal-500/10",    fg: "text-teal-600 dark:text-teal-400"       },
  geoserver_authkey: { icon: TbMapPin, bg: "bg-lime-500/10",    fg: "text-lime-600 dark:text-lime-400"       },
};

export const DEFAULT_CREDENTIAL_TYPE_STYLE: CredentialTypeStyle = {
  icon: TbPlugConnected,
  bg: "bg-muted",
  fg: "text-muted-foreground",
};

export function getCredentialTypeStyle(type: string | undefined | null): CredentialTypeStyle {
  if (!type) return DEFAULT_CREDENTIAL_TYPE_STYLE;
  return CREDENTIAL_TYPE_STYLES[type] ?? DEFAULT_CREDENTIAL_TYPE_STYLE;
}
