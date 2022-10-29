<template>
    <section id="cloud" class="plugin" v-if="instance || provider">
        <span class="title">{{ provider }}</span> {{ instance }}
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
            return this.data.stats['cloud'];
        },
        provider() {
            return this.stats['ami-id'] !== undefined ? 'AWS EC2' : null;
        },
        instance() {
            const { stats } = this;
            return this.stats['ami-id'] !== undefined
                ? `${stats['instance-type']} instance ${stats['instance-id']} (${stats['reggion']})`
                : null;
        }
    }
};
</script>