<template>
    <section v-if="address" id="ip" class="plugin">
        <span v-if="address" class="title">IP</span>
        <span v-if="address">{{ address }}/{{ maskCdir }}</span>
        <span v-if="publicAddress" class="title">Pub</span>
        <span v-if="publicAddress">{{ publicAddress }}</span>
        <span v-if="publicInfo" class="text-truncate">{{ publicInfo }}</span>
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
        ipStats() {
            return this.data.stats['ip'];
        },
        address() {
            return this.ipStats.address;
        },
        gateway() {
            return this.ipStats.gateway;
        },
        maskCdir() {
            return this.ipStats.mask_cidr;
        },
        publicAddress() {
            return this.ipStats.public_address;
        },
        publicInfo() {
            return this.ipStats.public_info_human;
        }
    }
};
</script>