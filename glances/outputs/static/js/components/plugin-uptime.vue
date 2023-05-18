<template>
    <section class="plugin" id="uptime">
        <span>Uptime: {{ value }}</span>
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
            return this.data.stats['uptime'];
        }
    }
};
</script>