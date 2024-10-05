<template>
    <section class="plugin" id="cloud" v-if="instance || provider">
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
            return this.stats['id'] !== undefined ? `${stats['platform']}` : null;
        },
        instance() {
            const { stats } = this;
            return this.stats['id'] !== undefined
                ? `${stats['type']} instance ${stats['name']} (${stats['region']})`
                : null;
        }
    }
};
</script>