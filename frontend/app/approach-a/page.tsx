"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useNdjsonRun } from "@/lib/use-ndjson";

export default function ApproachAPage() {
  const [file, setFile] = useState("./testfile.bin");
  const [connect, setConnect] = useState("127.0.0.1:9443");
  const { status, log, run } = useNdjsonRun();
  const logRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    fetch("/api/check-file?file=payload.bin")
      .then((res) => res.json())
      .then((data) => {
        if (data.exists) {
          setFile("./payload.bin");
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const hashLine = [...log].reverse().find((l) =>
    /^SHA-256:|Result:/.test(l.text)
  );

  return (
    <main>
      <p style={{ marginBottom: "1rem" }}>
        <Link href="/">← Back</Link>
      </p>
      <h1>Approach A — mTLS 1.3 Direct Streaming</h1>
      <p className="lede">
        Streams a file inside a mutually-authenticated TLS 1.3 connection. The
        receiver must be running before you click Send.
      </p>

      <div className="panel">
        <div className="row">
          <label htmlFor="file">File path</label>
          <input
            id="file"
            type="text"
            value={file}
            onChange={(e) => setFile(e.target.value)}
            disabled={status === "running"}
          />
        </div>
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <label htmlFor="connect">Receiver</label>
          <input
            id="connect"
            type="text"
            value={connect}
            onChange={(e) => setConnect(e.target.value)}
            disabled={status === "running"}
          />
        </div>
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <button
            disabled={status === "running"}
            onClick={() => run("/api/approach-a/send", { file, connect })}
          >
            {status === "running" ? "Sending…" : "Send via mTLS"}
          </button>
          <StatusBadge status={status} />
        </div>
      </div>

      {hashLine && (
        <div className="panel">
          <div className="kv">{hashLine.text}</div>
        </div>
      )}

      <h2>Log</h2>
      <pre className="log" ref={logRef}>
        {log.length === 0 ? (
          <span style={{ color: "var(--muted)" }}>
            (no output yet — start the A receiver, then click Send)
          </span>
        ) : (
          log.map((l, i) => (
            <div key={i} className={l.stderr ? "stderr" : undefined}>
              {l.text}
            </div>
          ))
        )}
      </pre>
    </main>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "idle") return <span className="badge idle">idle</span>;
  if (status === "running") return <span className="badge run">running…</span>;
  if (status === "ok") return <span className="badge ok">✔ hash match</span>;
  return <span className="badge err">✘ failed</span>;
}
