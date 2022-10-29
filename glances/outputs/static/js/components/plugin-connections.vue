<template>
    <section class="plugin" id="connections">
        <div class="table-row">
            <div class="table-cell text-left title">TCP CONNECTIONS</div>
            <div class="table-cell"></div>
        </div>
        <div class="table-row">
            <div class="table-cell text-left">Listen</div>
            <div class="table-cell"></div>
            <div class="table-cell">{{ listen }}</div>
        </div>
        <div class="table-row">
            <div class="table-cell text-left">Initiated</div>
            <div class="table-cell"></div>
            <div class="table-cell">{{ initiated }}</div>
        </div>
        <div class="table-row">
            <div class="table-cell text-left">Established</div>
            <div class="table-cell"></div>
            <div class="table-cell">{{ established }}</div>
        </div>
        <div class="table-row">
            <div class="table-cell text-left">Terminated</div>
            <div class="table-cell"></div>
            <div class="table-cell">{{ terminated }}</div>
        </div>
        <div class="table-row">
            <div class="table-cell text-left">Tracked</div>
            <div class="table-cell"></div>
            <div class="table-cell" :class="getDecoration('nf_conntrack_percent')">
                {{ tracked.count }}/{{ tracked.max }}
            </div>
        </div>
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