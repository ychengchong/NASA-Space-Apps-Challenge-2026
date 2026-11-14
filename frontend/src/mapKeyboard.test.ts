import { describe, expect, test } from "vitest";
import { picksMapCentre } from "./mapKeyboard";

describe("picksMapCentre", () => {
  const map = new EventTarget();

  test("picks the centre on Enter while the map itself has focus", () => {
    expect(picksMapCentre({ key: "Enter", target: map }, map)).toBe(true);
  });

  test("leaves Enter on a control inside the map, such as the zoom buttons, to that control", () => {
    expect(picksMapCentre({ key: "Enter", target: new EventTarget() }, map)).toBe(false);
  });

  test("leaves the arrow keys to move the map", () => {
    expect(picksMapCentre({ key: "ArrowUp", target: map }, map)).toBe(false);
  });
});
