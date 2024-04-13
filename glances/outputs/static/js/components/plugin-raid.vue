<template>
    <section class="plugin" id="raid">
        <div class="table-row" v-if="hasDisks">
            <div class="table-cell text-left title">RAID disks</div>
            <div class="table-cell">Used</div>
            <div class="table-cell">Total</div>
        </div>
        <div class="table-row" v-for="(disk, diskId) in disks" :key="diskId">
            <div class="table-cell text-left">
                {{ disk.type.toUpperCase() }} {{ disk.name }}
                <div class="warning" v-show="disk.degraded">└─ Degraded mode</div>
                <div v-show="disk.degraded">&nbsp; &nbsp;└─ {{ disk.config }}</div>
                <div class="critical" v-show="disk.inactive">└─ Status {{ disk.status }}</div>
                <template v-if="disk.inactive">
                    <div v-for="(component, componentId) in disk.components" :key="componentId">
                        &nbsp; &nbsp;{{
                            componentId === disk.components.length - 1 ? '└─' : '├─'
                        }}
                        disk {{ component.number }}: {{ component.name }}
                    </div>
                </template>
            </div>
            <div class="table-cell" v-show="disk.status == 'active'" :class="getAlert(disk)">
                {{ disk.used }}
            </div>
            <div class="table-cell" v-show="disk.status == 'active'" :class="getAlert(disk)">
                {{ disk.available }}
            </div>
        </div>
    </section>
</template>

<script>
import { orderBy } from 'lodash';

export default {
    props: {
        data: {
            type: Object
        }
    },
    computed: {
        stats() {
            return this.data.stats['raid'];
        },
        disks() {
            const disks = Object.entries(this.stats).map(([diskKey, diskData]) => {
                const components = Object.entries(diskData.components).map(([name, number]) => {
                    return {
                        number: number,
                        name: name
                    };
                });
                return {
                    name: diskKey,
                    type: diskData.type == null ? 'UNKNOWN' : diskData.type,
                    used: diskData.used,
                    available: diskData.available,
                    status: diskData.status,
                    degraded: diskData.used < diskData.available,
                    config: diskData.config == null ? '' : diskData.config.replace('_', 'A'),
                    inactive: diskData.status == 'inactive',
                    components: orderBy(components, ['number'])
                };
            });
            return orderBy(disks, ['name']);
        },
        hasDisks() {
            return this.disks.length > 0;
        }
    },
    methods: {
        getAlert(disk) {
            if (disk.inactive) {
                return 'critical';
            }
            if (disk.degraded) {
                return 'warning';
            }
            return 'ok';
        }
    }
};
</script>