"use client";

import { useCallback, useRef, useState } from "react";

export type RunStatus = "idle" | "running" | "ok" | "error";

export type LogLine = { text: string; stderr?: boolean };

type Msg =
  | { type: "log"; line: string }
  | { type: "manifest"; manifest: unknown }
  | { type: "done"; exitCode: number | null; ok: boolean };

/**
 * Hook that POSTs to an NDJSON-streaming endpoint and exposes the parsed
 * messages as React state.
 */
export function useNdjsonRun() {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [log, setLog] = useState<LogLine[]>([]);
  const [manifest, setManifest] = useState<unknown>(null);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setLog([]);
    setManifest(null);
    setExitCode(null);
  }, []);

  const run = useCallback(
    async (url: string, body: object) => {
      abortRef.current?.abort();
      reset();
      setStatus("running");

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      let res: Response;
      try {
        res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: ctrl.signal,
        });
      } catch (err) {
        setLog((l) => [...l, { text: `[fetch] ${String(err)}`, stderr: true }]);
        setStatus("error");
        return;
      }

      if (!res.ok || !res.body) {
        const body = await res.text().catch(() => "");
        setLog((l) => [
          ...l,
          { text: `HTTP ${res.status}: ${body}`, stderr: true },
        ]);
        setStatus("error");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let nl: number;
        while ((nl = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, nl);
          buffer = buffer.slice(nl + 1);
          if (!line.trim()) continue;
          let msg: Msg;
          try {
            msg = JSON.parse(line);
          } catch {
            setLog((l) => [...l, { text: line }]);
            continue;
          }
          if (msg.type === "log") {
            const stderr = msg.line.startsWith("[stderr]");
            setLog((l) => [...l, { text: msg.line, stderr }]);
          } else if (msg.type === "manifest") {
            setManifest(msg.manifest);
          } else if (msg.type === "done") {
            setExitCode(msg.exitCode);
            setStatus(msg.ok ? "ok" : "error");
          }
        }
      }
    },
    [reset]
  );

  return { status, log, manifest, exitCode, run, reset };
}
