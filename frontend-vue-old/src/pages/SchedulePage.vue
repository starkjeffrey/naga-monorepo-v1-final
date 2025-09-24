<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('schedule.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('schedule.subtitle') }}
      </p>
    </div>

    <q-card class="q-mb-md">
      <q-card-section class="text-center q-pa-xl">
        <q-icon name="schedule" size="64px" color="orange-6" class="q-mb-md" />
        <h5 class="text-h5 text-weight-medium q-mb-sm">{{ $t('common.inDevelopment') }}</h5>
        <p class="text-body2 text-grey-6">{{ $t('schedule.developmentMessage') }}</p>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
// This page will show class schedule
</script>
