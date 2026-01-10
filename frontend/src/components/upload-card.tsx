import { type DragEvent, type RefObject, useState } from "react"
import { Loader2, X } from "lucide-react"

import { SelectedFilesSummary } from "@/components/selected-files-summary"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import type { Status } from "@/types"

type UploadCardProps = {
  files: File[]
  status: Status
  statusMessage: string
  isBusy: boolean
  fileInputRef: RefObject<HTMLInputElement | null>
  maxFiles: number
  maxUploadMb: number
  maxVideoMb: number
  allowedExtensions: string[]
  allowedVideoExtensions: string[]
  acceptExtensions: string
  selectionError: string | null
  onFilesSelected: (files: FileList | File[]) => void
  onStart: () => void
  onReset: () => void
}

const UploadCard = ({
  files,
  status,
  statusMessage,
  isBusy,
  fileInputRef,
  maxFiles,
  maxUploadMb,
  maxVideoMb,
  allowedExtensions,
  allowedVideoExtensions,
  acceptExtensions,
  selectionError,
  onFilesSelected,
  onStart,
  onReset,
}: UploadCardProps) => {
  const [isDragging, setIsDragging] = useState(false)

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    if (isBusy) return
    if (event.dataTransfer.files?.length) {
      onFilesSelected(event.dataTransfer.files)
    }
  }

  return (
    <Card
      className={`border-dashed ${isDragging ? "bg-muted/30" : ""}`}
      onDragOver={(event) => {
        event.preventDefault()
        if (isBusy) return
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <CardHeader>
        <CardTitle>Upload media</CardTitle>
        <CardDescription>
          Drag and drop or select images or a single video.
          <span className="block text-xs text-muted-foreground">
            Up to {maxFiles} images, {maxUploadMb} MB each, or 1 video up to{" "}
            {maxVideoMb} MB. Accepted images: {allowedExtensions.join(", ")}.
            {allowedVideoExtensions.length > 0 && (
              <> Videos: {allowedVideoExtensions.join(", ")}.</>
            )}
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="relative">
          <Input
            ref={fileInputRef}
            type="file"
            accept={acceptExtensions}
            multiple
            disabled={isBusy}
            className="pr-10"
            onChange={(event) => {
              if (event.target.files) {
                onFilesSelected(event.target.files)
              }
            }}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
            disabled={!files.length || isBusy}
            onClick={onReset}
            aria-label="Clear selected files"
          >
            <X className="size-4" />
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            onClick={onStart}
            disabled={!files.length || isBusy}
            className="gap-2"
          >
            {isBusy ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                {status === "uploading" ? "Uploading" : "Blurring"}
              </>
            ) : (
              "Blur media"
            )}
          </Button>
          <span
            className={`text-xs ${
              status === "error" ? "text-destructive" : "text-muted-foreground"
            }`}
          >
            {statusMessage}
          </span>
        </div>
        <SelectedFilesSummary files={files} />
        {selectionError && (
          <Alert variant="destructive" className="py-2">
            <AlertDescription className="text-xs">
              {selectionError}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

export { UploadCard }
