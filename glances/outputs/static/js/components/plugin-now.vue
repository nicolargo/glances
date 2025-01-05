<template>
    <section id="now" class="plugin">
        <span>{{ date_custom }}</span>
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
