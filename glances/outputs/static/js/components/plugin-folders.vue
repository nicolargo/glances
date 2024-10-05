<template>
    <section class="plugin" id="folders" v-if="hasFolders">
        <table class="table table-sm table-borderless margin-bottom">
            <thead>
                <tr>
                    <th scope="col">FOLDERS</th>
                    <th scope="col" class="text-end">Size</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(folder, folderId) in folders" :key="folderId">
                    <td scope="row">
                        {{ folder.path }}
                    </td>
                    <td class="text-end" :class="getDecoration(folder)">
                        <span v-if="folder.errno > 0" class="visible-lg-inline">?</span>
                        {{ $filters.bytes(folder.size) }}
                    </td>
                </tr>
            </tbody>
        </table>
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
            return this.data.stats['folders'];
        },
        folders() {
            return this.stats.map((folderData) => {
                return {
                    path: folderData['path'],
                    size: folderData['size'],
                    errno: folderData['errno'],
                    careful: folderData['careful'],
                    warning: folderData['warning'],
                    critical: folderData['critical']
                };
            });
        },
        hasFolders() {
            return this.folders.length > 0;
        }
    },
    methods: {
        getDecoration(folder) {
            if (folder.errno > 0) {
                return 'error';
            }
            if (folder.critical !== null && folder.size > folder.critical * 1000000) {
                return 'critical';
            } else if (folder.warning !== null && folder.size > folder.warning * 1000000) {
                return 'warning';
            } else if (folder.careful !== null && folder.size > folder.careful * 1000000) {
                return 'careful';
            }
            return 'ok';
        }
    }
};
</script>