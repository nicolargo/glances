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
                    <td class="text-end w-25" :class="getDecoration(disk.name, 'write_bytes_rate_per_sec')"
                        v-show="!args.diskio_iops">
                        {{ disk.bitrate.txps }}
                    </td>
                    <td class="text-end w-25" :class="getDecoration(disk.name, 'read_bytes_rate_per_sec')"
                        v-show="!args.diskio_iops">
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
        view() {
            return this.data.views['diskio'];
        },
        disks() {
            const disks = this.stats.map((diskioData) => {
                return {
                    name: diskioData['disk_name'],
                    alias: diskioData['alias'] !== undefined ? diskioData['alias'] : null,
                    bitrate: {
                        txps: bytes(diskioData['read_bytes_rate_per_sec']),
                        rxps: bytes(diskioData['write_bytes_rate_per_sec'])
                    },
                    count: {
                        txps: bytes(diskioData['read_count_rate_per_sec']),
                        rxps: bytes(diskioData['write_count_rate_per_sec'])
                    }
                };
            }).filter(disk => {
              const readBytesRate = this.view[disk.name]['read_bytes_rate_per_sec'];
              const writeBytesRate = this.view[disk.name]['write_bytes_rate_per_sec'];
              return (!readBytesRate || readBytesRate.hidden === false) && (!writeBytesRate || writeBytesRate.hidden === false);
            });
            return orderBy(disks, ['name']);
        },
        hasDisks() {
            return this.disks.length > 0;
        }
    },
    methods: {
        getDecoration(diskName, field) {
            if (this.view[diskName][field] == undefined) {
                return;
            }
            return this.view[diskName][field].decoration.toLowerCase();
        }
    }
};
</script>
