# Security

## How to report a vulnerability

Do not open a public issue. Use GitHub's private reporting: in the
**Security** tab of the official repository, **Report a vulnerability**. Only the
maintainers read it.

If the button does not appear (private reporting is turned off), open an issue
asking for a private contact for a security problem, without any details
of it. The reply provides the channel.

It helps a great deal to include:

- what the flaw allows (reading another account's data, executing code on the
  server or on the executor, taking the service down…);
- how to reproduce it, with the version or the commit;
- whether it depends on some configuration (`.env` variables, an enrolled
  executor, a specific node).

The reply comes through the same channel. Once the fix is published, the repository's security
advisory describes what it was and credits the person who reported it, if that
person so wishes.

## Supported versions

Only the most recent version (the latest `vX.Y.Z` tag of the official repository)
receives security fixes. On an earlier version, the fix is to update.

## What each installation is responsible for

Atlans is installed by those who use it. The fix arrives through the repository; applying it
is the responsibility of each installation: updating the code and the images, and running the migrations
when there are any ([docs/operations.md](docs/operations.md)).
