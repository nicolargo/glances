<template>
  <!-- If the plugin is disabled in the args, show a message -->
  <div v-if="args.disable_tailer">
    TAILER DISABLED (press the corresponding key or remove --disable-tailer to enable)
  </div>
  <!-- Otherwise, display the plugin content -->
  <div v-else>
    <h2>Tailer Plugin</h2>

    <!-- If no data available, show a fallback message -->
    <div v-if="!tailerStats">
      <i>No tailer data available.</i>
    </div>

    <!-- Otherwise, display tailer information -->
    <div v-else>
      <div>
        <strong>File Name:</strong> {{ tailerStats.filename }}
      </div>
      <div>
        <strong>Last Modified:</strong> {{ tailerStats.last_modified }}
      </div>
      <div>
        <strong>Total Line Count:</strong> {{ tailerStats.line_count }}
      </div>
      <div>
        <strong>File Size (bytes):</strong> {{ tailerStats.file_size }}
      </div>

      <!-- Display last lines -->
      <div class="mt-2">
        <strong>Last {{ tailerStats.last_lines?.length }} lines:</strong>
        <div v-for="(line, i) in tailerStats.last_lines" :key="i" class="ml-2">
          {{ line }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { store } from '../store.js'; // Path to your store.js

export default {
  name: 'GlancesPluginTailer',
  props: {
    // 'data' will be the entire Glances JSON data object (like in other plugins).
    // Typically something like: { tailer: [ { filename, file_size, last_modified, ... } ], cpu: [...], mem: [...] }
    data: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      store
    };
  },
  computed: {
    // Access global arguments from store (like disable_tailer, etc.)
    args() {
      return this.store.args || {};
    },

    // Return the plugin data object from the global data
    // Typically, your Python plugin returns a list in self.stats,
    // so `this.data.tailer` may be an array of stats.
    // We'll grab the first item for display if it exists.
    tailerStats() {
      if (!this.data.tailer || !this.data.tailer.length) {
        return null;
      }
      // By default, we'll show just the first dictionary in the tailer array
      // If your plugin returns multiple items, you can adapt to show them all.
      return this.data.tailer[0];
    }
  }
};
</script>

<style scoped>
/* Example styling; adapt as you wish */
.mt-2 {
  margin-top: 0.5rem;
}
.ml-2 {
  margin-left: 0.5rem;
}
</style>
