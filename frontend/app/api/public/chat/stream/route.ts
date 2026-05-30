/**
 * Next.js App Router route handler for SSE streaming.
 *
 * The built-in next.config.mjs rewrite proxy buffers the entire response
 * before forwarding it to the browser, which breaks Server-Sent Events.
 * This dedicated route handler bypasses that buffering by piping the
 * backend stream directly to the browser using the Web Streams API.
 */

import { NextRequest } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8080";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await fetch(`${BACKEND_URL}/api/public/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body,
    // @ts-ignore — Node 18 fetch supports this, types may lag
    duplex: "half",
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({ error: `Upstream error ${upstream.status}` }),
      { status: upstream.status, headers: { "Content-Type": "application/json" } }
    );
  }

  // Pipe the upstream SSE stream straight through — no buffering
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type":      "text/event-stream",
      "Cache-Control":     "no-cache",
      "X-Accel-Buffering": "no",
      Connection:          "keep-alive",
    },
  });
}
