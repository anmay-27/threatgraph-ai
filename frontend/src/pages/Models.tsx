import { useQuery } from "@tanstack/react-query";
import { Boxes } from "lucide-react";
import { api } from "../api";

import { Badge, ErrorBox, Loading, PageTitle } from "../components/shared";
export default function Models() {
  const query = useQuery({
    queryKey: ["models"],
    queryFn: () => api<any[]>("/models"),
  });
  return (
    <>
      <PageTitle
        eyebrow="REPRODUCIBLE DETECTION"
        title="Model registry"
        text="Installed checkpoints, data lineage, and actual evaluation results."
      />
      {query.isError ? (
        <ErrorBox error={query.error} />
      ) : query.isPending ? (
        <Loading />
      ) : (
        <div className="model-grid">
          {query.data.map((model) => (
            <section
              className={`card model-card ${model.available ? "installed" : ""}`}
              key={model.name}
            >
              <Boxes size={23} />
              <Badge
                value={
                  model.available
                    ? model.deployment_status?.startsWith("experimental")
                      ? "EXPERIMENTAL"
                      : "AVAILABLE"
                    : "UNAVAILABLE"
                }
              />
              <h2>{model.name} detector</h2>
              <p>{model.available ? model.architecture : model.reason}</p>
              {model.available ? (
                <>
                  {model.limitation && (
                    <p className="notice">{model.limitation}</p>
                  )}
                  <div className="model-metrics">
                    <div>
                      <span>In-domain research test accuracy</span>
                      <strong>
                        {model.test_metrics?.accuracy !== undefined
                          ? (model.test_metrics.accuracy * 100).toFixed(1) + "%"
                          : "Not measured"}
                      </strong>
                    </div>
                    <div>
                      <span>Held-out test F1</span>
                      <strong>
                        {model.test_metrics?.f1?.toFixed(4) ?? "Not measured"}
                      </strong>
                    </div>
                    <div>
                      <span>Held-out PR-AUC</span>
                      <strong>
                        {model.test_metrics?.pr_auc?.toFixed(4) ??
                          "Not measured"}
                      </strong>
                    </div>
                    <div>
                      <span>Test examples</span>
                      <strong>
                        {model.test_metrics?.count?.toLocaleString() ??
                          "Not measured"}
                      </strong>
                    </div>
                  </div>
                  <p className="hint">
                    Local benchmarks only; independent field evaluation remains
                    required. Dataset-specific results · Version {model.version}{" "}
                    ·{" "}
                    {model.date_trained
                      ? new Date(model.date_trained).toLocaleDateString()
                      : "Training date unavailable"}
                  </p>
                  {model.name === "image" && model.poster_external_metrics && (
                    <div className="origin-correction">
                      <strong>External poster check: {Math.round(model.poster_external_metrics.ai_recall * model.poster_external_metrics.ai_posters)}/{model.poster_external_metrics.ai_posters} AI posters flagged</strong>
                      <p>{model.poster_external_metrics.inconclusive_count}/{model.poster_external_metrics.count} posters were inconclusive under the current uncertainty rule. {model.poster_external_metrics.limitation}</p>
                    </div>
                  )}
                  <details className="registry-details">
                    <summary>Training metadata and full metrics</summary>
                    <pre>{JSON.stringify(model, null, 2)}</pre>
                  </details>
                </>
              ) : (
                <p className="hint">
                  Train on approved data and install the checkpoint with its
                  registry metadata. No substitute prediction is generated.
                </p>
              )}
            </section>
          ))}
        </div>
      )}
    </>
  );
}
