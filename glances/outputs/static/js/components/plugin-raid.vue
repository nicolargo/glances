<template>
    <section class="plugin" id="raid" v-if="hasDisks">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">RAID disks {{ disks.length }}</th>
                    <th scope="col" class="text-end">Used</th>
                    <th scope="col" class="text-end">Total</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(disk, diskId) in disks" :key="diskId">
                    <td scope="row">
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
                    </td>
                    <td scope="row" class="text-end" v-show="disk.status == 'active'" :class="getAlert(disk)">
                        {{ disk.used }}
                    </td>
                    <td scope="row" class="text-end" v-show="disk.status == 'active'" :class="getAlert(disk)">
                        {{ disk.available }}
                    </td>
                </tr>
            </tbody>
        </table>
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