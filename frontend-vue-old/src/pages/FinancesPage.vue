<template>
  <q-page class="q-pa-md">
    <div class="q-mb-lg">
      <h4 class="text-h4 q-mb-xs text-weight-medium">
        {{ $t('finances.title') }}
      </h4>
      <p class="text-subtitle1 text-grey-6">
        {{ $t('finances.subtitle') }}
      </p>
    </div>

    <q-card class="q-mb-md">
      <q-card-section class="text-center q-pa-xl">
        <q-icon name="account_balance_wallet" size="64px" color="teal-6" class="q-mb-md" />
        <h5 class="text-h5 text-weight-medium q-mb-sm">{{ $t('common.inDevelopment') }}</h5>
        <p class="text-body2 text-grey-6">{{ $t('finances.developmentMessage') }}</p>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
// This page will show financial balance and payment history
</script>
