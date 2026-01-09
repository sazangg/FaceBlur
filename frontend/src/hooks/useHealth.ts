import { useEffect, useRef, useState } from "react"

import { apiFetch } from "@/lib/api"

const useHealth = () => {
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null)
  const hasFetched = useRef(false)

  useEffect(() => {
    if (hasFetched.current) return
    hasFetched.current = true
    void (async () => {
      try {
        const response = await apiFetch("/health")
        setBackendHealthy(response.ok)
      } catch {
        setBackendHealthy(false)
      }
    })()
  }, [])

  return backendHealthy
}

export { useHealth }
