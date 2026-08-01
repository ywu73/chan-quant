export interface VisibilitySource {
  readonly visibilityState: "visible" | "hidden";
  addEventListener(type: "visibilitychange", listener: () => void): void;
  removeEventListener(type: "visibilitychange", listener: () => void): void;
}


interface VisiblePollingOptions {
  poll: (signal: AbortSignal) => Promise<void>;
  visibilitySource: VisibilitySource;
  intervalMs: number;
}


export function startVisiblePolling({
  poll,
  visibilitySource,
  intervalMs,
}: VisiblePollingOptions): () => void {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let activeController: AbortController | undefined;

  const clearTimer = () => {
    if (timer !== undefined) {
      clearTimeout(timer);
      timer = undefined;
    }
  };

  const run = async () => {
    if (stopped || visibilitySource.visibilityState !== "visible") return;

    const controller = new AbortController();
    activeController = controller;
    try {
      await poll(controller.signal);
    } finally {
      if (activeController === controller) activeController = undefined;
      if (!stopped && !controller.signal.aborted && visibilitySource.visibilityState === "visible") {
        timer = setTimeout(() => void run(), intervalMs);
      }
    }
  };

  const handleVisibility = () => {
    clearTimer();
    activeController?.abort();
    activeController = undefined;
    if (visibilitySource.visibilityState === "visible") {
      void run();
    }
  };

  visibilitySource.addEventListener("visibilitychange", handleVisibility);
  void run();

  return () => {
    stopped = true;
    activeController?.abort();
    activeController = undefined;
    clearTimer();
    visibilitySource.removeEventListener("visibilitychange", handleVisibility);
  };
}
