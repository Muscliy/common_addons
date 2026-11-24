import { registry } from "@web/core/registry";
import { ImageField, imageField } from "@web/views/fields/image/image_field";

export class WorkflowDefinitionIcon extends ImageField {
    static defaultProps = { ...ImageField.defaultProps, alt: "流程图标" };

    getUrl(imageFieldName) {
        if (!this.props.record.data[this.props.name] || !this.state.isValid) {
            return "/workflow_core/static/description/icon.svg";
        }
        return super.getUrl(imageFieldName);
    }
}

registry.category("fields").add("workflow_definition_icon", {
    ...imageField,
    component: WorkflowDefinitionIcon,
});
