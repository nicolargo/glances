<template>
    <section class="plugin" id="diskio">
        <div class="table-row" v-if="disks.length > 0">
            <div class="table-cell text-left title">DISK I/O</div>
            <div class="table-cell" v-show="!args.diskio_iops">R/s</div>
            <div class="table-cell" v-show="!args.diskio_iops">W/s</div>
            <div class="table-cell" v-show="args.diskio_iops">IOR/s</div>
            <div class="table-cell" v-show="args.diskio_iops">IOW/s</div>
        </div>
        <div class="table-row" v-for="(disk, diskId) in disks" :key="diskId">
            <div class="table-cell text-left">
                {{ $filters.minSize(disk.alias ? disk.alias : disk.name, 32) }}
            </div>
            <div class="table-cell" v-show="!args.diskio_iops">
                {{ disk.bitrate.txps }}
            </div>
            <div class="table-cell" v-show="!args.diskio_iops">
                {{ disk.bitrate.rxps }}
            </div>
            <div class="table-cell" v-show="args.diskio_iops">
                {{ disk.count.txps }}
            </div>
            <div class="table-cell" v-show="args.diskio_iops">
                {{ disk.count.rxps }}
            </div>
        </div>
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
        }
    }
};
</script>