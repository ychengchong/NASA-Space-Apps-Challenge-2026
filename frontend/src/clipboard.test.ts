import { afterEach, describe, expect, test, vi } from "vitest";
import { copyText } from "./clipboard";

const LINK = "https://trend.example/case?v=air_temp&p=60.17,24.94";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("copyText", () => {
  test("writes the text to the clipboard and says it did", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await expect(copyText(LINK)).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith(LINK);
  });

  test("says so when the browser offers no clipboard, as on a page without HTTPS", async () => {
    vi.stubGlobal("navigator", {});
    await expect(copyText(LINK)).resolves.toBe(false);
  });

  test("says so when the browser refuses the copy", async () => {
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await expect(copyText(LINK)).resolves.toBe(false);
  });

  test("passes on an error that is not the browser's refusal", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockRejectedValue(new TypeError("Broken"));
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await expect(copyText(LINK)).rejects.toBeInstanceOf(TypeError);
  });
});
