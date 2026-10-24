import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Analysis } from "../types";

import {
  AnalysisTable,
  Empty,
  ErrorBox,
  Loading,
  PageTitle,
} from "../components/shared";
export default function HistoryPage() {
  const [q, setQ] = useState(""),
    [type, setType] = useState(""),
    [risk, setRisk] = useState(""),
    [after, setAfter] = useState(""),
    [verdict, setVerdict] = useState("");
  const params = new URLSearchParams({
    q,
    input_type: type,
    risk,
    verdict,
    ...(after ? { after: after + "T00:00:00" } : {}),
  });
  const rows = useQuery({
    queryKey: ["history", params.toString()],
    queryFn: () => api<Analysis[]>("/history?" + params),
  });
  return (
    <>
      <PageTitle
        eyebrow="INVESTIGATION LOG"
        title="Analysis history"
        text="A persistent record of your content investigations."
      />
      <div className="filters">
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Search history"
            placeholder="Search input…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          aria-label="Input type"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          <option value="">All types</option>
          {["url", "image", "audio", "video", "file"].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          aria-label="Risk level"
          value={risk}
          onChange={(e) => setRisk(e.target.value)}
        >
          <option value="">All risk levels</option>
          {["LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN"].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          aria-label="Verdict"
          value={verdict}
          onChange={(e) => setVerdict(e.target.value)}
        >
          <option value="">All verdicts</option>
          {["INCONCLUSIVE", "THREAT_INDICATORS", "LIMITED_INDICATORS"].map(
            (t) => (
              <option key={t}>{t}</option>
            ),
          )}
        </select>
        <input
          type="date"
          aria-label="Created after"
          value={after}
          onChange={(e) => setAfter(e.target.value)}
        />
      </div>
      {rows.isError ? (
        <ErrorBox error={rows.error} />
      ) : rows.isPending ? (
        <Loading />
      ) : rows.data.length ? (
        <AnalysisTable rows={rows.data} />
      ) : (
        <Empty title="No investigations found">
          Try changing your filters or{" "}
          <Link to="/analyze">start an investigation</Link>.
        </Empty>
      )}
    </>
  );
}
