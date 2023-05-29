<template>
    <section id="now" class="plugin">
        <div class="table-row">
            <div class="table-cell text-left">{{ value }}</div>
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
    }
};
</script>
