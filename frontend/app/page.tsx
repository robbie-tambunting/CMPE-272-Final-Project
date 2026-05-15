import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>CMPE 272 — CIAA File Transfer Demo</h1>
      <p className="lede">
        Two architecturally distinct 4 GB-file transfer approaches with
        confidentiality, integrity, authentication, and availability guarantees.
      </p>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Approach A — mTLS 1.3 direct streaming</h2>
        <p>
          Transport-layer security. Receiver listens on <code>:9443</code> with
          client-cert verification; sender streams the file inside the TLS
          connection with a small framing protocol that supports resume and a
          final SHA-256 check.
        </p>
        <p>
          <Link href="/approach-a">→ Open Approach A</Link>
        </p>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0 }}>
          Approach B — encrypted envelope via untrusted broker
        </h2>
        <p>
          Application-layer security. Sender encrypts chunks with AES-256-GCM,
          signs a manifest with Ed25519, and uploads everything to a plain-HTTP
          broker. Receiver verifies the signature, derives the file key via
          X25519, decrypts, and checks per-chunk and whole-file hashes.
        </p>
        <p>
          <Link href="/approach-b">→ Open Approach B</Link>
        </p>
      </div>

      <p style={{ marginTop: "2rem", color: "var(--muted)", fontSize: "0.9rem" }}>
        This UI shells out to the Python implementations in{" "}
        <code>approach_a_mtls/</code> and <code>approach_b_envelope/</code>.
        Start the supporting daemons (A&apos;s receiver, B&apos;s broker) in
        terminals before clicking Send — see <code>DESIGN1.md</code> and{" "}
        <code>DESIGN2.md</code>.
      </p>
    </main>
  );
}
