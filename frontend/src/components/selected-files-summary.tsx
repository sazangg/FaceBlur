import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

type SelectedFilesSummaryProps = {
  files: File[]
  maxVisible?: number
}

const SelectedFilesSummary = ({
  files,
  maxVisible = 3,
}: SelectedFilesSummaryProps) => {
  if (!files.length) {
    return (
      <span className="self-start text-sm text-muted-foreground">
        No files selected
      </span>
    )
  }

  if (files.length <= maxVisible) {
    return (
      <span className="self-start text-sm text-muted-foreground">
        {files.map((file) => file.name).join(", ")}
      </span>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="self-start cursor-help text-sm text-muted-foreground">
          {files.length} files selected
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        align="start"
        sideOffset={8}
        className="w-max max-w-[80vw]"
      >
        <div className="max-h-48 space-y-1 overflow-auto text-xs">
          {files.map((file) => (
            <div
              key={`${file.name}-${file.size}-${file.lastModified}`}
              className="whitespace-nowrap"
            >
              {file.name}
            </div>
          ))}
        </div>
      </TooltipContent>
    </Tooltip>
  )
}

export { SelectedFilesSummary }
