<!--
  Atlans PR template. It is a guide, not a form: fill in what makes
  sense and delete what does not apply. Describe only your code
  changes — no credentials, tokens or internal data.
-->

## What and why

<!-- One or two sentences: what this PR changes and which problem it solves. -->


## Changes

<!-- The main points of the diff — one line per relevant change. -->
-

## How to test

<!--
  What you ran, and what can be checked. Examples by area:
    desktop/    → npm run typecheck && npm test
    web/        → npm run lint && npm test
    flow/ and API → pytest
  Include the manual steps when there are any (UI flow, deep link, node execution).
-->
-

## Impact and risks

<!-- Check what applies and give details below. -->

- [ ] Database migration (describe it; say whether it is reversible)
- [ ] Breaking change (API, node contract, config)
- [ ] Touches security (auth, mTLS, credentials, isolation, CSP)
- [ ] Changes environment variables or the build/CD process
- [ ] None of the above


## Checklist

- [ ] Tests covering the change (or a justification of why not)
- [ ] `typecheck`/`lint` and the affected area's suite passing locally
- [ ] No secrets, tokens or sensitive data in the diff
- [ ] Documentation updated where it made sense
- [ ] First PR: I have accepted the CLA (CLA.md and CONTRIBUTING.md, at the repository root, explain how)

## Evidence

<!-- Screenshots or a recording for UI changes (web/desktop); logs/output for everything else. -->


## Pending items / follow-ups

<!-- What was deliberately left out and becomes an issue or the next PR. -->
