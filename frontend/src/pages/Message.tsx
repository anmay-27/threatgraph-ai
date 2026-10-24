import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, PageTitle } from "../components/shared";
export default function Message() {
  const [kind, setKind] = useState(() => new URLSearchParams(window.location.search).get('kind') === 'email' ? 'email' : 'message'),
    [title, setTitle] = useState("Suspicious message"),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<Error | null>(null);
  const navigate = useNavigate();
  return (
    <>
      <PageTitle
        eyebrow="DIGITAL TRUST & FRAUD INVESTIGATION"
        title="Investigate a message"
        text="Examine suspicious offers, payment instructions, emails and credential requests."
      />
      <form
        className="card case-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          setBusy(true);
          try {
            const row = await api<{ id: string }>("/analyze/" + kind, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ title, text }),
            });
            navigate("/analysis/" + row.id);
          } catch (e) {
            setError(e as Error);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Input format
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="message">Message / SMS / WhatsApp text</option>
            <option value="email">Email source including headers</option>
          </select>
        </label>
        <label>
          Investigation title
          <input
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          {kind === "email"
            ? "Email source (From, Subject, blank line, body)"
            : "Message content"}
          <textarea
            required
            maxLength={100000}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <p>
          Detected public URLs will be fetched through the protected URL
          analyzer. Do not include passwords or private access links. Email
          authentication headers are inspected as unverified claims.
        </p>
        <button disabled={busy || !text.trim()}>
          {busy ? "Submitting…" : "Investigate message"}
        </button>
        {error && <ErrorBox error={error} />}
        <Link to="/analyze">
          Upload a screenshot, document or .eml file instead
        </Link>
      </form>
    </>
  );
}
