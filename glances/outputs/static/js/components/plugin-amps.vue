<template>
    <section id="amps" class="plugin" v-if="hasAmps">
        <table class="table table-sm table-borderless">
            <tbody>
                <tr v-for="(process, processId) in processes" :key="processId">
                    <td :class="getNameDecoration(process)">{{ process.name }}</td>
                    <td v-if="process.regex">{{ process.count }}</td>
                    <td class="process-result" v-html="$filters.nl2br(process.result)"></td>
                </tr>
            </tbody>
        </table>

        <!-- <div class="table">
            <div class="table-row" v-for="(process, processId) in processes" :key="processId">
                <div class="table-cell text-start" :class="getNameDecoration(process)">
                    {{ process.name }}
                </div>
                <div class="table-cell text-start" v-if="process.regex">{{ process.count }}</div>
                <div
                    class="table-cell text-start process-result"
                    v-html="$filters.nl2br(process.result)"
                ></div>
            </div>
        </div> -->

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
        },
        hasAmps() {
            return this.processes.length > 0;
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