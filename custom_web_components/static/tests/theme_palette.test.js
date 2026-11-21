import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mockService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    THEME_COLOR_COUNT,
    THEME_COLOR_GROUPS,
    ThemePalette,
} from "@custom_web_components/theme_palette/theme_palette";

describe.current.tags("cwc");

test("theme catalog covers every supported color family with unique tokens", () => {
    const tokens = THEME_COLOR_GROUPS.flatMap((group) => group.tokens);
    const tokenIds = new Set(tokens.map((token) => token.id));

    expect(THEME_COLOR_GROUPS.map((group) => group.id)).toEqual([
        "theme",
        "brand",
        "text",
        "neutral",
        "spectrum",
        "interface",
        "alerts",
    ]);
    expect(THEME_COLOR_COUNT).toBe(tokens.length);
    expect(THEME_COLOR_COUNT).toBeGreaterThan(60);
    expect(tokenIds).toHaveLength(tokens.length);
    expect(tokenIds).toInclude("theme-warning");
    expect(tokenIds).toInclude("theme-success");
    expect(tokenIds).toInclude("alert-danger-background");
});

test("every token has one resolvable runtime color source", () => {
    for (const token of THEME_COLOR_GROUPS.flatMap((group) => group.tokens)) {
        expect(Boolean(token.variable) !== Boolean(token.probeClass)).toBe(true);
        expect(token.cssName.length).toBeGreaterThan(0);
        if (token.probeClass) {
            expect(token.property.length).toBeGreaterThan(0);
        }
    }
});

test("palette renders and resolves every color from the active stylesheets", async () => {
    mockService("notification", { add() {} });
    await mountWithCleanup(ThemePalette);
    await animationFrame();

    expect(".o_cwc_theme_group").toHaveCount(THEME_COLOR_GROUPS.length);
    expect(".o_cwc_theme_token").toHaveCount(THEME_COLOR_COUNT);
    expect(".o_cwc_theme_token_value:contains('读取中')").toHaveCount(0);
    expect(".o_cwc_theme_token[data-token='theme-warning'] .o_cwc_theme_token_value").toHaveText(
        /^(#|rgb)/,
    );
});
