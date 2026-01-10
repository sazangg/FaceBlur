import { StatusIndicator } from "@/components/status-indicator"
import { Button } from "@/components/ui/button"
import linksData from "@/data/links.json"

import type { QueueStatus, VanityStats } from "@/types"

type Links = {
  name: string
  website: string
  github: string
  linkedin: string
}

type AppFooterProps = {
  stats: VanityStats | null
  statsError: string | null
  queue: QueueStatus | null
  queueError: string | null
  backendHealthy: boolean | null
}

const links = linksData as Links

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" role="img" aria-hidden="true" className="size-4">
    <path
      fill="currentColor"
      d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.757-1.333-1.757-1.09-.745.084-.73.084-.73 1.205.084 1.84 1.236 1.84 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.304-5.466-1.332-5.466-5.93 0-1.31.468-2.382 1.236-3.222-.123-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.3 1.23a11.49 11.49 0 0 1 3.003-.404c1.02.005 2.047.138 3.003.404 2.29-1.552 3.297-1.23 3.297-1.23.653 1.653.241 2.874.118 3.176.77.84 1.235 1.912 1.235 3.222 0 4.61-2.804 5.624-5.475 5.92.43.372.823 1.102.823 2.222 0 1.606-.015 2.898-.015 3.293 0 .32.216.694.825.576C20.565 21.795 24 17.295 24 12.297c0-6.627-5.373-12-12-12"
    />
  </svg>
)

const LinkedInIcon = () => (
  <svg viewBox="0 0 24 24" role="img" aria-hidden="true" className="size-4">
    <path
      fill="currentColor"
      d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452H7.119zM22.225 0H1.771C.792 0 0 .774 0 1.727v20.545C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.273V1.727C24 .774 23.2 0 22.222 0h.003z"
    />
  </svg>
)

const AppFooter = ({
  stats,
  statsError,
  queue,
  queueError,
  backendHealthy,
}: AppFooterProps) => {
  return (
    <footer className="mt-6 w-full border-t text-xs text-muted-foreground">
      <div className="w-full px-6 py-3">
        <div className="flex items-center justify-between gap-4">
          <StatusIndicator
            backendHealthy={backendHealthy}
            stats={stats}
            statsError={statsError}
            queue={queue}
            queueError={queueError}
          />

          <div className="flex items-center justify-center gap-2">
            <span>Made by</span>
            <Button
              variant="link"
              asChild
              className="h-auto p-0 text-xs text-foreground"
            >
              <a href={links.website} target="_blank" rel="noreferrer">
                {links.name}
              </a>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              asChild
              className="h-7 w-7 text-muted-foreground"
            >
              <a href={links.linkedin} target="_blank" rel="noreferrer">
                <LinkedInIcon />
                <span className="sr-only">LinkedIn</span>
              </a>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              asChild
              className="h-7 w-7 text-muted-foreground"
            >
              <a href={links.github} target="_blank" rel="noreferrer">
                <GitHubIcon />
                <span className="sr-only">GitHub</span>
              </a>
            </Button>
          </div>
        </div>
      </div>
    </footer>
  )
}

export { AppFooter }
