import cytoscape from "cytoscape";
import { Maximize2, Route, ZoomIn, ZoomOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Graph as GraphType } from "./types";

export default function Graph({ graph }: { graph: GraphType }) {
  const container = useRef<HTMLDivElement>(null),
    instance = useRef<cytoscape.Core | null>(null);
  const [selected, setSelected] = useState<GraphType["nodes"][number] | null>(
    null,
  );
  const [severity, setSeverity] = useState("all");
  const [dark, setDark] = useState(document.documentElement.dataset.theme === "dark");
  useEffect(() => {
    const update = () => setDark(document.documentElement.dataset.theme === "dark");
    window.addEventListener("themechange", update);
    return () => window.removeEventListener("themechange", update);
  }, []);
  useEffect(() => {
    if (!container.current) return;
    const nodes = graph.nodes.filter(
      (n) =>
        severity === "all" ||
        n.type !== "detector_finding" ||
        n.severity === severity,
    );
    const ids = new Set(nodes.map((n) => n.id));
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...nodes.map((n) => ({
          data: {
            ...n,
            label: n.label.length > 32 ? n.label.slice(0, 29) + "…" : n.label,
          },
        })),
        ...graph.edges
          .filter((e) => ids.has(e.source) && ids.has(e.target))
          .map((e) => ({ data: e })),
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 45,
        spacingFactor: 1.2,
      },
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#7963b4",
            label: "data(label)",
            color: dark ? "#c8d6e6" : "#536575",
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: 34,
            height: 34,
            "border-width": 5,
            "border-color": dark ? "#354058" : "#e9e3f5",
          },
        },
        {
          selector: 'node[type="detector_finding"]',
          style: {
            shape: "round-rectangle",
            "background-color": "#899ab3",
            width: 24,
            height: 24,
          },
        },
        {
          selector: 'node[severity="high"], node[severity="critical"]',
          style: { "background-color": "#bd624b" },
        },
        {
          selector: "edge",
          style: {
            width: 1.3,
            "line-color": "#c8bddc",
            "target-arrow-color": "#b2a3cd",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: "edge.path",
          style: {
            "line-color": "#b34f34",
            "target-arrow-color": "#b34f34",
            width: 3,
          },
        },
        {
          selector: "node.path",
          style: { "background-color": "#b34f34" },
        },
        {
          selector: ":selected",
          style: { "border-width": 3, "border-color": "#183f59" },
        },
      ],
    });
    instance.current = cy;
    cy.on("tap", "node", (event) => {
      const data = event.target.data();
      setSelected(graph.nodes.find((n) => n.id === data.id) || null);
    });
    let resizeFrame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(resizeFrame);
      resizeFrame = requestAnimationFrame(() => { cy.resize(); cy.fit(undefined, 35); });
    });
    observer.observe(container.current);
    return () => { observer.disconnect(); cancelAnimationFrame(resizeFrame); cy.destroy(); };
  }, [graph, severity, dark]);
  function trace() {
    const cy = instance.current;
    if (!cy || !selected) return;
    cy.elements().removeClass("path");
    const node = cy.getElementById(selected.id);
    node.predecessors().add(node).addClass("path");
  }
  return (
    <section className="card graph-card">
      <div className="card-heading">
        <div>
          <span className="eyebrow">CONNECTED EVIDENCE</span>
          <h2>Investigation graph</h2>
        </div>
        <select
          aria-label="Filter graph severity"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          <option value="all">All severities</option>
          {["critical", "high", "moderate", "low", "info"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <div
        ref={container}
        className="graph"
        role="region"
        aria-label="Interactive investigation graph"
      />
      <div className="graph-controls">
        <button
          aria-label="Zoom in"
          onClick={() => instance.current?.zoom(instance.current.zoom() * 1.3)}
        >
          <ZoomIn size={16} />
        </button>
        <button
          aria-label="Zoom out"
          onClick={() => instance.current?.zoom(instance.current.zoom() / 1.3)}
        >
          <ZoomOut size={16} />
        </button>
        <button
          aria-label="Fit graph"
          onClick={() => instance.current?.fit(undefined, 35)}
        >
          <Maximize2 size={16} />
        </button>
        <span>
          {graph.nodes.length} nodes · {graph.edges.length} connections
        </span>
      </div>
      <div className="node-inspector">
        <label htmlFor="node-select">Inspect a node</label>
        <select
          id="node-select"
          value={selected?.id || ""}
          onChange={(e) =>
            setSelected(
              graph.nodes.find((n) => n.id === e.target.value) || null,
            )
          }
        >
          <option value="">Select a node on the graph or here</option>
          {graph.nodes.map((n) => (
            <option key={n.id} value={n.id}>
              {n.type}: {n.label}
            </option>
          ))}
        </select>
        {selected && (
          <div>
            <p>
              <strong>{selected.type.replaceAll("_", " ")}</strong> ·{" "}
              {selected.label}
            </p>
            <button onClick={trace}>
              <Route size={15} />
              Trace incoming paths
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
