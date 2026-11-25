/** @odoo-module **/

import { onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";

const CHATTER_WIDTH_KEY = "showroom_backend_theme.chatterWidth";
// Odoo's own design baselines: $o-mail-Chatter-minWidth and $o-form-sheet-min-width.
const MIN_CHATTER_WIDTH = 530;
const MIN_SHEET_WIDTH = 990;
const RESIZE_STOP_EVENTS = ["keydown", "mousedown", "mouseup"];

function readChatterWidth() {
    const width = Number(browser.localStorage.getItem(CHATTER_WIDTH_KEY));
    return Number.isFinite(width) && width >= MIN_CHATTER_WIDTH ? width : 0;
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        // Plain property on purpose: the drag already writes the CSS variable
        // directly, so a state update would only re-render the whole form.
        this.chatterWidth = { value: readChatterWidth() };
        this.stopChatterResize = null;
        onWillUnmount(() => this.stopChatterResize?.());
    },

    onStartChatterResize(ev) {
        const chatter = ev.target.closest(".o-mail-Form-chatter");
        if (ev.button !== 0 || !chatter) {
            return;
        }
        const maxWidth = Math.max(
            chatter.parentElement.offsetWidth - MIN_SHEET_WIDTH,
            MIN_CHATTER_WIDTH
        );
        const initialX = ev.pageX;
        const initialWidth = chatter.offsetWidth;
        const direction = getComputedStyle(chatter).direction === "rtl" ? -1 : 1;
        let width = 0;
        const resize = (moveEv) => {
            moveEv.preventDefault();
            moveEv.stopPropagation();
            if (!chatter.isConnected) {
                return;
            }
            width = Math.min(
                Math.max(
                    MIN_CHATTER_WIDTH,
                    initialWidth - (moveEv.pageX - initialX) * direction
                ),
                maxWidth
            );
            chatter.style.setProperty("--showroom-chatter-width", `${width}px`);
        };
        const cleanup = () => {
            document.removeEventListener("mousemove", resize, true);
            for (const eventName of RESIZE_STOP_EVENTS) {
                document.removeEventListener(eventName, stop, true);
            }
            window.removeEventListener("blur", stop, true);
            this.stopChatterResize = null;
        };
        const stop = (stopEv) => {
            stopEv.preventDefault();
            stopEv.stopPropagation();
            cleanup();
            if (width) {
                browser.localStorage.setItem(CHATTER_WIDTH_KEY, width);
                this.chatterWidth.value = width;
            }
        };
        document.addEventListener("mousemove", resize, true);
        for (const eventName of RESIZE_STOP_EVENTS) {
            document.addEventListener(eventName, stop, true);
        }
        window.addEventListener("blur", stop, true);
        this.stopChatterResize = cleanup;
    },

    onResetChatterWidth(ev) {
        ev.target
            .closest(".o-mail-Form-chatter")
            ?.style.removeProperty("--showroom-chatter-width");
        browser.localStorage.removeItem(CHATTER_WIDTH_KEY);
        this.chatterWidth.value = 0;
    },
});

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const chatter = res.querySelector(".o_form_renderer > .o-mail-Form-chatter");
        if (!chatter) {
            return res;
        }
        setAttributes(chatter, {
            "t-att-style":
                "__comp__.chatterWidth.value ? '--showroom-chatter-width:' + __comp__.chatterWidth.value + 'px' : ''",
        });
        const handle = createElement("span");
        handle.classList.add("showroom_chatter_resize");
        setAttributes(handle, {
            "t-on-mousedown.stop.prevent": "__comp__.onStartChatterResize.bind(__comp__)",
            "t-on-dblclick.stop.prevent": "__comp__.onResetChatterWidth.bind(__comp__)",
        });
        append(chatter, handle);
        return res;
    },
});
