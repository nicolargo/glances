<template>
    <section id="system" class="plugin">
        <span v-if="isDisconnected" class="critical">Disconnected from</span>
        <span class="title">{{ hostname }}</span>
    </section>
</template>

<script>
import { store } from '../store.js';

export default {
    props: {
        data: {
            type: Object
        }
    },
    data() {
        return {
            store
        };
    },
    computed: {
        stats() {
            return this.data.stats['system'];
        },
        hostname() {
            return this.stats['hostname'];
        },
        isDisconnected() {
            return this.store.status === 'FAILURE';
        }
    }
};
</script>