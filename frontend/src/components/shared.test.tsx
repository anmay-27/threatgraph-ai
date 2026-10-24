import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ErrorBox, EvidenceList, Loading } from "./shared";
afterEach(cleanup);
describe("Report states", () => {
  it("announces loading without fake progress", () => {
    render(<Loading />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading investigation data",
    );
  });
  it("announces an actionable error", () => {
    render(<ErrorBox error={new Error("Upload exceeds size limit")} />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Upload exceeds size limit",
    );
  });
  it("renders untrusted evidence as text and exposes details", () => {
    render(
      <EvidenceList
        items={[
          {
            id: "e",
            asset_id: "a",
            source: "local",
            category: "metadata",
            label: "file_metadata",
            score: null,
            confidence: 0,
            uncertainty: 1,
            severity: "info",
            explanation: "<script>alert(1)</script>",
            metadata: { size: 12 },
            model_version: "rules-1",
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByText("file metadata"));
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
