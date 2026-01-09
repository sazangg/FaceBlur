import { useEffect, useMemo, useRef, useState } from "react"
import { unzipSync } from "fflate"

import { apiFetch, parseErrorMessage } from "@/lib/api"
import type { DownloadPayload, ResultPreview, Status } from "@/types"

const POLL_INTERVAL = 1500

const useBlurWorkflow = () => {
  const [files, setFiles] = useState<File[]>([])
  const [status, setStatus] = useState<Status>("idle")
  const [download, setDownload] = useState<DownloadPayload | null>(null)
  const [downloadBusy, setDownloadBusy] = useState(false)
  const [resultPreviews, setResultPreviews] = useState<ResultPreview[]>([])
  const [taskId, setTaskId] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [selectionError, setSelectionError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parsePositiveInt = (value: string | undefined, fallback: number) => {
    const parsed = Number(value)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return fallback
    }
    return Math.floor(parsed)
  }

  const parseExtensions = (value: string | undefined, fallback: string[]) => {
    if (!value) {
      return fallback
    }
    const parsed = value
      .split(",")
      .map((ext) => ext.trim().replace(/^\./, "").toLowerCase())
      .filter(Boolean)
    return parsed.length ? parsed : fallback
  }

  const maxFiles = parsePositiveInt(
    import.meta.env.VITE_MAX_UPLOAD_FILES,
    10
  )
  const maxUploadMb = parsePositiveInt(import.meta.env.VITE_MAX_UPLOAD_MB, 25)
  const maxUploadBytes = maxUploadMb * 1024 * 1024
  const allowedExtensions = parseExtensions(
    import.meta.env.VITE_ALLOWED_EXTENSIONS,
    ["jpg", "jpeg", "png", "webp", "bmp", "gif", "tif", "tiff"]
  )
  const allowedExtensionsSet = new Set(allowedExtensions)
  const acceptExtensions = allowedExtensions.map((ext) => `.${ext}`).join(",")

  const isBusy = status === "uploading" || status === "processing"
  const statusMessage = useMemo(() => {
    switch (status) {
      case "uploading":
        return "Uploading images..."
      case "processing":
        return "Blurring in worker..."
      case "ready":
        return "Results are ready."
      case "error":
        return "Something went wrong."
      default:
        return files.length ? "Ready to blur." : "Select images to start."
    }
  }, [files.length, status])

  useEffect(() => {
    return () => {
      resultPreviews.forEach((preview) => URL.revokeObjectURL(preview.url))
    }
  }, [resultPreviews])

  const handleFiles = (incoming: FileList | File[]) => {
    if (isBusy) return
    const next = Array.from(incoming).filter((file) =>
      file.type.startsWith("image/")
    )
    const invalidExtensions = next.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
      return !ext || !allowedExtensionsSet.has(ext)
    })
    const validByExtension = next.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
      return ext && allowedExtensionsSet.has(ext)
    })
    const oversized = validByExtension.filter(
      (file) => file.size > maxUploadBytes
    )
    let accepted = validByExtension.filter(
      (file) => file.size <= maxUploadBytes
    )
    const exceededLimit = accepted.length > maxFiles
    if (exceededLimit) {
      accepted = accepted.slice(0, maxFiles)
    }

    const messages: string[] = []
    if (invalidExtensions.length > 0) {
      messages.push(
        `${invalidExtensions.length} file(s) have unsupported extensions.`
      )
    }
    if (oversized.length > 0) {
      messages.push(
        `${oversized.length} file(s) exceed ${maxUploadMb} MB and were skipped.`
      )
    }
    if (exceededLimit) {
      messages.push(`Only ${maxFiles} images can be uploaded at once.`)
    }
    setSelectionError(messages.length ? messages.join(" ") : null)
    setFiles(accepted)
    setStatus("idle")
    setTaskId(null)
    setDownload(null)
    setDownloadBusy(false)
    setResultPreviews([])
    setErrorMessage(null)
  }

  const resetAll = () => {
    if (isBusy) return
    setFiles([])
    setStatus("idle")
    setTaskId(null)
    setDownload(null)
    setDownloadBusy(false)
    setResultPreviews([])
    setErrorMessage(null)
    setSelectionError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const startProcessing = async () => {
    if (!files.length || isBusy) return
    setStatus("uploading")
    setErrorMessage(null)
    setDownload(null)
    setResultPreviews([])

    const payload = new FormData()
    for (const file of files) {
      payload.append("files", file)
    }

    try {
      const response = await apiFetch("/blur", {
        method: "POST",
        body: payload,
      })
      if (!response.ok) {
        const message = await parseErrorMessage(response)
        setStatus("error")
        setErrorMessage(message)
        return
      }
      const data = (await response.json()) as { data?: { task_id?: string } }
      if (!data?.data?.task_id) {
        setStatus("error")
        setErrorMessage("Backend did not return a task id.")
        return
      }
      setTaskId(data.data.task_id)
      setStatus("processing")
    } catch (error) {
      setStatus("error")
      setErrorMessage(
        error instanceof Error ? error.message : "Upload failed."
      )
    }
  }

  const handleDownload = () => {
    if (!download || downloadBusy || isBusy) return
    setDownloadBusy(true)
    const blobUrl = URL.createObjectURL(download.blob)
    const link = document.createElement("a")
    link.href = blobUrl
    link.download = download.filename
    link.click()
    URL.revokeObjectURL(blobUrl)
    setDownloadBusy(false)
  }

  useEffect(() => {
    if (!taskId || status !== "processing") return

    let cancelled = false
    let timerId: number | undefined

    const poll = async () => {
      try {
        const response = await apiFetch(`/results/${taskId}`)
        if (cancelled) return
        if (response.status === 202) {
          timerId = window.setTimeout(poll, POLL_INTERVAL)
          return
        }
        if (!response.ok) {
          const message = await parseErrorMessage(response)
          setStatus("error")
          setErrorMessage(message)
          return
        }

        const contentType = response.headers.get("content-type") || ""
        const blob = await response.blob()
        if (contentType.includes("application/zip")) {
          setDownload({ blob, filename: "blurred_images.zip" })
          const buffer = await blob.arrayBuffer()
          const entries = unzipSync(new Uint8Array(buffer))
          const images: ResultPreview[] = []
          for (const [name, data] of Object.entries(entries)) {
            if (!name.match(/\.(png|jpe?g|webp|gif|bmp|tiff?)$/i)) {
              continue
            }
            const imageBlob = new Blob([new Uint8Array(data)], {
              type: "image/jpeg",
            })
            images.push({
              name,
              url: URL.createObjectURL(imageBlob),
            })
          }
          setResultPreviews(images)
        } else if (contentType.startsWith("image/")) {
          setDownload({ blob, filename: "blurred_image.jpg" })
          setResultPreviews([
            { name: "blurred_image.jpg", url: URL.createObjectURL(blob) },
          ])
        } else {
          setStatus("error")
          setErrorMessage("Unexpected response type.")
          return
        }

        setStatus("ready")
      } catch (error) {
        if (cancelled) return
        setStatus("error")
        setErrorMessage(
          error instanceof Error ? error.message : "Polling failed."
        )
      }
    }

    void poll()

    return () => {
      cancelled = true
      if (timerId) window.clearTimeout(timerId)
    }
  }, [status, taskId])

  return {
    files,
    status,
    isBusy,
    statusMessage,
    download,
    downloadBusy,
    resultPreviews,
    errorMessage,
    selectionError,
    fileInputRef,
    maxFiles,
    maxUploadMb,
    allowedExtensions,
    acceptExtensions,
    handleFiles,
    resetAll,
    startProcessing,
    handleDownload,
  }
}

export { useBlurWorkflow }
