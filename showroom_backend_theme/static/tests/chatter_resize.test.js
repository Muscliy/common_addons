import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, queryOne, waitFor } from "@odoo/hoot-dom";
import {
    SIZES,
    defineMailModels,
    openFormView,
    patchUiSize,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { browser } from "@web/core/browser/browser";

import "@showroom_backend_theme/webclient/chatter_resize";

describe.current.tags("desktop");
defineMailModels();

const CHATTER_WIDTH_KEY = "showroom_backend_theme.chatterWidth";

async function openPartnerForm(size) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John" });
    await patchUiSize({ size });
    await start();
    await openFormView("res.partner", partnerId);
}

test("drag the resize handle and persist the width", async () => {
    browser.localStorage.removeItem(CHATTER_WIDTH_KEY);
    await openPartnerForm(SIZES.XXL);
    await waitFor(".o-mail-Form-chatter.o-aside > .showroom_chatter_resize");
    const handle = queryOne(".o-mail-Form-chatter.o-aside > .showroom_chatter_resize");
    await manuallyDispatchProgrammaticEvent(handle, "mousedown", { button: 0, pageX: 1200 });
    await manuallyDispatchProgrammaticEvent(document, "mousemove", { pageX: 1000 });
    await manuallyDispatchProgrammaticEvent(document, "mouseup", {});
    const chatter = queryOne(".o-mail-Form-chatter.o-aside");
    const storedWidth = Number(browser.localStorage.getItem(CHATTER_WIDTH_KEY));
    expect(storedWidth).toBeGreaterThanOrEqual(530);
    expect(chatter.style.getPropertyValue("--showroom-chatter-width")).toBe(`${storedWidth}px`);
});

test("double click resets the saved width", async () => {
    browser.localStorage.setItem(CHATTER_WIDTH_KEY, "600");
    await openPartnerForm(SIZES.XXL);
    await waitFor(".o-mail-Form-chatter.o-aside > .showroom_chatter_resize");
    const chatter = queryOne(".o-mail-Form-chatter.o-aside");
    expect(chatter.style.getPropertyValue("--showroom-chatter-width")).toBe("600px");
    await manuallyDispatchProgrammaticEvent(
        queryOne(".showroom_chatter_resize"),
        "dblclick",
        {}
    );
    expect(chatter.style.getPropertyValue("--showroom-chatter-width")).toBe("");
    expect(browser.localStorage.getItem(CHATTER_WIDTH_KEY)).toBe(null);
});

test("bottom chatter keeps its resize handle hidden", async () => {
    await openPartnerForm(SIZES.LG);
    await waitFor(".o-mail-Form-chatter:not(.o-aside) > .showroom_chatter_resize");
    const handle = queryOne(".o-mail-Form-chatter:not(.o-aside) > .showroom_chatter_resize");
    expect(getComputedStyle(handle).display).toBe("none");
});
