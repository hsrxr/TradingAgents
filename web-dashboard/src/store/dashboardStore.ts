import { create } from "zustand";
import { mockDashboardSnapshot } from "@/data/mockData";
import type {
  RuntimeEvent,
  TradeRecord,
  TradingDashboardSnapshot,
} from "@/types/trading";

interface DashboardState {
  baseSnapshot: TradingDashboardSnapshot;
  runtimeEvents: RuntimeEvent[];
  eventOffset: number;
  runId: string | null;
  trades: TradeRecord[];
  isRunning: boolean;
  autoTriggerEnabled: boolean;
  autoTriggerIntervalSec: number;
  runCount: number;
  lastRunAt: string | null;
  errorMessage: string | null;
  startRun: () => Promise<void>;
  stopRun: () => void;
  setAutoTriggerEnabled: (enabled: boolean) => void;
  setAutoTriggerIntervalSec: (seconds: number) => void;
}

const API_BASE = "http://127.0.0.1:8765";

let pollingTimer: ReturnType<typeof setInterval> | null = null;
let autoTriggerTimer: ReturnType<typeof setInterval> | null = null;

export const useDashboardStore = create<DashboardState>((set, get) => ({
  baseSnapshot: mockDashboardSnapshot,
  runtimeEvents: [],
  eventOffset: 0,
  runId: null,
  trades: [],
  isRunning: false,
  autoTriggerEnabled: false,
  autoTriggerIntervalSec: 30,
  runCount: 0,
  lastRunAt: null,
  errorMessage: null,

  startRun: async () => {
    if (get().isRunning) {
      return;
    }

    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }

    set((state: DashboardState) => ({
      runtimeEvents: [],
      eventOffset: 0,
      runId: null,
      trades: [],
      isRunning: true,
      runCount: state.runCount + 1,
      lastRunAt: new Date().toISOString(),
      errorMessage: null,
    }));

    try {
      const response = await fetch(`${API_BASE}/api/run/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pair: get().baseSnapshot.pair,
          selectedAnalysts: ["market", "news", "quant"],
          parallelMode: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`start run failed: ${response.status}`);
      }

      const payload = (await response.json()) as { runId: string };
      const runId = payload.runId;

      set({ runId });

      pollingTimer = setInterval(async () => {
        const { runId: activeRunId, eventOffset } = get();
        if (!activeRunId) {
          return;
        }

        try {
          const eventsRes = await fetch(
            `${API_BASE}/api/runs/${activeRunId}/events?after=${eventOffset}`,
          );
          if (!eventsRes.ok) {
            return;
          }
          const eventsPayload = (await eventsRes.json()) as {
            events: RuntimeEvent[];
            nextOffset: number;
            status: string;
            decision?: string | null;
            error?: string | null;
          };

          const newEvents = eventsPayload.events || [];

          set((state) => ({
            runtimeEvents: [...state.runtimeEvents, ...newEvents],
            eventOffset: eventsPayload.nextOffset ?? state.eventOffset,
          }));

          if (eventsPayload.status === "completed" || eventsPayload.status === "failed") {
            if (pollingTimer) {
              clearInterval(pollingTimer);
              pollingTimer = null;
            }

            if (eventsPayload.decision) {
              const decision = String(eventsPayload.decision);
              const syntheticTrade: TradeRecord = {
                id: `decision-${Date.now()}`,
                timestamp: new Date().toISOString(),
                pair: get().baseSnapshot.pair,
                side: decision.includes("BUY") ? "BUY" : "SELL",
                quantity: 0,
                price: 0,
                reason: decision,
              };
              set((state) => ({
                trades: [syntheticTrade, ...state.trades],
              }));
            }

            set({ isRunning: false });

            if (eventsPayload.status === "failed") {
              set({
                errorMessage:
                  eventsPayload.error ?? "runtime execution failed before trace output was generated",
              });
            }
          }
        } catch {
          // Keep polling loop resilient to transient failures.
        }
      }, 900);
    } catch (error) {
      set({
        isRunning: false,
        errorMessage: error instanceof Error ? error.message : "failed to start runtime api run",
      });
    }
  },

  stopRun: () => {
    if (pollingTimer) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
    set({ isRunning: false });
  },

  setAutoTriggerEnabled: (enabled: boolean) => {
    if (autoTriggerTimer) {
      clearInterval(autoTriggerTimer);
      autoTriggerTimer = null;
    }

    set({ autoTriggerEnabled: enabled });

    if (!enabled) {
      return;
    }

    const intervalMs = Math.max(5, get().autoTriggerIntervalSec) * 1000;
    autoTriggerTimer = setInterval(() => {
      if (!get().isRunning) {
        get().startRun();
      }
    }, intervalMs);
  },

  setAutoTriggerIntervalSec: (seconds: number) => {
    const safeSeconds = Math.max(5, Math.floor(seconds));
    set({ autoTriggerIntervalSec: safeSeconds });

    if (get().autoTriggerEnabled) {
      get().setAutoTriggerEnabled(true);
    }
  },
}));
