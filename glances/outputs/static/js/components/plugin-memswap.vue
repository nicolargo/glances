<template>
    <section id="memswap" class="plugin">
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left title">SWAP</div>
                <div class="table-cell" :class="getDecoration('percent')">{{ percent }}%</div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">total:</div>
                <div class="table-cell">{{ $filters.bytes(total) }}</div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">used:</div>
                <div class="table-cell" :class="getDecoration('used')">
                    {{ $filters.bytes(used) }}
                </div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">free:</div>
                <div class="table-cell">{{ $filters.bytes(free) }}</div>
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
            return this.data.stats['memswap'];
        },
        view() {
            return this.data.views['memswap'];
        },
        percent() {
            return this.stats['percent'];
        },
        total() {
            return this.stats['total'];
        },
        used() {
            return this.stats['used'];
        },
        free() {
            return this.stats['free'];
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