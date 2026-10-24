import { useState } from "react";
import { api } from "../api";
import { client } from "./shared";
export default function JobActions({
  id,
  state,
}: {
  id: string;
  state: string;
}) {
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const active = ["QUEUED", "PROCESSING"].includes(state);
  if (!active && !["FAILED", "CANCELLED"].includes(state)) return null;
  return (
    <div className="card case-form">
      <button
        disabled={busy}
        onClick={async () => {
          if (
            !window.confirm(
              active
                ? "Request cancellation at the next safe pipeline boundary?"
                : "Retry this failed or cancelled job using the retained input?",
            )
          )
            return;
          setBusy(true);
          try {
            await api("/analyses/" + id + (active ? "/cancel" : "/retry"), {
              method: "POST",
            });
            setMessage(
              active
                ? "Cancellation requested. The active detector may need to finish first."
                : "Retry queued.",
            );
            await client.invalidateQueries({ queryKey: ["analysis", id] });
          } catch (e) {
            setMessage((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {active ? "Cancel investigation" : "Retry investigation"}
      </button>
      <p role="status">{message}</p>
    </div>
  );
}
