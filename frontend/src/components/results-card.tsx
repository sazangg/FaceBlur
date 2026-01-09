import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog"
import type { DownloadPayload, ResultPreview } from "@/types"

type ResultsCardProps = {
  resultPreviews: ResultPreview[]
  download: DownloadPayload | null
  downloadBusy: boolean
  isBusy: boolean
  onDownload: () => void
}

const ResultsCard = ({
  resultPreviews,
  download,
  downloadBusy,
  isBusy,
  onDownload,
}: ResultsCardProps) => {
  const [selectedPreview, setSelectedPreview] =
    useState<ResultPreview | null>(null)
  const [carouselApi, setCarouselApi] = useState<CarouselApi | null>(null)
  const [showCarouselControls, setShowCarouselControls] = useState(false)

  useEffect(() => {
    if (!carouselApi) return
    const updateControls = () =>
      setShowCarouselControls(
        carouselApi.canScrollPrev() || carouselApi.canScrollNext()
      )
    updateControls()
    carouselApi.on("select", updateControls)
    carouselApi.on("reInit", updateControls)
    return () => {
      carouselApi.off("select", updateControls)
      carouselApi.off("reInit", updateControls)
    }
  }, [carouselApi])

  if (!resultPreviews.length) {
    return null
  }

  return (
    <>
      <Card className="gap-4">
        <CardHeader>
          <CardTitle>Results</CardTitle>
          <CardDescription>
            {resultPreviews.length === 1
              ? "Single image result."
              : "Swipe through your blurred images."}
          </CardDescription>
        </CardHeader>
        <CardContent className="h-72">
          {resultPreviews.length === 1 ? (
            <div className="flex h-full items-center justify-center">
              <Button
                type="button"
                variant="ghost"
                className="h-full w-full overflow-hidden rounded-md border p-0"
                onClick={() => setSelectedPreview(resultPreviews[0])}
              >
                <img
                  src={resultPreviews[0].url}
                  alt={resultPreviews[0].name}
                  className="h-full w-full object-contain"
                />
              </Button>
            </div>
          ) : (
            <Carousel
              className="h-full w-full"
              opts={{ align: "start", loop: true }}
              setApi={setCarouselApi}
            >
              <CarouselContent
                className="h-full items-center"
                containerClassName="h-full"
              >
                {resultPreviews.map((preview) => (
                  <CarouselItem
                    key={preview.url}
                    className="h-full basis-1/2 sm:basis-1/3 lg:basis-1/4"
                  >
                    <Button
                      type="button"
                      variant="ghost"
                      className="h-full w-full overflow-hidden rounded-md border p-0"
                      onClick={() => setSelectedPreview(preview)}
                    >
                      <img
                        src={preview.url}
                        alt={preview.name}
                        className="h-full w-full object-contain"
                      />
                    </Button>
                  </CarouselItem>
                ))}
              </CarouselContent>
              {showCarouselControls && (
                <>
                  <CarouselPrevious className="left-2" />
                  <CarouselNext className="right-2" />
                </>
              )}
            </Carousel>
          )}
        </CardContent>
        <CardFooter className="justify-end gap-2">
          <Button
            type="button"
            onClick={onDownload}
            disabled={downloadBusy || !download || isBusy}
          >
            {resultPreviews.length === 1 ? "Download image" : "Download zip"}
          </Button>
        </CardFooter>
      </Card>

      <Dialog
        open={Boolean(selectedPreview)}
        onOpenChange={(open) => {
          if (!open) setSelectedPreview(null)
        }}
      >
        <DialogContent className="w-fit max-w-[90vw] place-items-center p-4 sm:max-w-[90vw]">
          <DialogTitle className="sr-only">Blurred image preview</DialogTitle>
          <DialogDescription className="sr-only">
            Full-size preview of the selected blurred image.
          </DialogDescription>
          {selectedPreview && (
            <img
              src={selectedPreview.url}
              alt={selectedPreview.name}
              className="max-h-[70vh] w-auto max-w-[85vw] object-contain"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}

export { ResultsCard }
