import { describe, expect, test } from "vitest";
import { CASE_TABS, tabAfterKey } from "./caseTabs";

const COUNT = CASE_TABS.length;

describe("CASE_TABS", () => {
  test("puts the answer first, then explore, evidence and learn", () => {
    expect(CASE_TABS.map((tab) => tab.label)).toEqual(["Answer", "Explore", "Evidence", "Learn"]);
  });
});

describe("tabAfterKey", () => {
  test("steps right to the next tab and wraps from the last to the first", () => {
    expect(tabAfterKey("ArrowRight", 0, COUNT)).toBe(1);
    expect(tabAfterKey("ArrowRight", COUNT - 1, COUNT)).toBe(0);
  });

  test("steps left to the previous tab and wraps from the first to the last", () => {
    expect(tabAfterKey("ArrowLeft", 2, COUNT)).toBe(1);
    expect(tabAfterKey("ArrowLeft", 0, COUNT)).toBe(COUNT - 1);
  });

  test("goes to the first tab on Home and the last on End", () => {
    expect(tabAfterKey("Home", 2, COUNT)).toBe(0);
    expect(tabAfterKey("End", 1, COUNT)).toBe(COUNT - 1);
  });

  test("leaves every other key to the browser", () => {
    expect(tabAfterKey("Tab", 1, COUNT)).toBeNull();
    expect(tabAfterKey("Enter", 1, COUNT)).toBeNull();
    expect(tabAfterKey("ArrowDown", 1, COUNT)).toBeNull();
  });
});
