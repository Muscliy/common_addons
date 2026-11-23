import { expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { ThemeSwitcher } from "@showroom_backend_theme/webclient/theme_switcher";

defineMailModels();

test("selects Dark, persists it and reloads the current page", async () => {
    cookie.set("color_scheme", "light");
    patchWithCleanup(browser.location, { reload: () => expect.step("reload") });
    await mountWithCleanup(ThemeSwitcher);
    await contains('[aria-label="切换主题"]').click();
    expect('[role="menuitemradio"][aria-checked="true"]').toHaveText("Light");
    await contains('[role="menuitemradio"]:contains(Dark)').click();
    expect(cookie.get("color_scheme")).toBe("dark");
    expect.verifySteps(["reload"]);
});

test("switches back to Light and ignores the current or an unsupported scheme", () => {
    cookie.set("color_scheme", "dark");
    patchWithCleanup(browser.location, { reload: () => expect.step("reload") });
    const switcher = new ThemeSwitcher({}, {}, {});
    expect(switcher.scheme).toBe("dark");
    switcher.selectScheme("dark");
    switcher.selectScheme("system");
    expect.verifySteps([]);
    switcher.selectScheme("light");
    expect(cookie.get("color_scheme")).toBe("light");
    expect.verifySteps(["reload"]);
});

test("defaults to Light for missing or unsupported preferences", () => {
    const switcher = new ThemeSwitcher({}, {}, {});
    cookie.delete("color_scheme");
    expect(switcher.scheme).toBe("light");
    cookie.set("color_scheme", "invalid");
    expect(switcher.scheme).toBe("light");
});
