// CORS for the mirror's release files, for the web build of vibeBMS.
//
//   https://mirror.vibebms.workers.dev/<event>/<file>
//     -> https://github.com/vibeBMS/BMS/releases/download/<event>/<file>
//
// GitHub's release downloads carry no CORS headers, so a web page cannot
// read them. This passes them through with those headers, for this
// mirror's files only (an event tag and a file name as the mirror names
// them), to the pages listed in ORIGINS. Bodies are streamed, not held.

const RELEASES = "https://github.com/vibeBMS/BMS/releases/download/";
const ORIGINS = [
  /^https:\/\/vibebms\.github\.io$/,
  /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/,
];
const TAG = /^[a-z0-9]{1,32}$/;
const FILE = /^(\d{1,4}(\+\d{1,2})?\.[a-z0-9]{1,5}|index\.json)$/i;

export default {
  async fetch(request) {
    const origin = request.headers.get("Origin") || "";
    const allowed = ORIGINS.some((o) => o.test(origin));
    const cors = {
      "Access-Control-Allow-Origin": allowed ? origin : "null",
      "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
      "Access-Control-Allow-Headers": "Range",
      "Access-Control-Expose-Headers": "Content-Length, Content-Range",
      "Vary": "Origin",
    };
    if (request.method === "OPTIONS") {
      return new Response(null, { status: allowed ? 204 : 403, headers: cors });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("method not allowed", { status: 405, headers: cors });
    }
    if (!allowed) {
      return new Response("this proxy serves vibeBMS pages only", { status: 403, headers: cors });
    }
    const [tag, file, ...rest] = new URL(request.url).pathname.split("/").filter(Boolean);
    if (rest.length || !TAG.test(tag || "") || !FILE.test(file || "")) {
      return new Response("not a mirror file", { status: 404, headers: cors });
    }
    const upstream = await fetch(RELEASES + tag + "/" + file, {
      method: request.method,
      headers: request.headers.has("Range") ? { Range: request.headers.get("Range") } : {},
      redirect: "follow",
    });
    const headers = new Headers(cors);
    for (const h of ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified"]) {
      const v = upstream.headers.get(h);
      if (v) headers.set(h, v);
    }
    headers.set("Cache-Control", "public, max-age=86400");
    return new Response(upstream.body, { status: upstream.status, headers });
  },
};
