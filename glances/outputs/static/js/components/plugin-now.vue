<template>
    <section id="now" class="plugin">
        <div class="table-row">
            <div class="table-cell text-left">{{ localDate(date_iso) }}</div>
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
        date_iso() {
            return this.data.stats['now']['iso'];
        }
    },
    methods: {
        localDate(date) {
            return new Date(date).toLocaleString();
        }
    }
};
</script>
