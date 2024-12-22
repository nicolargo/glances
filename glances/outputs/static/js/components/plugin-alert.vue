<template>
  <section class="plugin" id="alerts">
    <span class="title" v-if="hasAlerts">
      Warning or critical alerts (last {{ countAlerts }} entries)
      <span>
        <button class="clear-button" v-on:click="clear()">Clear alerts</button>
      </span>
    </span>
    <span class="title" v-else>No warning or critical alert detected</span>
    <table class="table table-sm table-borderless">
      <tbody>
        <tr v-for="(alert, alertId) in alerts" :key="alertId">
          <td scope="row">
            <span>{{ formatDate(alert.begin) }}</span>
          </td>
          <td scope="row">
            <span>({{ alert.ongoing ? 'ongoing' : alert.duration }})</span>
          </td>
          <td scope="row">
            <span v-show="!alert.ongoing"> {{ alert.state }} on </span>
            <span :class="alert.state.toLowerCase()">{{ alert.type }}</span>
            <span>({{ $filters.number(alert.max, 1) }})</span>
            <span>: {{ alert.top }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script>
import { padStart } from 'lodash';
import { GlancesFavico } from '../services.js';

export default {
  props: {
    data: {
      type: Object
    }
  },
  computed: {
    stats() {
      return this.data.stats['alert'];
    },
    alerts() {
      return (this.stats || []).map((alertStats) => {
        const alert = {};
        alert.state = alertStats.state;
        alert.type = alertStats.type;
        alert.begin = alertStats.begin * 1000;
        alert.end = alertStats.end * 1000;
        alert.ongoing = alertStats.end == -1;
        alert.min = alertStats.min;
        alert.avg = alertStats.avg;
        alert.max = alertStats.max;
        alert.top = alertStats.top.join(', ');

        if (!alert.ongoing) {
          const duration = alert.end - alert.begin;
          const seconds = parseInt((duration / 1000) % 60),
            minutes = parseInt((duration / (1000 * 60)) % 60),
            hours = parseInt((duration / (1000 * 60 * 60)) % 24);

          alert.duration = padStart(hours, 2, '0') +
            ':' + padStart(minutes, 2, '0') +
            ':' + padStart(seconds, 2, '0');
        }

        return alert;
      });
    },
    hasAlerts() {
      return this.countAlerts > 0;
    },
    countAlerts() {
      return this.alerts.length;
    },
    hasOngoingAlerts() {
      return this.countOngoingAlerts > 0;
    },
    countOngoingAlerts() {
      return this.alerts.filter(({ ongoing }) => ongoing).length;
    }
  },
  watch: {
    countOngoingAlerts() {
      if (this.countOngoingAlerts) {
        GlancesFavico.badge(this.countOngoingAlerts);
      } else {
        GlancesFavico.reset();
      }
    }
  },
  methods: {
    formatDate(timestamp) {
      const tzOffset = new Date().getTimezoneOffset();
      const hours = Math.trunc(Math.abs(tzOffset) / 60);
      const minutes = Math.abs(tzOffset % 60);

      let tzString = tzOffset <= 0 ? '+' : '-';
      tzString += String(hours).padStart(2, '0') + String(minutes).padStart(2, '0');

      const date = new Date(timestamp);
      return String(date.getFullYear()) +
        '-' + String(date.getMonth() + 1).padStart(2, '0') +
        '-' + String(date.getDate()).padStart(2, '0') +
        ' ' + String(date.getHours()).padStart(2, '0') +
        ':' + String(date.getMinutes()).padStart(2, '0') +
        ':' + String(date.getSeconds()).padStart(2, '0') +
        '(' + tzString + ')';
    },
    clear() {
      const requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      };
      fetch('api/4/events/clear/all', requestOptions)
        .then(response => response.json())
        .then(data => product.value = data);
    }
  }
};
</script>