import { NextRequest } from "next/server";
import { spawnPythonStream, NDJSON_HEADERS } from "@/lib/spawn-stream";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { file, connect = "127.0.0.1:9443" } = await req.json();
  if (typeof file !== "string" || !file) {
    return new Response(JSON.stringify({ error: "missing 'file'" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const stream = spawnPythonStream([
    "-m",
    "approach_a_mtls.sender",
    "--connect",
    connect,
    "--file",
    file,
  ]);

  return new Response(stream, { headers: NDJSON_HEADERS });
}
