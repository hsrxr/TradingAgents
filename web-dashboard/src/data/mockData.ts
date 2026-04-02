import type {
  AgentProcessMessage,
  AgentStateMessage,
  PricePoint,
  RuntimeEvent,
  TradeExecutionMarker,
  TradeRecord,
  TradingDashboardSnapshot,
} from "@/types/trading";

const baseTime = new Date("2026-03-31T12:00:00Z").getTime();

const makeTs = (minuteOffset: number): string =>
  new Date(baseTime + minuteOffset * 60_000).toISOString();

export const mockPriceSeries: PricePoint[] = [
  { timestamp: makeTs(0), price: 3178.24, volume: 1240 },
  { timestamp: makeTs(1), price: 3180.91, volume: 1332 },
  { timestamp: makeTs(2), price: 3176.33, volume: 1514 },
  { timestamp: makeTs(3), price: 3171.54, volume: 1742 },
  { timestamp: makeTs(4), price: 3174.88, volume: 1681 },
  { timestamp: makeTs(5), price: 3184.21, volume: 1905 },
  { timestamp: makeTs(6), price: 3192.17, volume: 2012 },
  { timestamp: makeTs(7), price: 3188.03, volume: 1764 },
  { timestamp: makeTs(8), price: 3195.66, volume: 2206 },
  { timestamp: makeTs(9), price: 3201.72, volume: 2438 },
  { timestamp: makeTs(10), price: 3196.49, volume: 2148 },
  { timestamp: makeTs(11), price: 3204.85, volume: 2571 },
  { timestamp: makeTs(12), price: 3210.24, volume: 2499 },
  { timestamp: makeTs(13), price: 3205.1, volume: 2352 },
  { timestamp: makeTs(14), price: 3216.78, volume: 2810 },
  { timestamp: makeTs(15), price: 3220.15, volume: 2862 },
];

export const mockExecutionMarkers: TradeExecutionMarker[] = [
  { id: "exec-1", timestamp: makeTs(3), side: "BUY", price: 3171.54 },
  { id: "exec-2", timestamp: makeTs(9), side: "SELL", price: 3201.72 },
  { id: "exec-3", timestamp: makeTs(13), side: "BUY", price: 3205.1 },
];

export const mockAgentFeed: AgentStateMessage[] = [
  {
    id: "feed-1",
    timestamp: makeTs(2),
    agent: "Market Analyst",
    tone: "neutral",
    summary: "Detected liquidity wall near 3185; breakout probability increasing.",
    confidence: 0.74,
  },
  {
    id: "feed-2",
    timestamp: makeTs(3),
    agent: "Bull Researcher",
    tone: "bullish",
    summary: "Funding trend and volume delta align for long continuation setup.",
    confidence: 0.81,
  },
  {
    id: "feed-3",
    timestamp: makeTs(4),
    agent: "Bear Researcher",
    tone: "bearish",
    summary: "Short-term RSI stretch warns of pullback after impulse candle.",
    confidence: 0.63,
  },
  {
    id: "feed-4",
    timestamp: makeTs(5),
    agent: "Risk Engine",
    tone: "risk",
    summary: "Allowing exposure up to 34%, stop-loss tightened to 1.6%.",
    confidence: 0.9,
  },
  {
    id: "feed-5",
    timestamp: makeTs(6),
    agent: "Trader",
    tone: "execution",
    summary: "Executed BUY 3.2 WETH at 3184.21 after consensus threshold met.",
    confidence: 0.96,
  },
  {
    id: "feed-6",
    timestamp: makeTs(10),
    agent: "Trader",
    tone: "execution",
    summary: "Scaled out SELL 2.1 WETH at 3201.72, locking intraday gains.",
    confidence: 0.95,
  },
  {
    id: "feed-7",
    timestamp: makeTs(12),
    agent: "Risk Engine",
    tone: "risk",
    summary: "Volatility spike detected; maintaining defensive trailing stop.",
    confidence: 0.88,
  },
];

export const mockAgentProcessFeed: AgentProcessMessage[] = [
  {
    id: "proc-1",
    timestamp: makeTs(2),
    agent: "Market Analyst",
    stage: "thought",
    title: "Market Structure Check",
    content: "Short-term pullback exhausted near 3170 support. Momentum recovering with higher low setup.",
  },
  {
    id: "proc-2",
    timestamp: makeTs(3),
    agent: "Bull Researcher",
    stage: "thought",
    title: "Bull Thesis",
    content: "Volume expansion and funding normalization suggest continuation toward 3200+ zone.",
  },
  {
    id: "proc-3",
    timestamp: makeTs(4),
    agent: "Bear Researcher",
    stage: "thought",
    title: "Bear Counterpoint",
    content: "Price remains below broader swing resistance. A failed breakout may retrace to 3165.",
  },
  {
    id: "proc-4",
    timestamp: makeTs(5),
    agent: "Risk Engine",
    stage: "output",
    title: "Risk Constraints",
    content: "Approved with max exposure 34%, stop-loss 1.6%, and reduced size if volatility rises above threshold.",
  },
  {
    id: "proc-5",
    timestamp: makeTs(6),
    agent: "Trader",
    stage: "output",
    title: "Execution Result",
    content: "BUY executed: 3.2 WETH @ 3184.21 after multi-agent consensus score crossed execution trigger.",
  },
  {
    id: "proc-6",
    timestamp: makeTs(10),
    agent: "Trader",
    stage: "output",
    title: "Partial Take Profit",
    content: "SELL executed: 2.1 WETH @ 3201.72; moved remaining position to trailing protection mode.",
  },
  {
    id: "proc-7",
    timestamp: makeTs(12),
    agent: "Risk Engine",
    stage: "tool",
    title: "Volatility Recheck",
    content: "ATR and intrabar spread widened. Tightened trailing stop and lowered add-on permission.",
  },
];

export const mockRuntimeEvents: RuntimeEvent[] = [
  {
    id: "evt-1",
    timestamp: makeTs(0),
    event: "run_started",
    actor: "System",
    detail: "Trading run started for WETH/USDC with multi-agent parallel mode.",
  },
  {
    id: "evt-2",
    timestamp: makeTs(1),
    event: "node_start",
    actor: "Graph",
    detail: "Node started: Trading Analysis bootstrap state.",
  },
  {
    id: "evt-3",
    timestamp: makeTs(2),
    event: "llm_call",
    actor: "Market Analyst",
    detail: "Generated short-horizon structure assessment and scenario map.",
  },
  {
    id: "evt-4",
    timestamp: makeTs(3),
    event: "llm_call",
    actor: "Bull Researcher",
    detail: "Produced continuation thesis with confidence 0.81.",
  },
  {
    id: "evt-5",
    timestamp: makeTs(4),
    event: "llm_call",
    actor: "Bear Researcher",
    detail: "Submitted downside invalidation and pullback risk note.",
  },
  {
    id: "evt-6",
    timestamp: makeTs(5),
    event: "tool_call",
    actor: "Risk Engine",
    detail: "Evaluated exposure, stop-loss and volatility guardrails.",
  },
  {
    id: "evt-7",
    timestamp: makeTs(6),
    event: "node_end",
    actor: "Trader",
    detail: "Execution node completed with BUY order placement.",
  },
  {
    id: "evt-8",
    timestamp: makeTs(15),
    event: "run_completed",
    actor: "System",
    detail: "Trading run completed; portfolio metrics and trades persisted.",
  },
];

export const mockTrades: TradeRecord[] = [
  {
    id: "trade-1",
    timestamp: makeTs(3),
    pair: "WETH/USDC",
    side: "BUY",
    quantity: 3.2,
    price: 3171.54,
    reason: "Bull consensus + breakout confirmation",
  },
  {
    id: "trade-2",
    timestamp: makeTs(9),
    pair: "WETH/USDC",
    side: "SELL",
    quantity: 2.1,
    price: 3201.72,
    reason: "Take-profit at resistance band",
  },
  {
    id: "trade-3",
    timestamp: makeTs(13),
    pair: "WETH/USDC",
    side: "BUY",
    quantity: 1.5,
    price: 3205.1,
    reason: "Re-entry after shallow retrace",
  },
];

export const mockDashboardSnapshot: TradingDashboardSnapshot = {
  pair: "WETH/USDC",
  metrics: {
    timestamp: makeTs(15),
    portfolioValue: 248_620.33,
    pnl: 12_438.56,
    riskExposure: 0.34,
    status: "running",
  },
  priceSeries: mockPriceSeries,
  agentFeed: mockAgentFeed,
  agentProcessFeed: mockAgentProcessFeed,
  runtimeEvents: mockRuntimeEvents,
  trades: mockTrades,
  executionMarkers: mockExecutionMarkers,
};
