<template>
    <section class="plugin" id="irq">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">IRQ</th>
                    <th scope="col" class="text-end">Rate/s</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(irq, irqId) in irqs" :key="irqId">
                    <td scope="row">{{ irq.irq_line }}</td>
                    <td scope="row" class="text-end">{{ irq.irq_rate }}</td>
                </tr>
            </tbody>
        </table>
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