<template>
    <section class="plugin" id="connections">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">TCP CONNECTIONS</th>
                    <th scope="col" class="text-end"></th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td scope="row">Listen</td>
                    <td class="text-end">{{ listen }}</td>
                </tr>
                <tr>
                    <td scope="row">Initiated</td>
                    <td class="text-end">{{ initiated }}</td>
                </tr>
                <tr>
                    <td scope="row">Established</td>
                    <td class="text-end">{{ established }}</td>
                </tr>
                <tr>
                    <td scope="row">Terminated</td>
                    <td class="text-end">{{ terminated }}</td>
                </tr>
                <tr>
                    <td scope="row">Tracked</td>
                    <td class="text-end" :class="getDecoration('nf_conntrack_percent')">
                        {{ tracked.count }}/{{ tracked.max }}
                    </td>
                </tr>
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
            return this.data.stats['connections'];
        },
        view() {
            return this.data.views['connections'];
        },
        listen() {
            return this.stats['LISTEN'];
        },
        initiated() {
            return this.stats['initiated'];
        },
        established() {
            return this.stats['ESTABLISHED'];
        },
        terminated() {
            return this.stats['terminated'];
        },
        tracked() {
            return {
                count: this.stats['nf_conntrack_count'],
                max: this.stats['nf_conntrack_max']
            };
        }
    },
    methods: {
        getDecoration(value) {
            if (this.view[value] === undefined) {
                return;
            }
            return this.view[value].decoration.toLowerCase();
        }
    }
};
</script>