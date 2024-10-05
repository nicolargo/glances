<template>
    <section id="mem" class="plugin">
        <!-- d-none d-xxl-block -->
        <div class="table-responsive">
            <table class="table-sm table-borderless">
                <tbody>
                    <tr class="justify-content-between">
                        <td scope="col">
                            <table class="table table-sm table-borderless">
                                <tbody>
                                    <tr>
                                        <th scope="col">MEM</th>
                                        <td scope="col" class="text-end" :class="getDecoration('percent')">{{ percent }}%</td>
                                    </tr>
                                    <tr>
                                        <td scope="row">total:</td>
                                        <td class="text-end">{{ $filters.bytes(total) }}</td>
                                    </tr>
                                    <tr>
                                        <td scope="row">used:</td>
                                        <td class="text-end" :class="getDecoration('used')">{{ $filters.bytes(used, 2) }}</td>
                                    </tr>
                                    <tr>
                                        <td scope="row">free:</td>
                                        <td class="text-end" :class="getDecoration('free')">{{ $filters.bytes(free, 2) }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                        <td>
                            <template class="d-none d-xl-block d-xxl-block">
                                <table class="table table-sm table-borderless">
                                    <tbody>
                                        <tr>
                                            <td scope="col" v-show="active != undefined">
                                                active:
                                            </td>
                                            <td scope="col" v-show="active != undefined">
                                                {{ $filters.bytes(active) }}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="inactive != undefined">
                                                inactive:
                                            </td>
                                            <td scope="col" v-show="inactive != undefined">
                                                {{ $filters.bytes(inactive) }}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="buffers != undefined">
                                                buffers:
                                            </td>
                                            <td scope="col" v-show="buffers != undefined">
                                                {{ $filters.bytes(buffers) }}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td scope="col" v-show="cached != undefined">
                                                cached:
                                            </td>
                                            <td scope="col" v-show="cached != undefined">
                                                {{ $filters.bytes(cached) }}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </template>
                        </td>
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