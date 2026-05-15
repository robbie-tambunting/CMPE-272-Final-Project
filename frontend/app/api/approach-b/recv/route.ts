import { NextRequest } from "next/server";
import {
  spawnPythonStream,
  NDJSON_HEADERS,
  StreamMsg,
} from "@/lib/spawn-stream";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { out, broker = "http://127.0.0.1:9080" } = await req.json();
  if (typeof out !== "string" || !out) {
    return new Response(JSON.stringify({ error: "missing 'out'" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Pre-fetch the manifest so the UI can display it before logs start scrolling.
  const preEmit: StreamMsg[] = [];
  try {
    const latest = (await (await fetch(`${broker}/latest`)).text()).trim();
    const manifestRes = await fetch(`${broker}/${latest}/manifest.json`);
    if (manifestRes.ok) {
      const manifest = await manifestRes.json();
      preEmit.push({ type: "manifest", manifest });
    } else {
      preEmit.push({
        type: "log",
        line: `[warn] could not fetch manifest (HTTP ${manifestRes.status})`,
      });
    }
  } catch (err) {
    preEmit.push({
      type: "log",
      line: `[warn] manifest pre-fetch failed: ${String(err)}`,
    });
  }

  const stream = spawnPythonStream(
    [
      "-m",
      "approach_b_envelope.receiver",
      "--broker",
      broker,
      "--out",
      out,
    ],
    { preEmit }
  );

  return new Response(stream, { headers: NDJSON_HEADERS });
}
