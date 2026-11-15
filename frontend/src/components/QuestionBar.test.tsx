import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { QuestionBar } from "./QuestionBar";
import type { DiscoveryHelper } from "./QuestionBar";

const DISCOVERY: DiscoveryHelper = {
  discover: () => Promise.reject(new Error("not called")),
  onUseVariable: () => undefined,
  onManual: () => undefined,
  onFailure: () => undefined,
};

function render(ready: { summary: string; onRun: () => void; onEdit: () => void } | null): string {
  return renderToStaticMarkup(
    <QuestionBar onProposal={() => undefined} firstScreen screenChanges={0} ready={ready} />,
  );
}

describe("QuestionBar", () => {
  test("offers to run a case the question set up, right under the question", () => {
    const html = render({
      summary: "Air temperature · Helsinki · the full record, all months",
      onRun: () => undefined,
      onEdit: () => undefined,
    });
    expect(html).toContain("Ready to test:");
    expect(html).toContain("Air temperature · Helsinki · the full record, all months");
    expect(html).toContain("Run this case");
    expect(html).toContain("Change the settings");
  });

  test("shows no ready card before a question has set up a case", () => {
    expect(render(null)).not.toContain("Ready to test");
  });

  test("says an AI suggests variables with sources when guided discovery is on", () => {
    const html = renderToStaticMarkup(
      <QuestionBar onProposal={() => undefined} discovery={DISCOVERY} firstScreen screenChanges={0} />,
    );
    expect(html).toContain("An AI suggests variables from reviewed documentation, with its sources");
    expect(html).toContain("Nothing runs until you confirm.");
    expect(html).not.toContain("The AI helper is off.");
  });

  test("keeps keyword matching's note when guided discovery is off", () => {
    expect(render(null)).toContain("The AI helper is off.");
  });
});
