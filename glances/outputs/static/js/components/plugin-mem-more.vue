<template>
    <section id="mem-more" class="plugin">
        <div class="table">
            <div class="table-row" v-show="active != undefined">
                <div class="table-cell text-left">active:</div>
                <div class="table-cell">{{ $filters.bytes(active) }}</div>
            </div>
            <div class="table-row" v-show="inactive != undefined">
                <div class="table-cell text-left">inactive:</div>
                <div class="table-cell">{{ $filters.bytes(inactive) }}</div>
            </div>
            <div class="table-row" v-show="buffers != undefined">
                <div class="table-cell text-left">buffers:</div>
                <div class="table-cell">{{ $filters.bytes(buffers) }}</div>
            </div>
            <div class="table-row" v-show="cached != undefined">
                <div class="table-cell text-left">cached:</div>
                <div class="table-cell">{{ $filters.bytes(cached) }}</div>
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
        active() {
            return this.stats['active'];
        },
        inactive() {
            return this.stats['inactive'];
        },
        buffers() {
            return this.stats['buffers'];
        },
        cached() {
            return this.stats['cached'];
        }
    }
};
</script>