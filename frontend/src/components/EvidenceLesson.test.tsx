import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";
import { EvidenceLesson } from "./EvidenceLesson";

test("asks the learner to interpret evidence before revealing feedback", () => {
  const html = renderToStaticMarkup(<EvidenceLesson />);
  expect(html).toContain("Choose an interpretation before reading the guidance");
  expect(html).toContain("evidence for a monotonic trend is insufficient");
  expect(html).not.toContain("Correct.");
  expect(html).toContain('type="radio"');
});
