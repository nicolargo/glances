<template>
    <section v-if="cpucore != undefined" id="load" class="plugin">
        <div class="table-responsive">
            <table class="table table-sm table-borderless">
                <thead>
                    <tr>
                        <th scope="col">LOAD</th>
                        <td scope="col" class="text-end">{{ cpucore }}-core</td>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td scope="row">1 min:</td>
                        <td class="text-end"><span>{{ $filters.number(min1, 2) }}</span></td>
                    </tr>
                    <tr>
                        <td scope="row">5 min:</td>
                        <td class="text-end" :class="getDecoration('min5')"><span>{{ $filters.number(min5, 2) }}</span>
                        </td>
                    </tr>
                    <tr>
                        <td scope="row">15 min:</td>
                        <td class="text-end" :class="getDecoration('min15')"><span>{{ $filters.number(min15, 2)
                                }}</span></td>
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