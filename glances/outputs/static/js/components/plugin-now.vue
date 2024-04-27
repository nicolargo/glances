<template>
    <section id="now" class="plugin">
        <div class="table-row">
            <div class="table-cell text-left">{{ localDate(value) }}</div>
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
        value() {
            return this.data.stats['now'];
        }
    },
    methods: {
        localDate(date) {
            console.log(date)
            var local_date = new Date(date)
            console.log(local_date)
            return local_date.toISOString().slice(0, 19).replace(/[^\d-:]/, ' ');
        }
    }
};
</script>
