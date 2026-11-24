import { NextRequest } from "next/server";

async function proxyRequest(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const apiKey = process.env.API_KEY?.trim();
  if (!apiKey) {
    return Response.json(
      {
        error: {
          code: "PROXY_MISCONFIGURED",
          message: "Server API_KEY is not configured",
          details: {},
        },
      },
      { status: 500 }
    );
  }

  const { path } = await context.params;
  if (!path || path.length === 0 || path.some((seg) => seg === ".." || seg.includes("\\"))) {
    return Response.json(
      {
        error: {
          code: "INVALID_PATH",
          message: "Invalid upstream API path",
          details: {},
        },
      },
      { status: 400 }
    );
  }

  const upstreamBase = (process.env.API_INTERNAL_URL || "http://incidentiq-api:8000").replace(
    /\/+$/,
    ""
  );
  const targetUrl = `${upstreamBase}/v1/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  headers.set("X-API-Key", apiKey);

  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  const accept = req.headers.get("accept");
  if (accept) headers.set("Accept", accept);

  const forwardedFor = req.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("X-Forwarded-For", forwardedFor);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, init);
  } catch (err) {
    return Response.json(
      {
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: `Failed to reach IncidentIQ API: ${err instanceof Error ? err.message : String(err)}`,
          details: {},
        },
      },
      { status: 502 }
    );
  }

  const upstreamContentType = upstream.headers.get("content-type") || "application/json";
  if (upstreamContentType.includes("text/event-stream")) {
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstreamContentType,
      "Cache-Control": "no-store",
    },
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
