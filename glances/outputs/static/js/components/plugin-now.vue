<template>
    <section id="now" class="plugin">
        <span>{{ value }}</span>
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