// Glances v5 WebUI -- collection column helpers.
//
// `_levels` for a collection is keyed by the primary key's VALUE. The payload
// now publishes the key's NAME as `_key` (see get_api_payload), so this rule
// lives here once instead of being retyped in every collection component.

import { levelClass, itemLevel } from "./levels.js";

export function cellClassFor(payload, item, field) {
	const keyField = payload && payload._key;
	if (!keyField) return "";
	return levelClass(itemLevel(payload, item[keyField], field));
}
