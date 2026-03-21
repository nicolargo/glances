<template>
	<canvas ref="canvas" :height="height" style="display:block;flex:1"></canvas>
</template>

<script>
export default {
	props: {
		data: { type: Array, default: () => [] },
		max: { type: Number, default: 100 },
		height: { type: Number, default: 22 },
		color: { type: String, default: '#00ff88' },
	},
	mounted() {
		this.resizeObserver = new ResizeObserver(() => this.draw());
		this.resizeObserver.observe(this.$refs.canvas.parentElement);
		this.$nextTick(() => this.draw());
	},
	beforeUnmount() {
		if (this.resizeObserver) this.resizeObserver.disconnect();
	},
	watch: {
		data: { handler() { this.draw(); }, deep: true },
		color() { this.draw(); },
	},
	methods: {
		draw() {
			const c = this.$refs.canvas;
			if (!c) return;
			const parent = c.parentElement;
			if (!parent) return;

			// Size canvas to fill available flex space
			const siblings = [...parent.children].filter(el => el !== c);
			const gap = parseFloat(getComputedStyle(parent).gap) || 8;
			const usedW = siblings.reduce((s, el) => s + el.offsetWidth, 0);
			const w = Math.max(40, Math.floor(parent.offsetWidth - usedW - gap * siblings.length));
			c.width = w;

			const ctx = c.getContext('2d');
			const W = c.width, H = c.height;
			ctx.clearRect(0, 0, W, H);

			const pts = this.data.slice(-60);
			if (pts.length < 2) return;

			const sx = W / (pts.length - 1);
			const pad = 2;
			const uh = H - pad * 2;
			const maxVal = this.max || 1;
			const tx = i => i * sx;
			const ty = v => pad + uh - Math.min(v, maxVal) / maxVal * uh;
			const color = this.color;

			// gradient fill
			const g = ctx.createLinearGradient(0, 0, 0, H);
			g.addColorStop(0, color + '22');
			g.addColorStop(1, color + '03');
			ctx.beginPath();
			ctx.moveTo(tx(0), ty(pts[0]));
			for (let i = 1; i < pts.length; i++) ctx.lineTo(tx(i), ty(pts[i]));
			ctx.lineTo(tx(pts.length - 1), H);
			ctx.lineTo(0, H);
			ctx.closePath();
			ctx.fillStyle = g;
			ctx.fill();

			// line
			ctx.save();
			ctx.shadowColor = color;
			ctx.shadowBlur = 5;
			ctx.beginPath();
			ctx.moveTo(tx(0), ty(pts[0]));
			for (let i = 1; i < pts.length; i++) ctx.lineTo(tx(i), ty(pts[i]));
			ctx.strokeStyle = color;
			ctx.lineWidth = 1.5;
			ctx.lineJoin = 'round';
			ctx.stroke();
			ctx.restore();

			// tip dot
			const lx = tx(pts.length - 1);
			const ly = ty(pts[pts.length - 1]);
			ctx.save();
			ctx.shadowColor = color;
			ctx.shadowBlur = 8;
			ctx.beginPath();
			ctx.arc(lx, ly, 2.5, 0, Math.PI * 2);
			ctx.fillStyle = color;
			ctx.fill();
			ctx.restore();
		},
	},
};
</script>
