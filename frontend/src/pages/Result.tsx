import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import React, { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Graph from "../Graph";
import ImageAssessment from "../components/ImageAssessment";
import UrlAssessment from "../components/UrlAssessment";
import SecurityChecks from "../components/SecurityChecks";
import VideoAssessment from "../components/VideoAssessment";
import DocumentAssessment from "../components/DocumentAssessment";
import PrivacyControls from "../components/PrivacyControls";
import InvestigationContext from "../components/InvestigationContext";
import JobActions from "../components/JobActions";
import { imageAssessment } from "../imageAssessment";
import type { Analysis } from "../types";

import {
  Badge,
  Empty,
  ErrorBox,
  EvidenceList,
  Loading,
  nice,
  percent,
} from "../components/shared";
export default function Result() {
  const { id } = useParams();
  const data = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => api<Analysis>("/analyses/" + id),
    refetchInterval: (q) =>
      ["QUEUED", "PROCESSING"].includes(q.state.data?.state || "")
        ? 1500
        : false,
  });
  const [tab, setTab] = useState("evidence");
  const media = useRef<HTMLVideoElement | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  if (data.isPending) return <Loading />;
  if (data.isError) return <ErrorBox error={data.error} />;
  const row = data.data,
    r = row.report;
  function exportReport() {
    const url = URL.createObjectURL(
      new Blob(
        [
          JSON.stringify(
            {
              ...row,
              image_assessment:
                row.input_type === "image" && r
                  ? imageAssessment(r.evidence)
                  : undefined,
            },
            null,
            2,
          ),
        ],
        { type: "application/json" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `threatgraph-${id}.json`;
    a.hidden = true;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Let the browser start reading the blob before releasing it.
    window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
  }
  return (
    <>
      <div className="result-heading">
        <div>
          <Link className="back" to="/history">
            Investigations /
          </Link>
          <h1>Investigation report</h1>
          <p className="truncate">{row.name}</p>
        </div>
        <div>
          <Badge value={row.state} />
          {r && (
            <a
              className="button"
              href={"/api/v1/analyses/" + id + "/report.pdf"}
            >
              <Download size={15} />
              Export PDF
            </a>
          )}
          {r && (
            <button onClick={exportReport}>
              <Download size={15} />
              Export JSON
            </button>
          )}
        </div>
      </div>
      <JobActions id={row.id} state={row.state} />
      {["FAILED", "CANCELLED"].includes(row.state) ? (
        <ErrorBox error={new Error(row.error || "Analysis failed")} />
      ) : !r ? (
        <section className="card progress-panel">
          <Loader2 className="spin" size={30} />
          <h2>
            {row.state === "QUEUED"
              ? "Waiting for a worker"
              : "Following the evidence"}
          </h2>
          <p>Progress reflects completed analysis steps.</p>
          <ul>
            {row.progress.map((p, i) => (
              <li key={i}>
                <CheckCircle2 size={16} />
                {p.step}
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <>
          {row.input_type === "image" && (
            <ImageAssessment key={row.id} row={row} />
          )}
          {row.input_type === "url" && <UrlAssessment key={row.id} row={row} />}
          {row.input_type === "video" && (
            <VideoAssessment key={row.id} row={row} />
          )}
          <DocumentAssessment row={row} />
          <SecurityChecks row={row} />
          <InvestigationContext row={row} />
          <PrivacyControls id={row.id} />
          {row.state === "PARTIAL" && (
            <div className="notice">
              <AlertTriangle size={18} />
              Coverage is incomplete. Unavailable detectors are listed below;
              this report is not a safety certificate.
            </div>
          )}
          {row.input_type === "image" && (
            <div className="assessment-separator">
              <h2>Overall investigation coverage</h2>
              <p>
                Security risk is assessed separately from image origin. AI
                generation alone does not establish a threat. “Unknown” means
                there is insufficient security evidence.
              </p>
            </div>
          )}
          <div className="risk-overview">
            <div className="card risk-main">
              <div
                className={`risk-ring ${r.risk_level.toLowerCase()}`}
                style={
                  {
                    "--risk": `${(r.risk_score || 0) * 3.6}deg`,
                  } as React.CSSProperties
                }
              >
                <div>
                  <strong>{r.risk_score ?? "—"}</strong>
                  <small>
                    {r.risk_score === null ? "NO ESTIMATE" : "/ 100"}
                  </small>
                </div>
              </div>
              <div>
                <span className="eyebrow">
                  {row.input_type === "image"
                    ? "COMBINED EVIDENCE INDICATORS"
                    : "OVERALL INDICATOR RISK"}
                </span>
                <h2>{r.risk_score === null ? 'Security verdict not established' : r.risk_level}</h2>
                <Badge value={r.verdict} />
              </div>
            </div>
            <div className="card stat">
              <span>Investigation confidence</span>
              <strong>{r.risk_score === null ? 'Not estimated' : percent(r.confidence)}</strong>
              <small>
                Evidence reliability and coverage, not the AI model score
              </small>
            </div>
            <div className="card stat">
              <span>Uncertainty</span>
              <strong className="word-stat">{nice(r.uncertainty_level)}</strong>
              <small>
                {r.conflicts.length} evidence conflict
                {r.conflicts.length === 1 ? "" : "s"}
              </small>
            </div>
          </div>
          <section className="finding-summary">
            <ShieldCheck size={24} />
            <div>
              <h2>{r.scenarios[0]?.label || "Evidence-led assessment"}</h2>
              <p>{r.explanation}</p>
            </div>
          </section>
          <Graph graph={r.graph} />
          <div className="result-columns">
            <section className="card">
              <div className="tabs" role="tablist" aria-label="Report section">
                {["evidence", "models", "provenance", "technical"].map((t) => (
                  <button
                    key={t}
                    role="tab"
                    aria-selected={tab === t}
                    className={tab === t ? "active" : ""}
                    onClick={() => setTab(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              {tab === "evidence" ? (
                <EvidenceList items={r.evidence} />
              ) : tab === "models" ? (
                <EvidenceList items={r.model_results} />
              ) : tab === "provenance" ? (
                r.provenance.length ? (
                  <EvidenceList items={r.provenance} />
                ) : (
                  <Empty title="No provenance inspection">
                    No applicable credential result is available. Absence is
                    neutral.
                  </Empty>
                )
              ) : (
                <dl className="technical">
                  {Object.entries({
                    id: row.id,
                    MIME: row.mime,
                    SHA256: row.sha256,
                    Bytes: row.size,
                    Fusion: r.fusion_method,
                    Created: row.created_at,
                  }).map(([k, v]) => (
                    <React.Fragment key={k}>
                      <dt>{k}</dt>
                      <dd>{v ?? "Not available"}</dd>
                    </React.Fragment>
                  ))}
                </dl>
              )}
            </section>
            <aside>
              <section className="card next-steps">
                <span className="eyebrow">RECOMMENDED ACTIONS</span>
                <h2>
                  {row.input_type === "image"
                    ? "How to verify this image"
                    : "Proceed with context"}
                </h2>
                {(row.input_type === "image"
                  ? imageAssessment(r.evidence).recommendations
                  : r.recommendations
                ).map((text, i) => (
                  <p key={text}>
                    <span>{i + 1}</span>
                    {text}
                  </p>
                ))}
              </section>
              {r.conflicts.length > 0 && (
                <section className="card conflicts">
                  <h2>Conflicting evidence</h2>
                  {r.conflicts.map((c) => (
                    <p key={c.id}>{c.explanation}</p>
                  ))}
                </section>
              )}
            </aside>
          </div>
          {["image", "audio", "video"].includes(row.input_type) && (
            <section className="card media-card">
              <h2>Submitted media</h2>
              <p className="hint">
                Original preview is available until the configured retention
                deadline.
              </p>
              {row.input_type === "image" ? (
                <img
                  src={`/api/v1/analyses/${id}/media`}
                  alt="Submitted content"
                />
              ) : row.input_type === "audio" ? (
                <>
                  <audio
                    ref={audio}
                    controls
                    src={`/api/v1/analyses/${id}/media`}
                  />
                  <div
                    className="waveform"
                    aria-label="Audio amplitude waveform"
                  >
                    {(
                      r.evidence.find((e) => e.label === "audio_metadata")
                        ?.metadata.waveform || []
                    ).map((v: number, i: number) => (
                      <i key={i} style={{ height: Math.max(2, v * 80) }} />
                    ))}
                  </div>
                </>
              ) : (
                <video
                  ref={media}
                  controls
                  src={`/api/v1/analyses/${id}/media`}
                />
              )}
              <div className="segments">
                {r.model_results.flatMap((e) =>
                  (e.metadata.segments || []).map((s: any, i: number) => (
                    <button
                      key={e.id + i}
                      onClick={() => {
                        const player = media.current || audio.current;
                        if (player) player.currentTime = s.start;
                      }}
                    >
                      {s.start.toFixed(1)}–{s.end.toFixed(1)}s · synthetic{" "}
                      {percent(s.probability)}
                    </button>
                  )),
                )}
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}
