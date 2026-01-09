const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString() || "http://localhost:8000"

const apiFetch = (path: string, options?: RequestInit) =>
  fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
  })

const parseErrorMessage = async (response: Response) => {
  try {
    const data = (await response.json()) as { message?: string }
    return data?.message || response.statusText
  } catch {
    return response.statusText || "Request failed."
  }
}

export { API_BASE_URL, apiFetch, parseErrorMessage }
