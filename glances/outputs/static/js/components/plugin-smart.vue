<template>
    <section id="smart" class="plugin" v-if="hasDrives">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">SMART DISKS</th>
                    <th scope="col" class="text-end"></th>
                </tr>
            </thead>
            <tbody>
                <template v-for="(drive, driveId) in drives" :key="driveId">
                    <tr>
                        <td scope="row">{{ drive.name }}</td>
                        <td scope="col" class="text-end"></td>
                    </tr>
                    <tr v-for="(metric, metricId) in drive.details" :key="metricId">
                        <td scope="row">{{ metric.name }}</td>
                        <td scope="row" class="text-end text-truncate">{{ metric.raw }}</td>
                    </tr>
                </template>
            </tbody>
        </table>
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
        },
        hasDrives() {
            return this.drives.length > 0;
        }
    }
};
</script>
