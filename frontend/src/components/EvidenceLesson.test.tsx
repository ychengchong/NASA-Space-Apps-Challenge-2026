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

test("is folded to one line until the learner opens it", () => {
  const html = renderToStaticMarkup(<EvidenceLesson />);
  expect(html).toContain("<details");
  expect(html).not.toContain("<details open");
  expect(html).toContain("One question on reading a result that is not significant");
});
