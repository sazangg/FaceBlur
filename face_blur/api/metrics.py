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
