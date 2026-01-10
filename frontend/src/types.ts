export type Status = "idle" | "uploading" | "processing" | "ready" | "error"

export type ResultPreview = {
  name: string
  url: string
  type: "image" | "video"
}

export type DownloadPayload = {
  blob: Blob
  filename: string
}

export type VanityStats = {
  total_visitors: number
  total_images: number
  total_requests: number
  total_videos: number
  total_video_seconds: number
}
