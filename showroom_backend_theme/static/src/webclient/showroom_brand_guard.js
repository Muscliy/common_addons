/** @odoo-module **/

const brandPattern = /OdooBot|Odoo Bot|Odoo/gi;
const protectedContentSelector = [
    "script",
    "style",
    "code",
    "pre",
    "input",
    "textarea",
    "[contenteditable='true']",
    ".o_field_widget",
    ".o-mail-Message-body",
].join(",");

function replaceBrand(value) {
    return value
        .replace(/OdooBot|Odoo Bot/gi, "TYJ 助手")
        .replace(/Odoo/gi, "TYJ");
}

function isProtected(element) {
    if (element?.closest?.(".o_modules_kanban, .o_module_form")) {
        return false;
    }
    return Boolean(element?.closest?.(protectedContentSelector));
}

function sanitizeElement(element) {
    if (isProtected(element)) {
        return;
    }
    for (const attribute of ["title", "aria-label", "alt", "placeholder"]) {
        const value = element.getAttribute?.(attribute);
        if (value && brandPattern.test(value)) {
            element.setAttribute(attribute, replaceBrand(value));
        }
        brandPattern.lastIndex = 0;
    }
    if (element.matches?.("a[href*='odoo.com'], a[href*='odoo.com'] *")) {
        const link = element.closest("a");
        if (link && !isProtected(link)) {
            const parent = link.parentElement;
            if (parent && /^Powered by\s*(Odoo)?$/i.test(parent.textContent.trim())) {
                parent.textContent = "TYJ 企业管理平台";
            } else {
                link.hidden = true;
            }
        }
    }
}

function sanitizeTree(root) {
    if (root.nodeType === Node.TEXT_NODE) {
        const parent = root.parentElement;
        if (!isProtected(parent) && brandPattern.test(root.nodeValue || "")) {
            root.nodeValue = replaceBrand(root.nodeValue);
        }
        brandPattern.lastIndex = 0;
        return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE) {
        return;
    }
    sanitizeElement(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.nodeType === Node.TEXT_NODE) {
            const parent = node.parentElement;
            if (!isProtected(parent) && brandPattern.test(node.nodeValue || "")) {
                node.nodeValue = replaceBrand(node.nodeValue);
            }
            brandPattern.lastIndex = 0;
        } else {
            sanitizeElement(node);
        }
    }
}

function startBrandGuard() {
    if (document.documentElement.dataset.tyjBrandGuard === "active") {
        return;
    }
    document.documentElement.dataset.tyjBrandGuard = "active";
    sanitizeTree(document.body);
    document.title = replaceBrand(document.title);
    new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.type === "characterData") {
                sanitizeTree(mutation.target);
            }
            if (mutation.type === "attributes") {
                sanitizeElement(mutation.target);
            }
            for (const node of mutation.addedNodes) {
                sanitizeTree(node);
            }
        }
        document.title = replaceBrand(document.title);
    }).observe(document.body, {
        attributes: true,
        attributeFilter: ["title", "aria-label", "alt", "placeholder", "href"],
        childList: true,
        characterData: true,
        subtree: true,
    });
}

if (document.body) {
    startBrandGuard();
} else {
    document.addEventListener("DOMContentLoaded", startBrandGuard, { once: true });
}
