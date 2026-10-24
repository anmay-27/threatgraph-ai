import { QueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowUpRight, FileSearch, Loader2 } from "lucide-react";
import React from "react";
import { Link } from "react-router-dom";
import type { Analysis, Evidence } from "../types";
export const client = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});
export const nice = (text: string) => text.replaceAll("_", " ").toLowerCase();
export const percent = (value: number) => `${Math.round(value * 100)}%`;
export function ErrorBox({ error }: { error: Error }) {
  return (
    <div role="alert" className="notice error">
      <AlertTriangle size={18} />
      {error.message}
    </div>
  );
}

export function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <FileSearch size={32} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

export function Loading() {
  return (
    <div role="status" className="loading">
      <Loader2 className="spin" />
      Loading investigation data…
    </div>
  );
}

export function Badge({ value }: { value: string }) {
  return <span className={`badge ${value.toLowerCase()}`}>{nice(value)}</span>;
}

export function PageTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="page-title">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{text}</p>
    </div>
  );
}

export function AnalysisTable({ rows }: { rows: Analysis[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Input / investigation</th>
            <th>Type</th>
            <th>Created</th>
            <th>Risk</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td data-label="Investigation">
                <Link to={"/analysis/" + row.id}>
                  {row.name}
                  <ArrowUpRight size={13} />
                </Link>
                <small>
                  {row.report
                    ? nice(row.report.verdict)
                    : "Waiting for evidence"}
                </small>
              </td>
              <td data-label="Type">{row.input_type}</td>
              <td data-label="Created">{new Date(row.created_at).toLocaleString()}</td>
              <td data-label="Indicators">
                <Badge value={row.report?.risk_level || "PENDING"} />
              </td>
              <td data-label="Status">
                <Badge value={row.state} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EvidenceList({ items }: { items: Evidence[] }) {
  return (
    <div className="evidence-list">
      {items.map((e) => (
        <details key={e.id}>
          <summary>
            <span className={"evidence-dot " + e.severity} />
            <div>
              <strong>{nice(e.label)}</strong>
              <small>
                {e.source} · {nice(e.category)}
              </small>
            </div>
            <Badge value={e.severity} />
            {e.score !== null && (
              <span className="evidence-score">{percent(e.score)}</span>
            )}
          </summary>
          <div className="evidence-body">
            <p>{e.explanation}</p>
            <p className="hint">
              Confidence {percent(e.confidence)} · Version {e.model_version}
            </p>
            <pre>{JSON.stringify(e.metadata, null, 2)}</pre>
          </div>
        </details>
      ))}
    </div>
  );
}
