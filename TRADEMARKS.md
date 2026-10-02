# The Atlans trademark

The Atlans code is free: AGPL-3.0-only, see [LICENSE](LICENSE). The name
**Atlans**, the form **Atlans.app** and the logos (the glyph of the two connected
nodes, the web icon and those of the desktop app) are not: they are trademarks of the
project's holder, the person who maintains the official repository, and the code license grants no
right to use them. This page states what you may do without asking.

The goal is a single one: whoever sees the name Atlans must know they are looking at the Atlans
published by the holder, and not at a version altered by someone else.

## Allowed, without asking

- Referring to Atlans by name: in texts, classes, comparisons and in code ("a
  fork of Atlans", "based on Atlans", "compatible with Atlans").
- Installing Atlans, with or without modifications, for yourself or for your
  organization, and keeping it with the name and the logos.
- Redistributing, without modification, the code or the installers published by the
  holder, with the name and the logos as they came.

## You must change the name and the logos

- When distributing a modified version, as code or as an installer.
- When offering Atlans, modified or not, as a service to people outside
  your organization.

In these cases, use a different name and different logos. Saying that your version is
"based on Atlans" remains permitted, and the AGPL continues to apply to the code
(including the obligation to offer the source code to those who use it over a network, section 13).

## Never, without written authorization

- Using "Atlans", or a name similar enough to cause confusion, in the name of a
  company, product, service or domain.
- Suggesting that the holder endorses, certifies or maintains your product or service.
- Altering the logos or using them in your materials.

To request an authorization, open an issue in the official repository.

## Where the name and the logos are

For those who are going to change them:

- **Logos**: `web/app/icon.png`, `web/app/favicon.ico`, the glyph in
  `web/app/components/sidebar/marca.tsx`, its animated version in
  `web/app/components/home/assistente/marca-animada.tsx`, and the icons and the
  installer image in `desktop/build/`.
- **Name**: the web title (`web/app/layout.tsx`), the sidebar brand
  (`marca.tsx`), the sign-in screen, the email templates
  (`app/templates/email/`), the default sender (`EMAIL_FROM`) and the desktop app:
  the `productName` in `desktop/package.json` and, in
  `desktop/electron-builder.yml`, the `productName`, the `shortcutName`, the
  protocol name ("Atlans Studio") and the `copyright` line.
  `git grep -nw Atlans` finds the rest.
- **The desktop app's identifiers**: the `appId` (`app.atlans.executor`, in
  `desktop/electron-builder.yml`) and the scheme of the enrollment links,
  `atlans://` (the same file and the `PROTOCOLO` in
  `desktop/src/main/deeplink.ts`). They do not appear as a trademark, but an app
  distributed with the same ones is confused with the official one on Windows: one installs
  over the other, and the links open the wrong app. A fork that distributes its
  own app changes both.

The other technical names (the `atlans-*` package, the volume, the step-ca
provisioner, the `ATLANS_*` variables) are not visible to users and may stay.

## The name on screen

The published code shows "Atlans" in the sidebar, on the sign-in screen and in the
tab title. The form with the domain is the holder's installation, and does not go into the
code: each installation defines the name it shows in `NOME_NA_TELA`, in the `.env`
([self-hosting](docs/self-hosting.md)). Whoever needs to change the
name, under the rules above, changes it there — and the logos, in the files listed.
