import { registry } from "@web/core/registry";

export const componentPreferenceService = {
    dependencies: ["orm"],
    async: ["load", "save", "reset"],
    start(env, { orm }) {
        // Serialize mutations from multiple mounted components using the same scope.
        const pending = new Map();
        const args = (scope) => [
            scope.type,
            scope.model,
            scope.viewId || false,
            scope.key || "default",
        ];
        function mutate(scope, method, config) {
            const key = JSON.stringify(args(scope));
            const previous = pending.get(key) || Promise.resolve();
            const operation = previous.then(
                () =>
                    orm.call(
                        "web.component.preference",
                        method,
                        args(scope),
                        config === undefined ? {} : { config },
                    ),
                () =>
                    orm.call(
                        "web.component.preference",
                        method,
                        args(scope),
                        config === undefined ? {} : { config },
                    ),
            );
            pending.set(key, operation);
            const cleanup = () => {
                if (pending.get(key) === operation) {
                    pending.delete(key);
                }
            };
            operation.then(cleanup, cleanup);
            return operation;
        }
        return {
            load: (scope) => orm.call("web.component.preference", "get_preference", args(scope)),
            save: (scope, config) => mutate(scope, "save_preference", config),
            reset: (scope) => mutate(scope, "reset_preference"),
        };
    },
};

registry.category("services").add("component_preference", componentPreferenceService);
