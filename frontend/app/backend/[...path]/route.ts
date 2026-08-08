import { NextRequest } from "next/server";

const backendOrigin = process.env.DJANGO_API_ORIGIN || "http://127.0.0.1:8000";

type RouteContext = {
  params: {
    path: string[];
  };
};

function buildTargetUrl(request: NextRequest, path: string[]) {
  const sourceUrl = new URL(request.url);
  const pathname = `/${path.join("/")}/`;
  const targetUrl = new URL(pathname, backendOrigin);
  targetUrl.search = sourceUrl.search;

  return targetUrl.toString();
}

function buildRequestHeaders(request: NextRequest) {
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  headers.delete("accept-encoding");

  return headers;
}

function buildResponseHeaders(response: Response) {
  const headers = new Headers(response.headers);

  headers.delete("content-encoding");
  headers.delete("content-length");
  headers.delete("transfer-encoding");
  headers.delete("connection");

  return headers;
}

async function proxy(request: NextRequest, context: RouteContext) {
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstreamResponse = await fetch(
    buildTargetUrl(request, context.params.path),
    {
      method: request.method,
      headers: buildRequestHeaders(request),
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual"
    }
  );

  return new Response(await upstreamResponse.arrayBuffer(), {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: buildResponseHeaders(upstreamResponse)
  });
}

export const dynamic = "force-dynamic";

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
