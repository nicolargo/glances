<template>
    <section class="plugin" id="wifi">
        <div class="table-row" v-if="hotspots.length > 0">
            <div class="table-cell text-left title">WIFI</div>
            <div class="table-cell"></div>
            <div class="table-cell">dBm</div>
        </div>
        <div class="table-row" v-for="(hotspot, hotspotId) in hotspots" :key="hotspotId">
            <div class="table-cell text-left">
                {{ $filters.limitTo(hotspot.ssid, 20) }}
                <span v-if="hotspot.encrypted">
                    {{ hotspot.encryption_type }}
                </span>
            </div>
            <div class="table-cell"></div>
            <div class="table-cell" :class="getDecoration(hotspot, 'signal')">
                {{ hotspot.signal }}
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
                        encrypted: hotspotData['encrypted'],
                        signal: hotspotData['signal'],
                        encryption_type: hotspotData['encryption_type']
                    };
                })
                .filter(Boolean);
            return orderBy(hotspots, ['ssid']);
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