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
  const [videoDuration, setVideoDuration] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const parsePositiveInt = (value: string | undefined, fallback: number) => {
    const parsed = Number(value)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return fallback
    }
    return Math.floor(parsed)
  }

  const parsePositiveFloat = (value: string | undefined, fallback: number) => {
    const parsed = Number(value)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return fallback
    }
    return parsed
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
  const maxVideoMb = parsePositiveInt(import.meta.env.VITE_MAX_VIDEO_MB, 50)
  const maxVideoBytes = maxVideoMb * 1024 * 1024
  const maxVideoFps = parsePositiveInt(import.meta.env.VITE_VIDEO_MAX_FPS, 20)
  const detectEveryN = parsePositiveInt(
    import.meta.env.VITE_VIDEO_DETECT_EVERY_N,
    4
  )
  const etaUnitsPerSecond = parsePositiveFloat(
    import.meta.env.VITE_VIDEO_ETA_UNITS_PER_SEC,
    6
  )
  const allowedExtensions = parseExtensions(
    import.meta.env.VITE_ALLOWED_EXTENSIONS,
    ["jpg", "jpeg", "png", "webp", "bmp", "gif", "tif", "tiff"]
  )
  const allowedVideoExtensions = parseExtensions(
    import.meta.env.VITE_ALLOWED_VIDEO_EXTENSIONS,
    ["mp4", "webm", "mov", "mkv"]
  )
  const allowedExtensionsSet = new Set(allowedExtensions)
  const allowedVideoExtensionsSet = new Set(allowedVideoExtensions)
  const acceptExtensions = [...allowedExtensions, ...allowedVideoExtensions]
    .map((ext) => `.${ext}`)
    .join(",")

  const isVideoFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
    return ext && allowedVideoExtensionsSet.has(ext)
  }

  const formatDuration = (value: number) => {
    const totalSeconds = Math.max(0, Math.round(value))
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes === 0) {
      return `${seconds}s`
    }
    return `${minutes}m ${seconds.toString().padStart(2, "0")}s`
  }

  const isBusy = status === "uploading" || status === "processing"
  const statusMessage = useMemo(() => {
    switch (status) {
      case "uploading":
        return "Uploading media..."
      case "processing":
        return "Blurring in worker..."
      case "ready":
        return "Results are ready."
      case "error":
        return "Something went wrong."
      default:
        return files.length ? "Ready to blur." : "Select media to start."
    }
  }, [files.length, status])

  useEffect(() => {
    return () => {
      resultPreviews.forEach((preview) => URL.revokeObjectURL(preview.url))
    }
  }, [resultPreviews])

  useEffect(() => {
    let cancelled = false
    if (files.length === 1 && isVideoFile(files[0])) {
      const file = files[0]
      const url = URL.createObjectURL(file)
      const video = document.createElement("video")
      video.preload = "metadata"
      video.onloadedmetadata = () => {
        if (cancelled) return
        setVideoDuration(Number.isFinite(video.duration) ? video.duration : null)
        URL.revokeObjectURL(url)
      }
      video.onerror = () => {
        if (cancelled) return
        setVideoDuration(null)
        URL.revokeObjectURL(url)
      }
      video.src = url
    } else {
      setVideoDuration(null)
    }

    return () => {
      cancelled = true
    }
  }, [files])

  const handleFiles = (incoming: FileList | File[]) => {
    if (isBusy) return
    const next = Array.from(incoming)
    const imageFiles = next.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
      return ext && allowedExtensionsSet.has(ext)
    })
    const videoFiles = next.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
      return ext && allowedVideoExtensionsSet.has(ext)
    })
    const invalidExtensions = next.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
      return (
        !ext ||
        (!allowedExtensionsSet.has(ext) && !allowedVideoExtensionsSet.has(ext))
      )
    })
    const oversizedImages = imageFiles.filter((file) => file.size > maxUploadBytes)
    const oversizedVideos = videoFiles.filter((file) => file.size > maxVideoBytes)

    let acceptedImages = imageFiles.filter((file) => file.size <= maxUploadBytes)
    const exceededLimit = acceptedImages.length > maxFiles
    if (exceededLimit) {
      acceptedImages = acceptedImages.slice(0, maxFiles)
    }
    const acceptedVideos = videoFiles.filter(
      (file) => file.size <= maxVideoBytes
    )

    const messages: string[] = []
    if (invalidExtensions.length > 0) {
      messages.push(
        `${invalidExtensions.length} file(s) have unsupported extensions.`
      )
    }
    if (oversizedImages.length > 0) {
      messages.push(
        `${oversizedImages.length} file(s) exceed ${maxUploadMb} MB and were skipped.`
      )
    }
    if (oversizedVideos.length > 0) {
      messages.push(
        `${oversizedVideos.length} video(s) exceed ${maxVideoMb} MB and were skipped.`
      )
    }
    if (exceededLimit) {
      messages.push(`Only ${maxFiles} images can be uploaded at once.`)
    }
    if (acceptedVideos.length > 1) {
      messages.push("Only one video can be uploaded at a time.")
    }

    let accepted: File[] = []
    if (acceptedVideos.length > 0) {
      accepted = [acceptedVideos[0]]
      if (acceptedImages.length > 0) {
        messages.push("Images were skipped because a video was selected.")
      }
    } else {
      accepted = acceptedImages
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

  const etaHint = useMemo(() => {
    if (!videoDuration) return null
    const estimatedFrames = Math.max(1, Math.ceil(videoDuration * maxVideoFps))
    const detectionPasses = Math.ceil(estimatedFrames / detectEveryN)
    const workUnits = estimatedFrames + detectionPasses
    const etaSeconds = Math.ceil(workUnits / etaUnitsPerSecond)
    return `ETA (rough): ~${formatDuration(etaSeconds)} for a ${formatDuration(
      videoDuration
    )} video.`
  }, [detectEveryN, maxVideoFps, videoDuration])

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
    const isVideo = files.length === 1 && isVideoFile(files[0])
    if (isVideo) {
      payload.append("file", files[0])
    } else {
      for (const file of files) {
        payload.append("files", file)
      }
    }

    try {
      const endpoint = isVideo ? "/blur/video" : "/blur"
      const response = await apiFetch(endpoint, {
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
              type: "image",
            })
          }
          setResultPreviews(images)
        } else if (contentType.startsWith("image/")) {
          setDownload({ blob, filename: "blurred_image.jpg" })
          setResultPreviews([
            {
              name: "blurred_image.jpg",
              url: URL.createObjectURL(blob),
              type: "image",
            },
          ])
        } else if (contentType.startsWith("video/")) {
          setDownload({ blob, filename: "blurred_video.mp4" })
          setResultPreviews([
            {
              name: "blurred_video.mp4",
              url: URL.createObjectURL(blob),
              type: "video",
            },
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
    maxVideoMb,
    allowedExtensions,
    allowedVideoExtensions,
    acceptExtensions,
    etaHint,
    handleFiles,
    resetAll,
    startProcessing,
    handleDownload,
  }
}

export { useBlurWorkflow }
