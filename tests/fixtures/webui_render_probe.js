// Minimal DOM + vm harness used by test_webserver_v5.py to prove that the
// v5 bundle actually RENDERS, rather than merely being served as bytes.
//
// It stubs only what glances5.js touches: document (element/text/comment
// node creation + a `#app` querySelector), window (existence check only)
// and fetch (resolved with empty JSON so the component's data-fetching
// paths don't throw). No jsdom, no npm dependency -- just enough of the
// DOM tree API for Vue's runtime-dom nodeOps to walk.
//
// Usage: node webui_render_probe.js <path-to-bundle.js>
// Prints one JSON line to stdout: {"childCount", "nodeType", "tagName"}
// describing what ended up inside the <div id="app"> mount target.

"use strict";

const fs = require("fs");
const vm = require("vm");

const ELEMENT_NODE = 1;
const TEXT_NODE = 3;
const COMMENT_NODE = 8;

class FakeNode {
	constructor(nodeType) {
		this.nodeType = nodeType;
		this.parentNode = null;
		this.childNodes = [];
	}

	get nextSibling() {
		if (!this.parentNode) return null;
		const idx = this.parentNode.childNodes.indexOf(this);
		return this.parentNode.childNodes[idx + 1] ?? null;
	}

	appendChild(child) {
		return this.insertBefore(child, null);
	}

	insertBefore(child, anchor) {
		if (child.parentNode) child.parentNode.removeChild(child);
		if (anchor == null) {
			this.childNodes.push(child);
		} else {
			const idx = this.childNodes.indexOf(anchor);
			this.childNodes.splice(idx === -1 ? this.childNodes.length : idx, 0, child);
		}
		child.parentNode = this;
		return child;
	}

	removeChild(child) {
		const idx = this.childNodes.indexOf(child);
		if (idx !== -1) this.childNodes.splice(idx, 1);
		child.parentNode = null;
		return child;
	}

	get textContent() {
		if (this.nodeType === TEXT_NODE || this.nodeType === COMMENT_NODE) return this._text ?? "";
		return this.childNodes.map((c) => c.textContent).join("");
	}

	set textContent(value) {
		if (this.nodeType === TEXT_NODE || this.nodeType === COMMENT_NODE) {
			this._text = value;
			return;
		}
		for (const child of this.childNodes.splice(0)) child.parentNode = null;
		if (value) {
			const t = new FakeNode(TEXT_NODE);
			t._text = value;
			this.appendChild(t);
		}
	}

	get nodeValue() {
		return this._text ?? null;
	}

	set nodeValue(value) {
		this._text = value;
	}
}

class FakeElement extends FakeNode {
	constructor(tag) {
		super(ELEMENT_NODE);
		this.tagName = String(tag).toUpperCase();
		this._attrs = new Map();
		this._classes = new Set();
		this.classList = {
			add: (...cs) => cs.forEach((c) => this._classes.add(c)),
			remove: (...cs) => cs.forEach((c) => this._classes.delete(c)),
			toggle: (c) => (this._classes.has(c) ? this._classes.delete(c) : this._classes.add(c)),
			contains: (c) => this._classes.has(c),
		};
		this.style = { cssText: "", setProperty() {}, removeProperty() {} };
	}

	get id() {
		return this._attrs.get("id") ?? "";
	}

	setAttribute(name, value) {
		this._attrs.set(name, String(value));
	}

	getAttribute(name) {
		return this._attrs.has(name) ? this._attrs.get(name) : null;
	}

	removeAttribute(name) {
		this._attrs.delete(name);
	}

	addEventListener() {}
	removeEventListener() {}
}

function findById(root, id) {
	if (root.nodeType === ELEMENT_NODE && root.id === id) return root;
	for (const child of root.childNodes) {
		const found = findById(child, id);
		if (found) return found;
	}
	return null;
}

const body = new FakeElement("body");
const appDiv = new FakeElement("div");
appDiv.setAttribute("id", "app");
body.appendChild(appDiv);

const document = {
	createElement: (tag) => new FakeElement(tag),
	createElementNS: (_ns, tag) => new FakeElement(tag),
	createTextNode: (text) => {
		const n = new FakeNode(TEXT_NODE);
		n._text = text;
		return n;
	},
	createComment: (text) => {
		const n = new FakeNode(COMMENT_NODE);
		n._text = text;
		return n;
	},
	querySelector: (selector) => {
		if (selector.startsWith("#")) return findById(body, selector.slice(1));
		return null;
	},
	body,
};

async function fakeFetch() {
	return { ok: true, status: 200, json: async () => ({}) };
}

// Vue's mount() does `instanceof Element` / `instanceof SVGElement` checks
// on the container node. Map the globals to our fake classes so those
// checks resolve instead of throwing ReferenceError, and so our appDiv
// (a FakeElement) is correctly recognised as an Element.
class FakeSVGElement extends FakeElement {}

const sandbox = { document, fetch: fakeFetch, console, Node: FakeNode, Element: FakeElement, SVGElement: FakeSVGElement };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

const bundlePath = process.argv[2];
const code = fs.readFileSync(bundlePath, "utf8");
vm.runInContext(code, sandbox, { filename: bundlePath });

const result = { childCount: appDiv.childNodes.length, nodeType: null, tagName: null };
const first = appDiv.childNodes[0];
if (first) {
	result.nodeType = first.nodeType;
	result.tagName = first.tagName ?? null;
}
process.stdout.write(JSON.stringify(result));
