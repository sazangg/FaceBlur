import { Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useTheme } from "@/hooks/useTheme"

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === "dark"
  const label = isDark ? "Switch to light mode" : "Switch to dark mode"

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={toggleTheme}
          aria-label={label}
          className="h-8 w-8"
        >
          {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

export { ThemeToggle }
