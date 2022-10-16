<template>
    <section class="plugin" id="ip" v-if="address != undefined">
        <span v-if="address != undefined" class="title">IP</span>
        <span v-if="address != undefined">{{ address }}/{{ maskCdir }}</span>
        <span v-if="publicAddress != undefined" class="title">Pub</span>
        <span v-if="publicAddress != undefined">{{ publicAddress }}</span>
        <span v-if="publicInfo != undefined">{{ publicInfo }}</span>
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
        // mask() {
        //     return this.ipStats.mask;
        // },
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