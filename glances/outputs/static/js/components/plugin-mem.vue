<template>
    <section id="mem" class="plugin">
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left title">MEM</div>
                <div class="table-cell" :class="getDecoration('percent')">{{ percent }}%</div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">total:</div>
                <div class="table-cell">{{ $filters.bytes(total) }}</div>
            </div>
            <div class="table-row">
                <div class="table-cell text-left">used:</div>
                <div class="table-cell" :class="getDecoration('used')">
                    {{ $filters.bytes(used, 2) }}
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
            return this.data.stats['mem'];
        },
        view() {
            return this.data.views['mem'];
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