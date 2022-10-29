<template>
    <section class="plugin" id="system">
        <span v-if="isDisconnected" class="critical">Disconnected from</span>
        <span class="title">{{ hostname }}</span>
        <span v-if="isLinux" class="hidden-xs hidden-sm">
            ({{ humanReadableName }} / {{ os.name }} {{ os.version }})
        </span>
        <span v-if="!isLinux" class="hidden-xs hidden-sm">
            ({{ os.name }} {{ os.version }} {{ platform }})
        </span>
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
        isLinux() {
            return this.data.isLinux;
        },
        hostname() {
            return this.stats['hostname'];
        },
        platform() {
            return this.stats['platform'];
        },
        os() {
            return {
                name: this.stats['os_name'],
                version: this.stats['os_version']
            };
        },
        humanReadableName() {
            return this.stats['hr_name'];
        },
        isDisconnected() {
            return this.store.status === 'FAILURE';
        }
    }
};
</script>