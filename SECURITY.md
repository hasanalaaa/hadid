# Security Policy

## Threat model

Hadid is a **local-first** application. Your archive never leaves your
machine: there is no cloud component, no account, and no telemetry.

The built-in web app (`hadid serve`) is designed for loopback use only:

- Binds to `127.0.0.1` by default and warns when bound elsewhere.
- Validates the `Host` header on every request, which blocks
  **DNS-rebinding** attacks against local servers.
- Sends a strict `Content-Security-Policy`, `X-Content-Type-Options:
  nosniff`, and `Referrer-Policy: no-referrer` on every response; API
  responses are marked `Cache-Control: no-store`.
- Renders all conversation content via `textContent` (never `innerHTML`),
  so archived messages cannot inject script into the UI.
- Search input is token-quoted before reaching FTS5, so queries cannot
  break out of the match expression.

Do **not** expose `hadid serve` to untrusted networks; it has no
authentication by design.

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please open a **confidential issue** on the project:
https://github.com/USERNAME/hadid/issues (mark it confidential).
Include reproduction steps and impact. You will get a response as soon as
possible, and a fix will be prioritized over all other work.
