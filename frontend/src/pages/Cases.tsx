import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import {
  Badge,
  ErrorBox,
  Loading,
  PageTitle,
  AnalysisTable,
  client,
} from "../components/shared";
import Graph from "../Graph";
import type { Analysis, Graph as GraphType } from "../types";
type CaseRecord = {
  id: string;
  title: string;
  description: string;
  status: string;
  severity: string;
  tags: string[];
  final_verdict: string;
  updated_at: string;
};
type Detail = CaseRecord & {
  entities: {
    id: string;
    type: string;
    display_value: string;
    investigation_count: number;
  }[];
  analyses: Analysis[];
  graph: GraphType;
  timeline: {
    id: string;
    action: string;
    content: string;
    created_at: string;
  }[];
};
const statuses = [
  "OPEN",
  "INVESTIGATING",
  "REVIEW_REQUIRED",
  "RESOLVED",
  "ARCHIVED",
];
const json = (body: unknown, method = "POST") => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
export default function Cases() {
  const [title, setTitle] = useState(""),
    [q, setQ] = useState(""),
    [error, setError] = useState<Error | null>(null),
    [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const rows = useQuery({
    queryKey: ["cases", q],
    queryFn: () => api<CaseRecord[]>("/cases?q=" + encodeURIComponent(q)),
  });
  return (
    <>
      <PageTitle
        eyebrow="INVESTIGATION WORKSPACE"
        title="Cases"
        text="Connect related submissions, record findings and follow an investigation over time."
      />
      <form
        className="card case-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            const row = await api<CaseRecord>("/cases", json({ title }));
            await client.invalidateQueries({ queryKey: ["cases"] });
            navigate("/cases/" + row.id);
          } catch (e) {
            setError(e as Error);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          New case title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            required
            placeholder="Suspicious recruitment offer"
          />
        </label>
        <button disabled={busy || !title.trim()}>Create case</button>
      </form>
      {error && <ErrorBox error={error} />}
      <div className="filters">
        <input
          aria-label="Search cases"
          placeholder="Search cases"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      {rows.isPending ? (
        <Loading />
      ) : rows.isError ? (
        <ErrorBox error={rows.error} />
      ) : (
        <div className="case-grid">
          {rows.data.length === 0 ? (
            <p>No cases yet. Create one to group related investigations.</p>
          ) : (
            rows.data.map((c) => (
              <Link className="card case-tile" to={"/cases/" + c.id} key={c.id}>
                <Badge value={c.status} />
                <h2>{c.title}</h2>
                <p>{c.description || "No description yet"}</p>
                <Badge value={c.severity} />
                <p>{c.tags.join(" · ")}</p>
              </Link>
            ))
          )}
        </div>
      )}
    </>
  );
}
export function CasePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("Overview"),
    [error, setError] = useState<Error | null>(null),
    [busy, setBusy] = useState(false),
    [note, setNote] = useState(""),
    [analysisId, setAnalysisId] = useState("");
  const row = useQuery({
    queryKey: ["case", id],
    queryFn: () => api<Detail>("/cases/" + id),
  });
  const history = useQuery({
    queryKey: ["history", "case-picker"],
    queryFn: () => api<Analysis[]>("/history"),
    enabled: tab === "Analyses",
  });
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await client.invalidateQueries({ queryKey: ["case", id] });
      await client.invalidateQueries({ queryKey: ["cases"] });
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  };
  if (row.isPending) return <Loading />;
  if (row.isError) return <ErrorBox error={row.error} />;
  const c = row.data;
  return (
    <>
      <Link to="/cases">← All cases</Link>
      <PageTitle
        eyebrow="CASE INVESTIGATION"
        title={c.title}
        text={c.description || "Build an evidence-backed investigation."}
      />
      <div className="case-actions">
        <Badge value={c.status} />
        <Badge value={c.severity} />
        <span>Severity is analyst-assigned</span>
        <Link to="/analyze">New investigation</Link>
      </div>
      {error && <ErrorBox error={error} />}
      <div className="tabs" role="tablist" aria-label="Case sections">
        {["Overview", "Analyses", "Threat graph", "Timeline", "Notes"].map(
          (t) => (
            <button
              role="tab"
              aria-selected={tab === t}
              key={t}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ),
        )}
      </div>
      {tab === "Overview" && (
        <form
          className="card case-form"
          key={c.updated_at}
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            void act(() =>
              api(
                "/cases/" + id,
                json(
                  {
                    title: f.get("title"),
                    description: f.get("description"),
                    status: f.get("status"),
                    severity: f.get("severity"),
                    tags: String(f.get("tags")).split(","),
                    final_verdict: f.get("verdict"),
                  },
                  "PUT",
                ),
              ),
            );
          }}
        >
          <label>
            Title
            <input
              name="title"
              defaultValue={c.title}
              required
              maxLength={200}
            />
          </label>
          <label>
            Description
            <textarea
              name="description"
              defaultValue={c.description}
              maxLength={10000}
            />
          </label>
          <label>
            Status
            <select name="status" defaultValue={c.status}>
              {statuses.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Analyst-assigned severity
            <select name="severity" defaultValue={c.severity}>
              {["UNKNOWN", "LOW", "MODERATE", "HIGH", "CRITICAL"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Tags (comma separated)
            <input
              name="tags"
              defaultValue={c.tags.join(", ")}
              maxLength={1000}
            />
          </label>
          <label>
            Investigator conclusion
            <textarea
              name="verdict"
              defaultValue={c.final_verdict}
              maxLength={5000}
            />
          </label>
          <p className="hint">
            Your conclusion is an investigator note, not a detector result.
          </p>
          <button disabled={busy}>Save case</button>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              if (
                window.confirm(
                  "Delete this case and its notes? Linked analyses will be preserved.",
                )
              )
                void act(async () => {
                  await api("/cases/" + id, { method: "DELETE" });
                  navigate("/cases");
                });
            }}
          >
            Delete case
          </button>
        </form>
      )}
      {tab === "Analyses" && (
        <>
          <form
            className="card case-form"
            onSubmit={(e) => {
              e.preventDefault();
              void act(async () => {
                await api("/cases/" + id + "/analyses/" + analysisId, {
                  method: "POST",
                });
                setAnalysisId("");
              });
            }}
          >
            <label>
              Add an existing investigation
              <select
                value={analysisId}
                onChange={(e) => setAnalysisId(e.target.value)}
                required
              >
                <option value="">Select investigation</option>
                {history.data
                  ?.filter((a) => !c.analyses.some((x) => x.id === a.id))
                  .map((a) => (
                    <option value={a.id} key={a.id}>
                      {a.name} — {a.id.slice(0, 8)}
                    </option>
                  ))}
              </select>
            </label>
            {history.isError && <ErrorBox error={history.error} />}
            <button disabled={busy || !analysisId}>Add to case</button>
          </form>
          <AnalysisTable rows={c.analyses} />
          {c.analyses.map((a) => (
            <div className="case-actions" key={a.id}>
              <span>{a.name}</span>
              <button
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm(
                      "Remove this analysis from the case? Its report will be preserved.",
                    )
                  )
                    void act(() =>
                      api("/cases/" + id + "/analyses/" + a.id, {
                        method: "DELETE",
                      }),
                    );
                }}
              >
                Remove from case
              </button>
            </div>
          ))}
        </>
      )}
      <p>
        <a href={"/api/v1/cases/" + id + "/report.pdf"}>Export case PDF</a>
      </p>
      <details className="card case-form">
        <summary>Case entities ({c.entities.length})</summary>
        {c.entities.map((e) => (
          <p key={e.id}>
            <Link to={"/entities/" + e.id}>{e.display_value}</Link> · {e.type} ·{" "}
            {e.investigation_count} investigations
          </p>
        ))}
      </details>
      {tab === "Threat graph" &&
        (c.graph.nodes.length ? (
          <Graph graph={c.graph} />
        ) : (
          <p>Add completed investigations to see their evidence graphs.</p>
        ))}
      {tab === "Timeline" && (
        <ol className="case-timeline">
          {c.timeline.map((e) => (
            <li className="card" key={e.id}>
              <time>{new Date(e.created_at).toLocaleString()}</time>
              <h3>{e.action.replaceAll("_", " ")}</h3>
              <p>{e.content}</p>
            </li>
          ))}
        </ol>
      )}
      {tab === "Notes" && (
        <>
          <form
            className="card case-form"
            onSubmit={(e) => {
              e.preventDefault();
              void act(async () => {
                await api("/cases/" + id + "/notes", json({ content: note }));
                setNote("");
              });
            }}
          >
            <label>
              Investigation note
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                required
                maxLength={10000}
              />
            </label>
            <button disabled={busy || !note.trim()}>Add note</button>
          </form>
          {c.timeline
            .filter((e) => e.action === "note_added")
            .map((e) => (
              <article className="card case-form" key={e.id}>
                <time>{new Date(e.created_at).toLocaleString()}</time>
                <p className="case-note">{e.content}</p>
              </article>
            ))}
        </>
      )}
    </>
  );
}
