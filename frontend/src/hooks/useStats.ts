import { useEffect, useState } from "react"

import { apiFetch } from "@/lib/api"
import type { VanityStats } from "@/types"

const useStats = () => {
  const [stats, setStats] = useState<VanityStats | null>(null)
  const [statsError, setStatsError] = useState<string | null>(null)

  const refreshIntervalMs = Math.max(
    3000,
    Number(import.meta.env.VITE_STATS_REFRESH_MS ?? 15000)
  )

  useEffect(() => {
    let cancelled = false

    const fetchStats = async () => {
      try {
        const response = await apiFetch("/stats")
        if (cancelled) return
        if (!response.ok) {
          setStatsError("Stats unavailable")
          return
        }
        const payload = (await response.json()) as {
          data?: VanityStats
        }
        if (payload.data) {
          setStats(payload.data)
          setStatsError(null)
        }
      } catch {
        if (!cancelled) {
          setStatsError("Stats unavailable")
        }
      }
    }

    void fetchStats()
    const intervalId = window.setInterval(fetchStats, refreshIntervalMs)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [refreshIntervalMs])

  return { stats, statsError }
}

export { useStats }
