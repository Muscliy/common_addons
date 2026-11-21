import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { IndicatorProgress } from "@custom_web_components/indicator_progress/indicator_progress";

describe.current.tags("cwc");

test("scales actual and target without capping overachievement", async () => {
    await mountWithCleanup(IndicatorProgress, {
        props: {
            actual: 200,
            target: 100,
            tone: "success",
            ariaLabel: "年度达成率：200.00%",
            actualText: "实际 200次",
            targetText: "目标 100次",
        },
    });
    const progress = queryOne(".o_indicator_progress");
    expect(progress).toHaveAttribute("aria-label", "年度达成率：200.00%");
    expect(progress).toHaveClass("text-success");
    const track = progress.querySelector(".o_indicator_progress_track");
    expect(track).not.toBe(null);
    expect(
        getComputedStyle(track).backgroundColor,
    ).not.toBe("rgba(0, 0, 0, 0)");
    expect(getComputedStyle(track).borderTopLeftRadius).toBe("999px");
    expect(progress.querySelector(".o_indicator_progress_fill").style.width).toBe("100%");
    expect(progress.querySelector(".o_indicator_progress_target").style.left).toBe(
        "50%",
    );
    const marker = progress.querySelector(".o_indicator_progress_target");
    const markerStyle = getComputedStyle(marker);
    expect(markerStyle.backgroundColor).not.toBe("rgba(0, 0, 0, 0)");
    expect(markerStyle.boxShadow).not.toBe("none");
    expect(markerStyle.width).toBe("7px");
    expect(markerStyle.height).toBe("19px");
    expect(markerStyle.borderTopWidth).toBe("2px");
    expect(progress.querySelector(".o_indicator_progress_values")).toHaveText(
        /实际 200次[\s\S]*目标 100次/,
    );
});

test("renders an unreported actual as an empty warning progress", async () => {
    await mountWithCleanup(IndicatorProgress, {
        props: {
            actual: null,
            target: 100,
            tone: "warning",
            ariaLabel: "年度达成率：未填报",
        },
    });
    const progress = queryOne(".o_indicator_progress");
    expect(progress).toHaveClass("text-warning");
    expect(progress.querySelector(".o_indicator_progress_fill").style.width).toBe("0%");
    expect(progress.querySelector(".o_indicator_progress_target").style.left).toBe(
        "100%",
    );
    expect(progress.querySelector(".o_indicator_progress_values")).toBe(null);
});
