<template>
    <section class="plugin" id="fs" v-if="hasFs">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">FILE SYSTEM</th>
                    <template v-if="!args.fs_free_space">
                        <th scope="col" class="text-end w-25">Used</th>
                    </template>
                    <template v-else>
                        <th scope="col" class="text-end w-25">Free</th>
                    </template>
                    <th scope="col" class="text-end w-25">Total</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(fs, fsId) in fileSystems" :key="fsId">
                    <td scope="row">
                        {{ $filters.minSize(fs.alias ? fs.alias : fs.mountPoint, 26, begin=false) }}
                        <span v-if="(fs.alias ? fs.alias : fs.mountPoint).length + fs.name.length <= 24" class="visible-lg-inline">
                            ({{ fs.name }})
                        </span>
                    </td>
                    <template v-if="!args.fs_free_space">
                        <td scope="row" class="text-end" :class="getDecoration(fs.mountPoint, 'used')">
                            {{ $filters.bytes(fs.used) }}
                        </td>
                    </template>
                    <template v-else>
                        <td scope="row" class="text-end" :class="getDecoration(fs.mountPoint, 'used')">
                            {{ $filters.bytes(fs.free) }}
                        </td>
                    </template>
                    <td scope="row" class="text-end">
                        {{ $filters.bytes(fs.size) }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
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
        args() {
            return this.store.args || {};
        },
        stats() {
            return this.data.stats['fs'];
        },
        view() {
            return this.data.views['fs'];
        },
        fileSystems() {
            const fileSystems = this.stats.map((fsData) => {
                return {
                    name: fsData['device_name'],
                    mountPoint: fsData['mnt_point'],
                    percent: fsData['percent'],
                    size: fsData['size'],
                    used: fsData['used'],
                    free: fsData['free'],
                    alias: fsData['alias'] !== undefined ? fsData['alias'] : null
                };
            });
            return orderBy(fileSystems, ['mnt_point']);
        },
        hasFs() {
            return this.fileSystems.length > 0;
        }
    },
    methods: {
        getDecoration(mountPoint, field) {
            if (this.view[mountPoint][field] == undefined) {
                return;
            }
            return this.view[mountPoint][field].decoration.toLowerCase();
        }
    }
};
</script>