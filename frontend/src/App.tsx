import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AppFooter } from "@/components/app-footer"
import { AppHeader } from "@/components/app-header"
import { ResultsCard } from "@/components/results-card"
import { UploadCard } from "@/components/upload-card"
import { useBlurWorkflow } from "@/hooks/useBlurWorkflow"
import { useHealth } from "@/hooks/useHealth"
import { useStats } from "@/hooks/useStats"
import { API_BASE_URL } from "@/lib/api"

function App() {
  const backendHealthy = useHealth()
  const { stats, statsError } = useStats()
  const {
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
  } = useBlurWorkflow()

  return (
    <div className="min-h-screen bg-background">
      <div className="grid min-h-screen grid-rows-[1fr_auto]">
        <main className="flex items-center justify-center px-6 py-6">
          <div className="w-full max-w-3xl space-y-6">
            <AppHeader />

            <UploadCard
              files={files}
              status={status}
              statusMessage={statusMessage}
              isBusy={isBusy}
              fileInputRef={fileInputRef}
              maxFiles={maxFiles}
              maxUploadMb={maxUploadMb}
              allowedExtensions={allowedExtensions}
              acceptExtensions={acceptExtensions}
              selectionError={selectionError}
              onFilesSelected={handleFiles}
              onStart={startProcessing}
              onReset={resetAll}
            />

            {status === "error" && (
              <Alert variant="destructive">
                <AlertTitle>Request failed</AlertTitle>
                <AlertDescription>
                  {errorMessage || "Please try again."}
                </AlertDescription>
              </Alert>
            )}

            {backendHealthy === false && (
              <Alert variant="destructive">
                <AlertTitle>Backend unavailable</AlertTitle>
                <AlertDescription>
                  Start the API at {API_BASE_URL} before uploading files.
                </AlertDescription>
              </Alert>
            )}

            {status === "ready" && (
              <ResultsCard
                resultPreviews={resultPreviews}
                download={download}
                downloadBusy={downloadBusy}
                isBusy={isBusy}
                onDownload={handleDownload}
              />
            )}
          </div>
        </main>

        <AppFooter
          stats={stats}
          statsError={statsError}
          backendHealthy={backendHealthy}
        />
      </div>
    </div>
  )
}

export default App
