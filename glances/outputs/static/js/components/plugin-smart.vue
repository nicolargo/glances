<template>
    <section id="smart" class="plugin">
        <div class="table-row">
            <div class="table-cell text-left title">SMART disks</div>
            <div class="table-cell"></div>
            <div class="table-cell"></div>
        </div>
        <template v-for="(drive, driveId) in drives" :key="driveId">
            <div class="table-row">
                <div class="table-cell text-left text-truncate">{{ drive.name }}</div>
                <div class="table-cell"></div>
                <div class="table-cell"></div>
            </div>
            <template v-for="(metric, metricId) in drive.details" :key="metricId">
                <div class="table-row">
                    <div class="table-cell text-left">&nbsp;&nbsp;{{ metric.name }}</div>
                    <div class="table-cell"></div>
                    <div class="table-cell text-truncate">
                        <span>{{ metric.raw }}</span>
                    </div>
                </div>
            </template>
        </template>
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
        stats() {
            return this.data.stats['smart'];
        },
        drives() {
            return (Array.isArray(this.stats) ? this.stats : []).map((data) => {
                const name = data.DeviceName;
                const details = Object.entries(data)
                    .filter(([key]) => key !== 'DeviceName')
                    .sort(([, a], [, b]) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
                    .map(([prop, value]) => value);
                return { name, details };
            });
        }
    }
};
</script>
