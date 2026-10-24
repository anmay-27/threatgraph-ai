import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox, Loading, PageTitle } from "../components/shared";
export default function Operations() {
  const data = useQuery({
    queryKey: ["operations"],
    queryFn: () => api<Record<string, unknown>>("/admin/health"),
    refetchInterval: 30000,
  });
  return (
    <>
      <PageTitle
        eyebrow="ADMINISTRATION"
        title="Operations"
        text="Observed service status and recorded job states. Unavailable telemetry is explicitly identified."
      />
      {data.isPending ? (
        <Loading />
      ) : data.isError ? (
        <ErrorBox error={data.error} />
      ) : (
        <div className="case-grid">
          {Object.entries(data.data)
            .filter(([k]) => k !== "models")
            .map(([k, v]) => (
              <article className="card case-form" key={k}>
                <h2>{k.replaceAll("_", " ")}</h2>
                <pre>
                  {typeof v === "string" ? v : JSON.stringify(v, null, 2)}
                </pre>
              </article>
            ))}
        </div>
      )}
    </>
  );
}
