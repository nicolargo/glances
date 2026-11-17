// Applies `[outputs] theme` to the page: the `data-theme` attribute, plus the
// user's stylesheet when the theme is a CSS file (see resolveTheme(), api.js).

import { resolveTheme } from "./api.js";

const STYLE_ID = "gl-user-theme";

export async function applyTheme() {
	const { name, css } = await resolveTheme();
	// The static template hardcodes "dark" so the page has a theme before
	// this fetch resolves. See the design spec, section 5.
	document.documentElement.dataset.theme = name;
	if (css === null) return;
	let style = document.getElementById(STYLE_ID);
	if (!style) {
		style = document.createElement("style");
		style.id = STYLE_ID;
		// Appended after the bundle's own stylesheet: at equal specificity the
		// user's block wins. The CSP allows it (`style-src 'unsafe-inline'`),
		// and `textContent` keeps the CSS text, never markup.
		document.head.appendChild(style);
	}
	style.textContent = css;
}
