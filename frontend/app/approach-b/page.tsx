"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useNdjsonRun } from "@/lib/use-ndjson";

type Manifest = {
  file_id: string;
  filename: string;
  total_size: number;
  chunk_size: number;
  chunk_count: number;
  total_sha256: string;
  suite: { kem: string; kdf: string; enc: string };
  sender_ephemeral_pub: string;
  receiver_key_fingerprint: string;
  sender_signing_fingerprint: string;
};

export default function ApproachBPage() {
  const [file, setFile] = useState("./testfile.bin");
  const [out, setOut] = useState("./recv_b/testfile.bin");
  const [broker, setBroker] = useState("http://127.0.0.1:9080");

  const send = useNdjsonRun();
  const recv = useNdjsonRun();

  useEffect(() => {
    fetch("/api/check-file?file=payload.bin")
      .then((res) => res.json())
      .then((data) => {
        if (data.exists) {
          setFile("./payload.bin");
          setOut("./recv_b/payload.bin");
        }
      })
      .catch(() => {});
  }, []);

  const sendLogRef = useRef<HTMLPreElement>(null);
  const recvLogRef = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (sendLogRef.current) sendLogRef.current.scrollTop = sendLogRef.current.scrollHeight;
  }, [send.log]);
  useEffect(() => {
    if (recvLogRef.current) recvLogRef.current.scrollTop = recvLogRef.current.scrollHeight;
  }, [recv.log]);

  const manifest = recv.manifest as Manifest | null;
  const sigVerified = recv.log.some((l) => l.text.includes("Manifest signature: OK"));

  return (
    <main>
      <p style={{ marginBottom: "1rem" }}>
        <Link href="/">← Back</Link>
      </p>
      <h1>Approach B — Encrypted Envelope via Untrusted Broker</h1>
      <p className="lede">
        Sender encrypts chunks and signs a manifest, then uploads to a plain
        HTTP broker that never sees plaintext. The receiver verifies the
        signature, derives the file key, and decrypts. The broker must be
        running before you click Send.
      </p>

      <div className="panel">
        <div className="row">
          <label htmlFor="file">File path</label>
          <input id="file" type="text" value={file} onChange={(e) => setFile(e.target.value)} />
        </div>
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <label htmlFor="out">Output path</label>
          <input id="out" type="text" value={out} onChange={(e) => setOut(e.target.value)} />
        </div>
        <div className="row" style={{ marginTop: "0.5rem" }}>
          <label htmlFor="broker">Broker URL</label>
          <input id="broker" type="text" value={broker} onChange={(e) => setBroker(e.target.value)} />
        </div>
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <button
            disabled={send.status === "running"}
            onClick={() => send.run("/api/approach-b/send", { file, broker })}
          >
            {send.status === "running" ? "Sending…" : "1. Send"}
          </button>
          <button
            className="secondary"
            disabled={recv.status === "running" || send.status !== "ok"}
            onClick={() => recv.run("/api/approach-b/recv", { out, broker })}
          >
            {recv.status === "running" ? "Receiving…" : "2. Receive"}
          </button>
          <Badges send={send.status} recv={recv.status} />
        </div>
      </div>

      {manifest && (
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Manifest</h2>
          <div className="kv">
            <div><span className="k">file_id</span>{manifest.file_id}</div>
            <div><span className="k">filename</span>{manifest.filename}</div>
            <div><span className="k">total_size</span>{manifest.total_size.toLocaleString()} bytes</div>
            <div><span className="k">chunk_count</span>{manifest.chunk_count} × {manifest.chunk_size.toLocaleString()} bytes</div>
            <div><span className="k">suite</span>{manifest.suite.kem} / {manifest.suite.kdf} / {manifest.suite.enc}</div>
            <div><span className="k">total_sha256</span>{manifest.total_sha256}</div>
            <div><span className="k">receiver_key_fingerprint</span>{manifest.receiver_key_fingerprint.slice(0, 32)}…</div>
            <div><span className="k">sender_signing_fingerprint</span>{manifest.sender_signing_fingerprint.slice(0, 32)}…</div>
            <div style={{ marginTop: "0.5rem" }}>
              <span className="k">signature</span>
              {sigVerified ? (
                <span className="badge ok">✔ valid</span>
              ) : recv.status === "error" ? (
                <span className="badge err">✘ invalid</span>
              ) : (
                <span className="badge idle">pending</span>
              )}
            </div>
          </div>
        </div>
      )}

      <h2>Sender log</h2>
      <pre className="log" ref={sendLogRef}>
        {send.log.length === 0 ? (
          <span style={{ color: "var(--muted)" }}>(idle — start the broker, then click Send)</span>
        ) : (
          send.log.map((l, i) => (
            <div key={i} className={l.stderr ? "stderr" : undefined}>{l.text}</div>
          ))
        )}
      </pre>

      <h2>Receiver log</h2>
      <pre className="log" ref={recvLogRef}>
        {recv.log.length === 0 ? (
          <span style={{ color: "var(--muted)" }}>(idle — click Receive after Send completes)</span>
        ) : (
          recv.log.map((l, i) => (
            <div key={i} className={l.stderr ? "stderr" : undefined}>{l.text}</div>
          ))
        )}
      </pre>
    </main>
  );
}

function Badges({ send, recv }: { send: string; recv: string }) {
  const cls = (s: string) =>
    s === "ok" ? "badge ok" :
    s === "error" ? "badge err" :
    s === "running" ? "badge run" : "badge idle";
  const label = (s: string, kind: string) =>
    s === "ok" ? `${kind} ✔` :
    s === "error" ? `${kind} ✘` :
    s === "running" ? `${kind}…` : kind;
  return (
    <>
      <span className={cls(send)}>{label(send, "send")}</span>
      <span className={cls(recv)}>{label(recv, "recv")}</span>
    </>
  );
}
