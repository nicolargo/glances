<template>
    <section id="processcount" class="plugin">
        <span class="title">TASKS</span>
        <span>{{ total }} ({{ thread }} thr),</span>
        <span>{{ running }} run,</span>
        <span>{{ sleeping }} slp,</span>
        <span>{{ stopped }} oth</span>
        <span class="title">{{ sorter.auto ? 'sorted automatically' : 'sorted' }}</span>
        <span>by {{ sorter.getColumnLabel(sorter.column) }}</span>
    </section>
</template>

<script>
export default {
    props: {
        data: {
            type: Object
        },
        sorter: {
            type: Object
        }
    },
    computed: {
        stats() {
            return this.data.stats['processcount'];
        },
        total() {
            return this.stats['total'] || 0;
        },
        running() {
            return this.stats['running'] || 0;
        },
        sleeping() {
            return this.stats['sleeping'] || 0;
        },
        stopped() {
            return this.stats['stopped'] || 0;
        },
        thread() {
            return this.stats['thread'] || 0;
        }
    }
};
</script>