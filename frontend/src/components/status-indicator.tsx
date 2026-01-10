import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { VanityStats } from "@/types"

type StatusIndicatorProps = {
  backendHealthy: boolean | null
  stats?: VanityStats | null
  statsError?: string | null
}

const MIN_COUNTER_WIDTH = 6

const formatCounter = (value: number, width: number) => {
  const normalized = Math.max(0, Math.floor(value))
  return normalized.toString().padStart(width, "0")
}

const StatusIndicator = ({
  backendHealthy,
  stats,
  statsError,
}: StatusIndicatorProps) => {
  const statusLabel =
    backendHealthy === true
      ? "Service running"
      : backendHealthy === false
        ? "Service unavailable"
        : "Checking service status"
  const statusText =
    backendHealthy === true
      ? "Service online"
      : backendHealthy === false
        ? "Service offline"
        : "Checking"
  const dotClass =
    backendHealthy === true
      ? "bg-emerald-500"
      : backendHealthy === false
        ? "bg-red-500"
        : "bg-muted-foreground"

  const counterWidth = stats
    ? Math.max(
        MIN_COUNTER_WIDTH,
        (stats.total_visitors ?? 0).toString().length,
        (stats.total_images ?? 0).toString().length,
        (stats.total_requests ?? 0).toString().length,
        (stats.total_videos ?? 0).toString().length,
        (stats.total_video_seconds ?? 0).toString().length
      )
    : MIN_COUNTER_WIDTH

  const tooltipContent = stats ? (
    <div className="space-y-2 text-xs">
      <div className="text-muted-foreground">Stats</div>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-6">
          <span>Visitors</span>
          <span className="font-mono tabular-nums">
            {formatCounter(stats.total_visitors ?? 0, counterWidth)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span>Images blurred</span>
          <span className="font-mono tabular-nums">
            {formatCounter(stats.total_images ?? 0, counterWidth)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span>Blur requests</span>
          <span className="font-mono tabular-nums">
            {formatCounter(stats.total_requests ?? 0, counterWidth)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span>Videos blurred</span>
          <span className="font-mono tabular-nums">
            {formatCounter(stats.total_videos ?? 0, counterWidth)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-6">
          <span>Video seconds</span>
          <span className="font-mono tabular-nums">
            {formatCounter(stats.total_video_seconds ?? 0, counterWidth)}
          </span>
        </div>
      </div>
    </div>
  ) : (
    <div className="text-xs">
      {statsError ? statsError : "Stats loading..."}
    </div>
  )

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline" className="gap-2 px-3 py-1">
          <span
            className={`size-2.5 rounded-full ${dotClass}`}
            aria-label={statusLabel}
          />
          <span className="text-xs">{statusText}</span>
        </Badge>
      </TooltipTrigger>
      <TooltipContent align="start" className="w-56">
        {tooltipContent}
      </TooltipContent>
    </Tooltip>
  )
}

export { StatusIndicator }
