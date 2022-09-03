<template>
    <section id="amps" class="plugin">
        <div class="table">
            <div class="table-row" v-for="(process, processId) in processes" :key="processId">
                <div class="table-cell text-left" :class="getNameDecoration(process)">
                    {{ process.name }}
                </div>
                <div class="table-cell text-left" v-if="process.regex">{{ process.count }}</div>
                <div
                    class="table-cell text-left process-result"
                    v-html="$filters.nl2br(process.result)"
                ></div>
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
            return this.data.stats['amps'];
        },
        processes() {
            return this.stats.filter((process) => process.result !== null);
        }
    },
    methods: {
        getNameDecoration(process) {
            const count = process.count;
            const countMin = process.countmin;
            const countMax = process.countmax;
            let decoration = 'ok';
            if (count > 0) {
                if (
                    (countMin === null || count >= countMin) &&
                    (countMax === null || count <= countMax)
                ) {
                    decoration = 'ok';
                } else {
                    decoration = 'careful';
                }
            } else {
                decoration = countMin === null ? 'ok' : 'critical';
            }
            return decoration;
        }
    }
};
</script>