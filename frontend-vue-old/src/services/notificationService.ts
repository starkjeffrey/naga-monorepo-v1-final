/**
 * Notification Service for Quasar notifications
 * Provides a way to show notifications from stores and other non-component contexts
 */

import { Notify } from 'quasar'

export interface NotificationOptions {
  type?: 'positive' | 'negative' | 'warning' | 'info'
  message: string
  position?:
    | 'top'
    | 'top-left'
    | 'top-right'
    | 'bottom'
    | 'bottom-left'
    | 'bottom-right'
    | 'left'
    | 'right'
    | 'center'
  timeout?: number
  actions?: Array<{
    label: string
    color?: string
    handler?: () => void
  }>
}

export const notificationService = {
  /**
   * Show a notification using Quasar's Notify
   */
  notify(options: NotificationOptions): void {
    Notify.create({
      type: options.type || 'info',
      message: options.message,
      position: options.position || 'top',
      timeout: options.timeout || 5000,
      actions: options.actions,
    })
  },

  /**
   * Show a success notification
   */
  success(message: string, timeout = 3000): void {
    this.notify({
      type: 'positive',
      message,
      timeout,
    })
  },

  /**
   * Show an error notification
   */
  error(message: string, timeout = 5000): void {
    this.notify({
      type: 'negative',
      message,
      timeout,
    })
  },

  /**
   * Show a warning notification
   */
  warning(message: string, timeout = 4000): void {
    this.notify({
      type: 'warning',
      message,
      timeout,
    })
  },

  /**
   * Show an info notification
   */
  info(message: string, timeout = 4000): void {
    this.notify({
      type: 'info',
      message,
      timeout,
    })
  },
}
