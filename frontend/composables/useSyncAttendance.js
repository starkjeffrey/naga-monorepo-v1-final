import { apiFetch } from '../utils/api.js'

export async function syncAttendanceQueue() {
  if (!navigator.onLine) return

  const queue = JSON.parse(localStorage.getItem('attendanceQueue') || '[]')
  const remaining = []

  for (const entry of queue) {
    try {
      await apiFetch('/api/student/checkin/', {
        method: 'POST',
        body: JSON.stringify(entry),
      })
    } catch {
      remaining.push(entry)
    }
  }

  localStorage.setItem('attendanceQueue', JSON.stringify(remaining))
}
