<template>
    <section class="plugin" id="irq">
        <div class="table-row" v-if="irqs.length > 0">
            <div class="table-cell text-left title">IRQ</div>
            <div class="table-cell"></div>
            <div class="table-cell">Rate/s</div>
        </div>
        <div class="table-row" v-for="(irq, irqId) in irqs" :key="irqId">
            <div class="table-cell text-left">{{ irq.irq_line }}</div>
            <div class="table-cell"></div>
            <div class="table-cell">
                <span>{{ irq.irq_rate }}</span>
            </div>
        </div>
    </section>
</template>

<script>
export default {
    props: {
        data: {
            type: Object
        }
    },
    computed: {
        stats() {
            return this.data.stats['irq'];
        },
        irqs() {
            return this.stats.map((IrqData) => {
                return {
                    irq_line: IrqData['irq_line'],
                    irq_rate: IrqData['irq_rate']
                };
            });
        }
    }
};
</script>