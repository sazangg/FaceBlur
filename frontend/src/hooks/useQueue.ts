import { useEffect, useState } from "react"

import { apiFetch } from "@/lib/api"
import type { QueueStatus } from "@/types"

const useQueue = () => {
  const [queue, setQueue] = useState<QueueStatus | null>(null)
  const [queueError, setQueueError] = useState<string | null>(null)

  const refreshIntervalMs = Math.max(
    3000,
    Number(import.meta.env.VITE_STATS_REFRESH_MS ?? 15000)
  )

  useEffect(() => {
    let cancelled = false

    const fetchQueue = async () => {
      try {
        const response = await apiFetch("/queue")
        if (cancelled) return
        if (!response.ok) {
          setQueueError("Queue unavailable")
          return
        }
        const payload = (await response.json()) as {
          data?: QueueStatus
        }
        if (payload.data) {
          if (payload.data.available === false) {
            setQueue(null)
            setQueueError(payload.data.error || "Queue unavailable")
          } else {
            setQueue(payload.data)
            setQueueError(null)
          }
        }
      } catch {
        if (!cancelled) {
          setQueueError("Queue unavailable")
        }
      }
    }

    void fetchQueue()
    const intervalId = window.setInterval(fetchQueue, refreshIntervalMs)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [refreshIntervalMs])

  return { queue, queueError }
}

export { useQueue }
