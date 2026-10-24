import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "./shared";
import type { Analysis } from "../types";
export default function InvestigationContext({ row }: { row: Analysis }) {
  const entities = useQuery({
    queryKey: ["analysis-entities", row.id],
    queryFn: () =>
      api<
        {
          id: string;
          type: string;
          display_value: string;
          investigation_count: number;
        }[]
      >("/analyses/" + row.id + "/entities"),
  });
  const [technical, setTechnical] = useState(false);
  const [feedback, setFeedback] = useState(""),
    [note, setNote] = useState(""),
    [saved, setSaved] = useState("");
  const duplicates = useQuery({
    queryKey: ["duplicates", row.id],
    queryFn: () =>
      api<{
        matches: { id: string; name: string; relation: string }[];
        limitation: string;
      }>("/analyses/" + row.id + "/duplicates"),
  });
  return (
    <section className="card case-form">
      <div className="case-actions">
        <h2>Investigation context</h2>
        <button
          aria-pressed={technical}
          onClick={() => setTechnical(!technical)}
        >
          {technical ? "Switch to simple view" : "Switch to technical view"}
        </button>
      </div>
      {row.report?.scenarios.map((scenario: any) => (
        <article key={scenario.id}>
          <h3>{scenario.label}</h3>
          <p>{scenario.explanation}</p>
          <p>
            <strong>Still unverified:</strong>{" "}
            {scenario.missing_evidence?.join("; ") ||
              "Independent confirmation of identity and intent."}
          </p>
          {technical && (
            <pre>
              {JSON.stringify(
                {
                  rule_confidence: scenario.confidence,
                  method: scenario.confidence_method,
                  evidence_ids: scenario.evidence_ids,
                },
                null,
                2,
              )}
            </pre>
          )}
        </article>
      ))}
      <h3>Entities & previous occurrences</h3>
      <p>Repeated entities are investigative leads, not proof of fraud.</p>
      {entities.isError ? (
        <ErrorBox error={entities.error} />
      ) : (
        <ul>
          {entities.data?.slice(0, 30).map((e) => (
            <li key={e.id}>
              <Link to={"/entities/" + e.id}>{e.display_value}</Link> · {e.type}{" "}
              · {Math.max(0, e.investigation_count - 1)} other investigations
              {technical && <code> {e.id}</code>}
            </li>
          ))}
        </ul>
      )}
      {technical && (
        <p>
          Raw detector scores, metadata and model versions are available in the
          evidence tabs below.
        </p>
      )}
      {duplicates.data && (
        <>
          <h3>Previous submissions</h3>
          <p>{duplicates.data.limitation}</p>
          {duplicates.data.matches.length ? (
            duplicates.data.matches.map((d) => (
              <p key={d.id}>
                <Link to={"/analysis/" + d.id}>{d.name}</Link> ·{" "}
                {d.relation.replaceAll("_", " ")}
              </p>
            ))
          ) : (
            <p>
              No matching submission found in the latest 500 accessible
              investigations.
            </p>
          )}
        </>
      )}
      <details>
        <summary>Give feedback on a finding</summary>
        <form
          className="case-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            try {
              await api("/analyses/" + row.id + "/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  evidence_id: feedback,
                  verdict: f.get("verdict"),
                  note,
                }),
              });
              setSaved(
                "Feedback saved separately. No model retraining was triggered.",
              );
            } catch (e) {
              setSaved((e as Error).message);
            }
          }}
        >
          <label>
            Finding
            <select
              required
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
            >
              <option value="">Select finding</option>
              {row.report?.evidence.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label.replaceAll("_", " ")} ({e.source})
                </option>
              ))}
            </select>
          </label>
          <label>
            Your assessment
            <select name="verdict">
              <option value="unsure">Unsure</option>
              <option value="accurate">Accurate</option>
              <option value="incorrect">Incorrect</option>
            </select>
          </label>
          <label>
            Optional note
            <textarea
              maxLength={2000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button disabled={!feedback}>Save feedback</button>
          <p role="status">{saved}</p>
        </form>
      </details>
    </section>
  );
}
