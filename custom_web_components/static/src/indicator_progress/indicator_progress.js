import { Component } from "@odoo/owl";

export class IndicatorProgress extends Component {
    static template = "custom_web_components.IndicatorProgress";
    static props = {
        actual: { type: [Number, { value: null }] },
        target: { type: [Number, { value: null }] },
        tone: {
            type: [
                { value: "success" },
                { value: "warning" },
                { value: "danger" },
            ],
        },
        ariaLabel: { type: String },
        actualText: { type: String, optional: true },
        targetText: { type: String, optional: true },
    };

    static defaultProps = {
        actualText: "",
        targetText: "",
    };

    get chartMaximum() {
        return Math.max(this.props.actual ?? 0, this.props.target ?? 0, 1);
    }

    get actualWidth() {
        return this.position(this.props.actual);
    }

    get targetPosition() {
        return this.position(this.props.target);
    }

    position(value) {
        const percentage = (value ?? 0) / this.chartMaximum * 100;
        return Math.min(100, Math.max(0, percentage));
    }
}
