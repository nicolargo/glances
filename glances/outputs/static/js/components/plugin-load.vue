<template>
    <section id="load" class="plugin" v-if="cpucore != undefined">
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left title">LOAD</div>
                <div class="table-cell">{{ cpucore }}-core</div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">1 min:</div>
                <div class="table-cell">
                    {{ $filters.number(min1, 2) }}
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">5 min:</div>
                <div class="table-cell" :class="getDecoration('min5')">
                    {{ $filters.number(min5, 2) }}
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">15 min:</div>
                <div class="table-cell" :class="getDecoration('min15')">
                    {{ $filters.number(min15, 2) }}
                </div>
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
            return this.data.stats['load'];
        },
        view() {
            return this.data.views['load'];
        },
        cpucore() {
            return this.stats['cpucore'];
        },
        min1() {
            return this.stats['min1'];
        },
        min5() {
            return this.stats['min5'];
        },
        min15() {
            return this.stats['min15'];
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