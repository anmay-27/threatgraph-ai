import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import {
  AnalysisTable,
  ErrorBox,
  Loading,
  PageTitle,
} from "../components/shared";
import Graph from "../Graph";
import type { Analysis, Graph as GraphType } from "../types";
type Entity = {
  id: string;
  type: string;
  display_value: string;
  first_seen: string;
  last_seen: string;
  investigation_count: number;
};
export default function Intelligence() {
  const [q, setQ] = useState("");
  const rows = useQuery({
    queryKey: ["entities", q],
    queryFn: () => api<Entity[]>("/entities/search?q=" + encodeURIComponent(q)),
  });
  const graph = useQuery({
    queryKey: ["intelligence", q],
    queryFn: () =>
      api<GraphType>("/intelligence/graph?q=" + encodeURIComponent(q)),
  });
  return (
    <>
      <PageTitle
        eyebrow="CONNECTED EVIDENCE"
        title="Intelligence graph"
        text="Find entities shared across investigations. A shared entity is a lead, not proof of fraud."
      />
      <input
        aria-label="Search entities"
        placeholder="Search domain, email, phone or hash"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <p className="hint">
        Graph shows up to 100 matching entities and 500 occurrences. Refine your
        search to explore a smaller set.
      </p>
      {graph.isPending ? (
        <Loading />
      ) : graph.isError ? (
        <ErrorBox error={graph.error} />
      ) : (
        <Graph graph={graph.data} />
      )}
      <EntityList rows={rows.data || []} />
      {rows.isError && <ErrorBox error={rows.error} />}
    </>
  );
}
function EntityList({ rows }: { rows: Entity[] }) {
  return (
    <div className="case-grid">
      {rows.map((e) => (
        <Link key={e.id} to={"/entities/" + e.id} className="card case-tile">
          <small>{e.type}</small>
          <h3 className="case-note">{e.display_value}</h3>
          <p>
            Observed in {e.investigation_count} investigation
            {e.investigation_count === 1 ? "" : "s"}
          </p>
        </Link>
      ))}
    </div>
  );
}
export function EntityPage() {
  const { id } = useParams();
  const row = useQuery({
    queryKey: ["entity", id],
    queryFn: () =>
      api<
        Entity & {
          analyses: Analysis[];
          cases: { id: string; title: string }[];
          limitation: string;
        }
      >("/entities/" + id),
  });
  if (row.isPending) return <Loading />;
  if (row.isError) return <ErrorBox error={row.error} />;
  const e = row.data;
  return (
    <>
      <Link to="/intelligence">← Intelligence graph</Link>
      <PageTitle eyebrow={e.type} title={e.display_value} text={e.limitation} />
      <p>
        Observed in {e.investigation_count} investigations · First seen{" "}
        {new Date(e.first_seen).toLocaleString()} · Last seen{" "}
        {new Date(e.last_seen).toLocaleString()}
      </p>
      <h2>Associated cases</h2>
      {e.cases.length ? (
        e.cases.map((c) => (
          <p key={c.id}>
            <Link to={"/cases/" + c.id}>{c.title}</Link>
          </p>
        ))
      ) : (
        <p>No cases linked.</p>
      )}
      <h2>Investigations</h2>
      <AnalysisTable rows={e.analyses} />
    </>
  );
}
