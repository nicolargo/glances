<template>
    <section id="now" class="plugin">
        <div class="table-row">
            <div class="table-cell text-start">{{ date_custom }}</div>
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
        date_custom() {
            return this.data.stats['now']['custom'];
        }
    }
};
</script>
