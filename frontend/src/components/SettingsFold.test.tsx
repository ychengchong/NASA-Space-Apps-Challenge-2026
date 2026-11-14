import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import { SettingsFold } from "./SettingsFold";

function renderFold(needed: boolean): string {
  return renderToStaticMarkup(
    <SettingsFold label="Change this case" hint="Variable, places, period and season" needed={needed}>
      <p>Case settings</p>
    </SettingsFold>,
  );
}

describe("SettingsFold", () => {
  test("folds the settings behind a button that says it is closed", () => {
    const html = renderFold(false);
    expect(html).toContain("Change this case");
    expect(html).toContain('aria-expanded="false"');
    expect(html).toMatch(/<div id="[^"]+" hidden="">/);
  });

  test("keeps the folded settings in the page", () => {
    expect(renderFold(false)).toContain("Case settings");
  });

  test("shows the settings without a button while the user has something to do in them", () => {
    const html = renderFold(true);
    expect(html).not.toContain("<button");
    expect(html).not.toContain("hidden");
    expect(html).toContain("Case settings");
  });
});
