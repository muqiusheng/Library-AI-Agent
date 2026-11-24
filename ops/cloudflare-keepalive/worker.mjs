export default {
  async scheduled(controller, env) {
    const started = Date.now();
    const response = await fetch(env.TARGET_URL, {
      method: "GET",
      headers: { "Cache-Control": "no-cache" },
      cache: "no-store",
      signal: AbortSignal.timeout(60_000),
    });

    if (!response.ok) {
      throw new Error(`BookPath health check returned HTTP ${response.status}`);
    }

    const result = await response.json();
    if (result.data?.status !== "ok") {
      throw new Error(`BookPath health check returned ${result.data?.status ?? "invalid data"}`);
    }

    console.log(JSON.stringify({
      event: "bookpath-health-check",
      scheduledAt: new Date(controller.scheduledTime).toISOString(),
      status: response.status,
      health: result.data.status,
      elapsedMs: Date.now() - started,
    }));
  },
};
