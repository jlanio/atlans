// desktop/scripts/segredos.mjs
//
// What must never be copied from executor/ and flow/ into the installer.
//
// The app keeps its own config and certificate under %APPDATA%\AtlansExecutor;
// anything of the kind inside the source tree belongs to the developer who
// built it. A local build copies the working tree as it is, gitignored files
// included (`.env.local`, `.env.bak`, a `.pem` left over from a test), so the
// list is by pattern, at any depth, and not by the two paths someone
// remembered.

/** Names that carry developer secrets. */
const SEGREDOS = [
  /^\.env(\..*)?$/i,                 // .env, .env.local, .env.production.local, .env.bak…
  /\.(pem|key|p12|pfx)$/i,           // private keys and certificates
  /^(certs?|executor-certs)$/i,      // the cert folders of the executor and the dev scripts
]

/** Exceptions: `.env.example` is what seed_env_from_example copies on first boot. */
const PERMITIDOS = [/^\.env\.example$/i]

/** Is this file or folder NAME one that must stay out of the payload? */
export function ehSegredo(nome) {
  return !PERMITIDOS.some((re) => re.test(nome)) && SEGREDOS.some((re) => re.test(nome))
}
