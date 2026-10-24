import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";

import {
  Empty,
  ErrorBox,
  Loading,
  PageTitle,
  nice,
} from "../components/shared";
export default function Dashboard() {
  const data = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<any>("/dashboard"),
  });
  return (
    <>
      <PageTitle
        eyebrow="WORKSPACE OVERVIEW"
        title="The bigger picture"
        text="Aggregate insights from your actual investigations."
      />
      {data.isError ? (
        <ErrorBox error={data.error} />
      ) : data.isPending ? (
        <Loading />
      ) : (
        <>
          <div className="stat-grid">
            {[
              ["Total analyses", data.data.total],
              ["Threat indicators", data.data.threats_detected],
              ["High risk", data.data.high_risk],
              ["Inconclusive", data.data.inconclusive],
            ].map(([name, value]) => (
              <div className="card stat" key={name}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          {!data.data.total ? (
            <Empty title="Your workspace is ready">
              Charts populate as you investigate content.{" "}
              <Link to="/analyze">Start an analysis</Link>.
            </Empty>
          ) : (
            <div className="chart-grid">
              {[
                ["Input types", "types"],
                ["Risk distribution", "risks"],
                ["Threat categories", "categories"],
              ].map(([title, key]) => (
                <section className="card" key={key}>
                  <h2>{title}</h2>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart
                      data={Object.entries(data.data[key]).map(
                        ([name, count]) => ({ name: nice(name), count }),
                      )}
                    >
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: "var(--text-secondary)" }} />
                      <YAxis allowDecimals={false} tick={{ fill: "var(--text-secondary)" }} />
                      <Tooltip contentStyle={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--text)" }} />
                      <Bar
                        isAnimationActive={false}
                        dataKey="count"
                        fill="var(--accent)"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
