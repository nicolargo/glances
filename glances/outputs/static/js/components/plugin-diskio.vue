<template>
    <section class="plugin" id="diskio" v-if="hasDisks">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">DISK I/O</th>
                    <th scope="col" class="text-end w-25" v-show="!args.diskio_iops">R/s</th>
                    <th scope="col" class="text-end w-25" v-show="!args.diskio_iops">W/s</th>
                    <th scope="col" class="text-end w-25" v-show="args.diskio_iops">IOR/s</th>
                    <th scope="col" class="text-end w-25" v-show="args.diskio_iops">IOW/s</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(disk, diskId) in disks" :key="diskId">
                    <td scope="row">
                        {{ $filters.minSize(disk.alias ? disk.alias : disk.name, 32) }}
                    </td>
                    <td class="text-end w-25" v-show="!args.diskio_iops">
                        {{ disk.bitrate.txps }}
                    </td>
                    <td class="text-end w-25" v-show="!args.diskio_iops">
                        {{ disk.bitrate.rxps }}
                    </td>
                    <td class="text-end w-25" v-show="args.diskio_iops">
                        {{ disk.count.txps }}
                    </td>
                    <td class="text-end w-25" v-show="args.diskio_iops">
                        {{ disk.count.rxps }}
                    </td>
                </tr>
            </tbody>
        </table>
    </section>
</template>

<script>
import { orderBy } from 'lodash';
import { store } from '../store.js';
import { bytes } from '../filters.js';

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
            return this.data.stats['diskio'];
        },
        disks() {
            const disks = this.stats.map((diskioData) => {
                const timeSinceUpdate = diskioData['time_since_update'];
                return {
                    name: diskioData['disk_name'],
                    bitrate: {
                        txps: bytes(diskioData['read_bytes'] / timeSinceUpdate),
                        rxps: bytes(diskioData['write_bytes'] / timeSinceUpdate)
                    },
                    count: {
                        txps: bytes(diskioData['read_count'] / timeSinceUpdate),
                        rxps: bytes(diskioData['write_count'] / timeSinceUpdate)
                    },
                    alias: diskioData['alias'] !== undefined ? diskioData['alias'] : null
                };
            });
            return orderBy(disks, ['name']);
        },
        hasDisks() {
            return this.disks.length > 0;
        }
    }
};
</script>