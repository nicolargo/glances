<template>
    <section class="plugin" id="wifi" v-if="hasHotpots">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">WIFI</th>
                    <th scope="col" class="text-end">dBm</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(hotspot, hotspotId) in hotspots" :key="hotspotId">
                    <td scope="row">{{ $filters.limitTo(hotspot.ssid, 20) }}</td>
                    <td scope="row" class="text-end" :class="getDecoration(hotspot, 'quality_level')">
                        {{ hotspot.quality_level }}
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
            return this.data.stats['wifi'];
        },
        view() {
            return this.data.views['wifi'];
        },
        hotspots() {
            const hotspots = this.stats
                .map((hotspotData) => {
                    if (hotspotData['ssid'] === '') {
                        return;
                    }
                    return {
                        ssid: hotspotData['ssid'],
                        quality_level: hotspotData['quality_level']
                    };
                })
                .filter(Boolean);
            return orderBy(hotspots, ['ssid']);
        },
        hasHotpots() {
            return this.hotspots.length > 0;
        }
    },
    methods: {
        getDecoration(hotpost, field) {
            if (this.view[hotpost.ssid][field] === undefined) {
                return;
            }
            return this.view[hotpost.ssid][field].decoration.toLowerCase();
        }
    }
};
</script>