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
                                        <td scope="col" class="text-end" :class="getDecoration('percent')"><span>{{
                                            percent }}%</span></td>
                                    </tr>
                                    <tr>
                                        <td scope="row">total:</td>
                                        <td class="text-end"><span>{{ $filters.bytes(total) }}</span></td>
                                    </tr>
                                    <tr>
                                        <td scope="row">used:</td>
                                        <td class="text-end" :class="getDecoration('used')"><span>{{
                                            $filters.bytes(used, 2) }}</span></td>
                                    </tr>
                                    <tr>
                                        <td scope="row">free:</td>
                                        <td class="text-end" :class="getDecoration('free')"><span>{{
                                            $filters.bytes(free, 2) }}</span></td>
                                    </tr>
                                </tbody>
                            </table>
                        </td>
                        <td>
                            <template class="d-none d-xl-block d-xxl-block">
                                <table class="table table-sm table-borderless">
                                    <tbody>
                                        <tr>
                                            <td v-show="active != undefined" scope="col">
                                                active:
                                            </td>
                                            <td v-show="active != undefined" scope="col">
                                                <span>{{ $filters.bytes(active) }}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td v-show="inactive != undefined" scope="col">
                                                inactive:
                                            </td>
                                            <td v-show="inactive != undefined" scope="col">
                                                <span>{{ $filters.bytes(inactive) }}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td v-show="buffers != undefined" scope="col">
                                                buffers:
                                            </td>
                                            <td v-show="buffers != undefined" scope="col">
                                                <span>{{ $filters.bytes(buffers) }}</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td v-show="cached != undefined" scope="col">
                                                cached:
                                            </td>
                                            <td v-show="cached != undefined" scope="col">
                                                <span>{{ $filters.bytes(cached) }}</span>
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