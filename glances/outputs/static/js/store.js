import { reactive } from "vue";

const MAX_HISTORY = 120;

export const store = reactive({
	args: undefined,
	config: undefined,
	data: undefined,
	status: "IDLE",
	history: {
		cpu: [],
		mem: [],
		swap: [],
		load: [],
		gpu: [],
		npu: [],
	},
});

export function pushHistory(stats) {
	if (!stats) return;

	if (stats.cpu != null && stats.cpu.total != null) {
		store.history.cpu.push(stats.cpu.total);
		if (store.history.cpu.length > MAX_HISTORY) store.history.cpu.shift();
	}

	if (stats.mem != null && stats.mem.percent != null) {
		store.history.mem.push(stats.mem.percent);
		if (store.history.mem.length > MAX_HISTORY) store.history.mem.shift();
	}

	if (stats.memswap != null && stats.memswap.percent != null) {
		store.history.swap.push(stats.memswap.percent);
		if (store.history.swap.length > MAX_HISTORY) store.history.swap.shift();
	}

	if (stats.load != null && stats.load.min1 != null) {
		store.history.load.push(stats.load.min1);
		if (store.history.load.length > MAX_HISTORY) store.history.load.shift();
	}

	if (stats.gpu != null && Array.isArray(stats.gpu) && stats.gpu.length > 0) {
		const meanProc =
			stats.gpu.reduce((s, g) => s + (g.proc || 0), 0) / stats.gpu.length;
		store.history.gpu.push(meanProc);
		if (store.history.gpu.length > MAX_HISTORY) store.history.gpu.shift();
	}

	if (stats.npu != null && Array.isArray(stats.npu) && stats.npu.length > 0) {
		const meanProc =
			stats.npu.reduce((s, n) => s + (n.proc || 0), 0) / stats.npu.length;
		store.history.npu.push(meanProc);
		if (store.history.npu.length > MAX_HISTORY) store.history.npu.shift();
	}
}
