<template>
    <section id="memswap" class="plugin">
        <div class="table-responsive">
            <table class="table table-sm table-borderless">
                <thead>
                    <tr>
                        <th scope="col">SWAP</th>
                        <td scope="col" class="text-end" :class="getDecoration('percent')"><span>{{ percent }}%</span>
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td scope="row">total:</td>
                        <td class="text-end"><span>{{ $filters.bytes(total) }}</span></td>
                    </tr>
                    <tr>
                        <td scope="row">used:</td>
                        <td class="text-end" :class="getDecoration('used')"><span>{{ $filters.bytes(used, 2) }}</span>
                        </td>
                    </tr>
                    <tr>
                        <td scope="row">free:</td>
                        <td class="text-end"><span>{{ $filters.bytes(free, 2) }}</span></td>
                    </tr>
                </tbody>
            </table>
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