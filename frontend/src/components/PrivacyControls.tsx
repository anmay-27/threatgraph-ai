import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, client } from "./shared";
export default function PrivacyControls({ id }: { id: string }) {
  const navigate = useNavigate(),
    [error, setError] = useState<Error | null>(null),
    [busy, setBusy] = useState(false);
  const data = useQuery({
    queryKey: ["privacy", id],
    queryFn: () =>
      api<{ original_present: boolean; stored_until: string; policy: string }>(
        "/analyses/" + id + "/privacy",
      ),
  });
  async function remove(original: boolean) {
    if (
      !window.confirm(
        original
          ? "Delete the original upload now? The report will remain."
          : "Delete this report, its evidence and original upload? This cannot be undone.",
      )
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await api("/analyses/" + id + (original ? "/original" : ""), {
        method: "DELETE",
      });
      await client.invalidateQueries();
      if (!original) navigate("/history");
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card case-form">
      <h2>Data & privacy</h2>
      {data.data && (
        <p>
          {data.data.original_present
            ? "Original stored until " +
              new Date(data.data.stored_until).toLocaleString()
            : "Original upload unavailable or deleted"}
          . {data.data.policy}
        </p>
      )}
      <div className="case-actions">
        <button
          disabled={busy || !data.data?.original_present}
          onClick={() => void remove(true)}
        >
          Delete original upload
        </button>
        <button disabled={busy} onClick={() => void remove(false)}>
          Delete investigation
        </button>
      </div>
      {error && <ErrorBox error={error} />}
    </section>
  );
}
