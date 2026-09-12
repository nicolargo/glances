// Glances v5 WebUI -- the SMART attribute keys whose raw value is formatted
// with auto_unit() instead of printed as-is.
//
// A mirror of LARGE_VALUE_KEYS (glances/plugins/smart/__init__.py:70-79): the
// browser cannot import Python. tests/test_webui_v5_smart_keys_drift.py fails
// on drift -- this copy decides displayed NUMBERS, not layout, which is why it
// gets a test of its own (the degrade.js precedent).
export const LARGE_VALUE_KEYS = new Set([
	"bytesWritten",
	"bytesRead",
	"dataUnitsRead",
	"dataUnitsWritten",
	"hostReadCommands",
	"hostWriteCommands",
]);
