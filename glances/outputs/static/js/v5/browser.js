// Glances v5 WebUI — the browser page's pure helpers (P3-6).
//
// The page lists /api/5/serverslist, served by `glances-v5 -s --browser`.
// Everything here mirrors the TUI browser (glances/outputs/browser_curses_v5.py)
// so the two read the same: status colours, the NAME cell, the column
// headers, the value format.

import { levelClass } from "./levels.js";

// The TUI browser's `_STATUS_ROLE`: a status is coloured like a level.
const STATUS_LEVEL = {
	ONLINE: "ok",
	UNSUPPORTED: "careful",
	PROTECTED: "warning",
	OFFLINE: "critical",
};

export function statusClass(status) {
	const level = STATUS_LEVEL[status];
	return level ? levelClass({ level }) : "";
}

export function displayName(server) {
	return server.alias || server.name;
}

// Where a click on a server goes: its own Web UI (v4 parity).
//
// The name comes from `[serverlist]` or from a Zeroconf announcement's
// ADDRESS (never its announced name, CVE-2026-32634), but it is still data:
// only an http(s) URL or a plain host can become a link. Anything else --
// `javascript:`, a host smuggling a path or credentials -- gets no link.
export function serverHref(server) {
	const name = String(server.name || "");
	let url;
	try {
		url = name.includes("://") ? new URL(name) : new URL(`http://${name}:${Number(server.port)}/`);
	} catch {
		return null;
	}
	if (url.protocol !== "http:" && url.protocol !== "https:") return null;
	if (url.username || url.password) return null;
	if (!name.includes("://") && (url.pathname !== "/" || url.search || url.hash)) return null;
	return url.href;
}

// The union of every server's column labels, in first-seen order: an
// OFFLINE server has none, and the table still needs its headers.
export function columnLabels(servers) {
	const labels = [];
	for (const server of servers) {
		for (const label of Object.keys(server.columns || {})) {
			if (!labels.includes(label)) labels.push(label);
		}
	}
	return labels;
}

// `sensors:value:Ambient` -> ["SENSORS", "VALUE AMBIENT"]: the TUI's two
// header rows (plugin, then field and key).
export function headerRows(label) {
	const [plugin, field, key] = label.split(":");
	return [plugin.toUpperCase(), (key ? `${field} ${key}` : field || "").toUpperCase()];
}

export function formatCell(cell) {
	if (!cell || cell.value === null || cell.value === undefined) return "?";
	if (typeof cell.value === "number" && !Number.isInteger(cell.value)) return cell.value.toFixed(1);
	return String(cell.value);
}

export function cellClass(cell) {
	return cell ? levelClass({ level: cell.level }) : "";
}

// "ONLINE: 2  OFFLINE: 1", in first-seen order, as the TUI's second line.
export function statusCounts(servers) {
	const counts = new Map();
	for (const server of servers) counts.set(server.status, (counts.get(server.status) || 0) + 1);
	return [...counts].map(([status, count]) => ({ status, count }));
}

export function title(count) {
	if (count === 0) return "No Glances server available";
	return `${count} Glances server${count > 1 ? "s" : ""} available`;
}
