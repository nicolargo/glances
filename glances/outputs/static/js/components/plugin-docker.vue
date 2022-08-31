<template>
    <section id="containers-plugin" class="plugin" v-if="containers.length">
        <span class="title">CONTAINERS</span>
        {{ containers.length }} (served by Docker {{ version }})
        <div class="table">
            <div class="table-row">
                <div class="table-cell text-left">Name</div>
                <div class="table-cell">Status</div>
                <div class="table-cell">Uptime</div>
                <div class="table-cell">CPU%</div>
                <div class="table-cell">MEM</div>
                <div class="table-cell">RSS</div>
                <div class="table-cell">IOR/s</div>
                <div class="table-cell">IOW/s</div>
                <div class="table-cell">RX/s</div>
                <div class="table-cell">TX/s</div>
                <div class="table-cell text-left">Command</div>
            </div>
            <div
                class="table-row"
                v-for="(container, containerId) in containers"
                :key="containerId"
            >
                <div class="table-cell text-left">{{ container.name }}</div>
                <div class="table-cell" :class="container.status == 'Paused' ? 'careful' : 'ok'">
                    {{ container.status }}
                </div>
                <div class="table-cell" :class="container.status == 'Paused' ? 'careful' : 'ok'">
                    {{ container.uptime }}
                </div>
                <div class="table-cell">
                    {{ $filters.number(container.cpu, 1) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bytes(container.memory) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bytes(container.rss) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.ior / container.io_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.iow / container.io_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.rx / container.net_time_since_update) }}
                </div>
                <div class="table-cell">
                    {{ $filters.bits(container.tx / container.net_time_since_update) }}
                </div>
                <div class="table-cell text-left">
                    {{ container.command }}
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
            return this.data.stats['docker'];
        },
        containers() {
            return (this.stats.containers || []).map((containerData) => {
                // prettier-ignore
                return {
                    'id': containerData.Id,
                    'name': containerData.name,
                    'status': containerData.Status,
                    'uptime': containerData.Uptime,
                    'cpu': containerData.cpu.total,
                    'memory': containerData.memory.usage != undefined ? containerData.memory.usage : '?',
                    'rss': containerData.memory.rss != undefined ? containerData.memory.rss : '?',
                    'ior': containerData.io.ior != undefined ? containerData.io.ior : '?',
                    'iow': containerData.io.iow != undefined ? containerData.io.iow : '?',
                    'io_time_since_update': containerData.io.time_since_update,
                    'rx': containerData.network.rx != undefined ? containerData.network.rx : '?',
                    'tx': containerData.network.tx != undefined ? containerData.network.tx : '?',
                    'net_time_since_update': containerData.network.time_since_update,
                    'command': containerData.Command,
                    'image': containerData.Image
            };
            });
        },
        version() {
            return (this.stats['version'] || {})['Version'];
        }
    }
};
</script>