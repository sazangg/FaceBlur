import { useEffect, useState } from "react"

type Theme = "light" | "dark"

const STORAGE_KEY = "theme"

const getInitialTheme = (): Theme => {
  if (typeof window === "undefined") {
    return "light"
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === "light" || stored === "dark") {
      return stored
    }
  } catch {
    // Ignore storage errors and fall back to media preference.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

const useTheme = () => {
  const [theme, setTheme] = useState<Theme>(() => getInitialTheme())

  useEffect(() => {
    const isDark = theme === "dark"
    document.documentElement.classList.toggle("dark", isDark)
    document.documentElement.style.colorScheme = isDark ? "dark" : "light"
    try {
      window.localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Ignore storage errors.
    }
  }, [theme])

  const toggleTheme = () => {
    setTheme((current) => (current === "dark" ? "light" : "dark"))
  }

  return { theme, toggleTheme }
}

export { useTheme }
