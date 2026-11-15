# CORS proxy for the web player

GitHub's release downloads carry no CORS headers, so the web build of
vibeBMS cannot read this mirror's files directly. `worker.js` (a Cloudflare
Worker) passes them through with those headers:

    https://mirror.vibebms.workers.dev/<event>/<file>
      -> https://github.com/vibeBMS/BMS/releases/download/<event>/<file>

It serves only this mirror's files (an event tag, then `NNN.ext`,
`NNN+K.ext` or `index.json`), only to the pages it lists (vibebms.github.io
and localhost), and streams the bodies (no CPU time to speak of; the free
plan's 100,000 requests a day are plenty).

## Deploy

Dashboard: Workers & Pages → Create → Start with Hello World → name it
`mirror` → Deploy → Edit code → replace it with `worker.js` → Deploy.

Or with wrangler, from this folder: `npx wrangler deploy`.

Check: `curl -H "Origin: https://vibebms.github.io" -I https://mirror.vibebms.workers.dev/bof22/index.json`
should answer 200 with `access-control-allow-origin: https://vibebms.github.io`.
