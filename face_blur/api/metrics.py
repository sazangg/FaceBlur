from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

BLUR_TASKS_SUBMITTED = Counter(
    "blur_tasks_submitted_total",
    "Total blur tasks submitted",
)

BLUR_RESULTS_SERVED = Counter(
    "blur_results_served_total",
    "Total blur results served",
    ["type"],
)

BLUR_ERRORS = Counter(
    "blur_errors_total",
    "Total blur errors by code",
    ["code"],
)

VIDEO_TASKS_SUBMITTED = Counter(
    "video_tasks_submitted_total",
    "Total video blur tasks submitted",
)

VIDEO_RESULTS_SERVED = Counter(
    "video_results_served_total",
    "Total video blur results served",
)

VIDEO_DURATION_SECONDS = Counter(
    "video_blur_duration_seconds_total",
    "Total duration of blurred videos in seconds",
)
