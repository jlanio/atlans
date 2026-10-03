// Map of visual styles per credential type — single source of truth.
// Used by the listing at /credentials to give each row a visual anchor.
//
// The types here mirror CREDENTIAL_TYPE_SCHEMAS in app/core/credentials/schemas.py.
// If a new type lands in the backend without an entry here, the UI falls back
// to DEFAULT instead of breaking — and the test in
// __tests__/consts/credential-type-styles.test.ts points out the mismatch.
//
// Brand icon (react-icons/si) where one exists, Tabler for the rest. Mixing
// sets is established practice in the repo (see WorkflowIcons.ts, which
// combines eight), and recognizing "this is my Postgres credential" at a glance
// is the main point of this screen. The colored container evens out the stroke
// difference between the sets.
//
// S3 is Tabler's bucket: Simple Icons removed the Amazon brands, and
// `SiAmazons3` disappeared from react-icons 5.7. When imported, it came in as
// `undefined` and took down the whole credential list at the first S3 card.
//
// The classes are written out in full on purpose: Tailwind scans the code
// statically and does not see classes built by interpolation.

import { IconType } from "react-icons";
import { SiPostgresql, SiMysql } from "react-icons/si";
import { TbBucket, TbKey, TbUserShield, TbWebhook, TbMail, TbMap2, TbMapPin, TbPlugConnected } from "react-icons/tb";

export interface CredentialTypeStyle {
  icon: IconType;
  /** Background of the icon container. */
  bg: string;
  /** Icon stroke color. Always with a dark variant: `text-<cor>-600` alone
   *  falls below 4.5:1 over `bg-<cor>-500/10` in the dark theme. */
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
