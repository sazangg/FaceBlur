import logo from "@/assets/blurred_face.jpeg"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useTheme } from "@/hooks/useTheme"

const AppHeader = () => {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="space-y-2 text-center">
      <div className="flex justify-center">
        <div
          onClick={toggleTheme}
          className="flex items-center h-auto cursor-pointer gap-3 px-0 py-1 text-3xl font-semibold tracking-tight text-foreground transition-none hover:bg-transparent hover:text-foreground focus-visible:ring-0 focus-visible:ring-offset-0"
          aria-label={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          <Avatar className="size-10 border border-border/60">
            <AvatarImage src={logo} alt="FaceBlur logo" />
            <AvatarFallback>FB</AvatarFallback>
          </Avatar>
          FaceBlur
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        Upload images or a single video to get back media with blurred faces.
      </p>
    </div>
  )
}

export { AppHeader }
