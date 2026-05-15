import { spawn, ChildProcessWithoutNullStreams } from "node:child_process";
import * as readline from "node:readline";
import path from "node:path";

// `next dev` runs from the frontend/ directory; the Python packages live one
// level up at the project root.
export const PROJECT_ROOT = path.resolve(process.cwd(), "..");

export type StreamMsg =
  | { type: "log"; line: string }
  | { type: "manifest"; manifest: unknown }
  | { type: "done"; exitCode: number | null; ok: boolean };

/**
 * Spawn a Python module and return an NDJSON ReadableStream of its output.
 * Each line of stdout/stderr is forwarded as a `log` message; on exit a
 * `done` message is sent and the stream closes.
 */
export function spawnPythonStream(
  args: string[],
  options?: { preEmit?: StreamMsg[] }
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream<Uint8Array>({
    start(controller) {
      const emit = (msg: StreamMsg) =>
        controller.enqueue(encoder.encode(JSON.stringify(msg) + "\n"));

      for (const msg of options?.preEmit ?? []) emit(msg);

      let proc: ChildProcessWithoutNullStreams;
      try {
        proc = spawn("python3", args, {
          cwd: PROJECT_ROOT,
          env: { ...process.env, PYTHONUNBUFFERED: "1" },
        });
      } catch (err) {
        emit({ type: "log", line: `[spawn-error] ${String(err)}` });
        emit({ type: "done", exitCode: -1, ok: false });
        controller.close();
        return;
      }

      readline
        .createInterface({ input: proc.stdout })
        .on("line", (line) => emit({ type: "log", line }));
      readline
        .createInterface({ input: proc.stderr })
        .on("line", (line) => emit({ type: "log", line: `[stderr] ${line}` }));

      proc.on("error", (err) => {
        emit({ type: "log", line: `[error] ${err.message}` });
      });
      proc.on("exit", (code) => {
        emit({ type: "done", exitCode: code, ok: code === 0 });
        controller.close();
      });
    },
  });
}

export const NDJSON_HEADERS = {
  "Content-Type": "application/x-ndjson",
  "Cache-Control": "no-cache, no-transform",
} as const;
