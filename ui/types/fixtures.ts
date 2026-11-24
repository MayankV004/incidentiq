import { Hypothesis } from "./api";

export const FIXTURE_DB_POOL_EXHAUSTION: Hypothesis = {
  category: "db_pool_exhaustion",
  service: "orders",
  confidence: 0.85,
  groundedness_score: 1.0,
  reasoning: "Metrics and logs confirm the database connection pool on 'orders' is fully exhausted.",
  abstained: false,
  evidence_ids: ["ev_metric_db_pool_in_use", "ev_log_err_1"],
  suggested_action: {
    type: "review_config",
    target: "orders",
    detail: "Increase MAX_DB_POOL_SIZE from 10 to 20 or restart leaked connections",
  },
};

export const FIXTURE_DEPENDENCY_TIMEOUT: Hypothesis = {
  category: "dependency_timeout",
  service: "payments",
  confidence: 0.9,
  groundedness_score: 1.0,
  reasoning: "Downstream external provider calls timed out on 'payments'. Logs report ReadTimeout after 5000ms.",
  abstained: false,
  evidence_ids: ["ev_log_cluster_1", "ev_metric_error_rate"],
  suggested_action: {
    type: "review_config",
    target: "payments",
    detail: "Adjust external client timeout and engage circuit-breaker",
  },
};

export const FIXTURE_MEMORY_LEAK: Hypothesis = {
  category: "memory_leak",
  service: "gateway",
  confidence: 0.88,
  groundedness_score: 1.0,
  reasoning: "Process memory usage climbed to container quota on 'gateway', triggering OOM kill.",
  abstained: false,
  evidence_ids: ["ev_metric_memory_mb", "ev_log_err_1"],
  suggested_action: {
    type: "restart_service",
    target: "gateway",
    detail: "Restart service container to clear heap allocations",
  },
};

export const TYPED_FAULT_FIXTURES: Record<string, Hypothesis> = {
  db_pool_exhaustion: FIXTURE_DB_POOL_EXHAUSTION,
  dependency_timeout: FIXTURE_DEPENDENCY_TIMEOUT,
  memory_leak: FIXTURE_MEMORY_LEAK,
};
