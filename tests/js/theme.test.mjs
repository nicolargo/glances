import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { applyTheme } from "../../glances/outputs/static/js/theme.js";

// A DOM with just what applyTheme() touches.
function stubDom() {
	const head = {
		children: [],
		appendChild(node) {
			this.children.push(node);
		},
	};
	globalThis.document = {
		documentElement: { dataset: {} },
		head,
		getElementById: (id) => head.children.find((node) => node.id === id) || null,
		createElement: (tag) => ({ tag, id: "", textContent: "" }),
	};
	return head;
}

function stubTheme(body) {
	globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => body });
}

beforeEach(() => {
	delete globalThis.fetch;
	delete globalThis.document;
});

test("applyTheme sets data-theme and adds no stylesheet for a built-in theme", async () => {
	const head = stubDom();
	stubTheme({ name: "light", css: null });
	await applyTheme();
	assert.equal(document.documentElement.dataset.theme, "light");
	assert.equal(head.children.length, 0);
});

test("applyTheme injects the user's stylesheet as text for a custom theme", async () => {
	const head = stubDom();
	const css = ':root[data-theme="custom"] { --gl-bg: #16276f; }';
	stubTheme({ name: "custom", css });
	await applyTheme();
	assert.equal(document.documentElement.dataset.theme, "custom");
	assert.equal(head.children.length, 1);
	assert.equal(head.children[0].tag, "style");
	assert.equal(head.children[0].textContent, css);
});

test("applyTheme reuses its stylesheet element on a second call", async () => {
	const head = stubDom();
	stubTheme({ name: "custom", css: "a {}" });
	await applyTheme();
	stubTheme({ name: "custom", css: "b {}" });
	await applyTheme();
	assert.equal(head.children.length, 1);
	assert.equal(head.children[0].textContent, "b {}");
});

test("applyTheme stays on the dark theme when the endpoint is unreachable", async () => {
	const head = stubDom();
	globalThis.fetch = async () => {
		throw new TypeError("network error");
	};
	await applyTheme();
	assert.equal(document.documentElement.dataset.theme, "dark");
	assert.equal(head.children.length, 0);
});
