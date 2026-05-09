/**
 * Energy Trading Analysis Engine
 * Multi-agent LLM analysis for energy commodities using DeepSeek API.
 */

import OpenAI from "openai";
import yahooFinance from "yahoo-finance2";
interface YFChartResult {
  meta: Record<string, unknown>;
  quotes: Array<{
    date: Date;
    high: number | null;
    low: number | null;
    open: number | null;
    close: number | null;
    volume: number | null;
  }>;
}

import {
  computeIndicators,
  formatPriceData,
  formatIndicators,
} from "./tech-indicators";
import type { OHLCV } from "./tech-indicators";

const COMMODITY_MAP: Record<string, string> = {
  BRENT: "BZ=F",
  WTI: "CL=F",
  HH: "NG=F",
  TTF: "TTF=F",
  JKM: "JKM=F",
  LPG: "LPG=F",
};

const COMMODITY_NAMES: Record<string, string> = {
  BRENT: "Brent Crude Oil",
  WTI: "WTI Crude Oil",
  HH: "Henry Hub Natural Gas",
  TTF: "TTF Dutch Natural Gas",
  JKM: "JKM LNG Marker",
  LPG: "LPG (Propane)",
};

const MACRO_TICKERS: Record<string, string> = {
  DXY: "DX-Y.NYB",
  US10Y: "^TNX",
  SPX: "^GSPC",
  VIX: "^VIX",
};

export interface AnalysisConfig {
  apiKey: string;
  baseUrl: string;
  deepModel: string;
  quickModel: string;
}

export interface AnalysisResult {
  commodity: string;
  tradeDate: string;
  technicalReport: string;
  supplyDemandReport: string;
  macroReport: string;
  geopoliticalReport: string;
  investmentPlan: string;
  traderPlan: string;
  finalDecision: string;
  rawData: {
    priceSummary: string;
    macroSummary: string;
  };
}

async function fetchOHLCV(
  symbol: string,
  start: Date,
  end: Date
): Promise<OHLCV[]> {
  const results = (await yahooFinance.chart(symbol, {
    period1: Math.floor(start.getTime() / 1000),
    period2: Math.floor(end.getTime() / 1000),
    interval: "1d",
  })) as YFChartResult;
  return (results.quotes || [])
    .filter((q: any) => q.close != null)
    .map((q: any) => ({
      date: new Date(q.date).toISOString().split("T")[0],
      open: Math.round(q.open * 100) / 100,
      high: Math.round(q.high * 100) / 100,
      low: Math.round(q.low * 100) / 100,
      close: Math.round(q.close * 100) / 100,
      volume: Math.round(q.volume || 0),
    }));
}

async function fetchMacro(start: Date, end: Date): Promise<string> {
  const entries = Object.entries(MACRO_TICKERS);
  const frames: string[] = [];
  for (const [name, ticker] of entries) {
    try {
      const result = (await yahooFinance.chart(ticker, {
        period1: Math.floor(start.getTime() / 1000),
        period2: Math.floor(end.getTime() / 1000),
        interval: "1d",
      })) as YFChartResult;
      const quotes = result.quotes || [];
      if (quotes.length > 0) {
        const latest = quotes[quotes.length - 1];
        const prev = quotes.length > 1 ? quotes[quotes.length - 2] : latest;
        const chg = prev.close && latest.close ? (((latest.close - prev.close) / prev.close) * 100).toFixed(2) : "0.00";
        frames.push(`${name}: ${latest.close?.toFixed(2) ?? "N/A"} (${chg}%)`);
      }
    } catch {
      frames.push(`${name}: N/A`);
    }
  }
  return frames.join(" | ");
}

function createClient(config: AnalysisConfig) {
  return new OpenAI({
    apiKey: config.apiKey,
    baseURL: config.baseUrl,
  });
}

async function chat(
  client: OpenAI,
  model: string,
  system: string,
  user: string,
  temperature = 0.3
): Promise<string> {
  const resp = await client.chat.completions.create({
    model,
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    temperature,
    max_tokens: 4000,
  });
  return resp.choices[0]?.message?.content || "";
}

export async function runAnalysis(
  commodity: string,
  tradeDate: string,
  config: AnalysisConfig
): Promise<AnalysisResult> {
  const symbol = COMMODITY_MAP[commodity.toUpperCase()] || commodity;
  const name = COMMODITY_NAMES[commodity.toUpperCase()] || commodity;
  const client = createClient(config);

  // Date range: 150 days before tradeDate
  const endDate = new Date(tradeDate);
  endDate.setDate(endDate.getDate() + 1);
  const startDate = new Date(tradeDate);
  startDate.setDate(startDate.getDate() - 150);

  // Fetch data
  let ohlcv: OHLCV[] = [];
  let macroStr = "";
  try {
    ohlcv = await fetchOHLCV(symbol, startDate, endDate);
  } catch (e: any) {
    console.warn("OHLCV fetch failed:", e.message);
  }
  try {
    macroStr = await fetchMacro(startDate, endDate);
  } catch (e: any) {
    console.warn("Macro fetch failed:", e.message);
  }

  // Compute indicators
  let indStr = "";
  let latestInd: Record<string, number | null> = {};
  if (ohlcv.length >= 60) {
    const { indicators, latest } = computeIndicators(ohlcv);
    indStr = formatIndicators(indicators, ohlcv);
    latestInd = latest;
  }

  const priceStr = formatPriceData(ohlcv, 60);
  const latestPrice = ohlcv.length > 0 ? ohlcv[ohlcv.length - 1] : null;

  const baseContext = [
    `Commodity: ${name} (${commodity})`,
    `Trade Date: ${tradeDate}`,
    latestPrice
      ? `Latest Price: O=${latestPrice.open} H=${latestPrice.high} L=${latestPrice.low} C=${latestPrice.close} V=${latestPrice.volume}`
      : "No price data available",
    `\nRecent OHLCV (last 60 days):\n${priceStr}`,
    indStr ? `\nTechnical Indicators:\n${indStr}` : "",
    `\nMacro Context: ${macroStr}`,
    `\nLatest Indicator Snapshot: ${JSON.stringify(latestInd)}`,
  ]
    .filter(Boolean)
    .join("\n");

  // 1. Technical Analyst
  const technicalReport = await chat(
    client,
    config.quickModel,
    `You are a senior technical analyst for energy commodities. Analyze price action, momentum, trend, volatility. Include support/resistance, RSI, MACD, Bollinger, SMA alignment, ATR, and seasonal patterns. Write in markdown with a summary table.`,
    `${baseContext}\n\nProvide your technical analysis report.`
  );

  // 2. Supply/Demand Analyst
  const supplyDemandReport = await chat(
    client,
    config.quickModel,
    `You are a supply & demand analyst for global energy. Assess surplus/deficit/balance from price trajectory, volume, and seasonality. Consider OPEC+, shale trends, storage cycles, refinery maintenance. Write in markdown with a summary table.`,
    `${baseContext}\n\nProvide your supply & demand outlook.`
  );

  // 3. Macro Analyst
  const macroReport = await chat(
    client,
    config.quickModel,
    `You are a macro strategist for energy. Analyze USD (DXY), interest rates (10Y), equity sentiment (SPX/VIX), inflation, and central bank policy impacts on commodity pricing. Write in markdown with a summary table.`,
    `${baseContext}\n\nProvide your macro analysis.`
  );

  // 4. Geopolitical Analyst
  const geopoliticalReport = await chat(
    client,
    config.quickModel,
    `You are a geopolitical risk analyst for energy markets. Assess risk premium: Middle East, Russia-Ukraine, US-China trade, maritime security, sanctions. Infer from price gaps, volatility spikes, spread dislocations. Write in markdown with a summary table.`,
    `${baseContext}\n\nProvide your geopolitical risk assessment.`
  );

  // 5. Bull Researcher
  const bullCase = await chat(
    client,
    config.quickModel,
    `You are a BULLISH energy researcher. Make the strongest LONG case. Highlight tightening S/D, supportive seasonality, bullish breakouts, weak USD, dovish CBs, supply disruption risk. Be aggressive but honest.`,
    `${baseContext}\n\nTechnical: ${technicalReport.slice(0, 800)}\n\nS/D: ${supplyDemandReport.slice(0, 800)}\n\nMacro: ${macroReport.slice(0, 800)}\n\nGeo: ${geopoliticalReport.slice(0, 800)}\n\nMake your bull case.`
  );

  // 6. Bear Researcher
  const bearCase = await chat(
    client,
    config.quickModel,
    `You are a BEARISH energy researcher. Make the strongest SHORT/FLAT case. Highlight oversupply (shale, OPEC+ cheating), demand destruction (recession, EVs, mild weather), bearish breakdowns, strong USD, hawkish CBs. Be aggressive but honest.`,
    `${baseContext}\n\nTechnical: ${technicalReport.slice(0, 800)}\n\nS/D: ${supplyDemandReport.slice(0, 800)}\n\nMacro: ${macroReport.slice(0, 800)}\n\nGeo: ${geopoliticalReport.slice(0, 800)}\n\nBull case: ${bullCase.slice(0, 800)}\n\nMake your bear case.`
  );

  // 7. Research Manager (deep model)
  const investmentPlan = await chat(
    client,
    config.deepModel,
    `You are the Research Manager. Synthesize bull and bear arguments into a 5-tier recommendation (Buy/Overweight/Hold/Underweight/Sell). Provide strategic actions: entry levels, stop-loss, sizing, roll/calendar considerations for futures.`,
    `Bull Case:\n${bullCase}\n\nBear Case:\n${bearCase}\n\nCommodity: ${name}\n\nIssue your research plan.`
  );

  // 8. Trader
  const traderPlan = await chat(
    client,
    config.quickModel,
    `You are the futures trader. Translate the research plan into a concrete transaction: action (Buy/Hold/Sell), entry price, stop-loss, position-sizing, time horizon. Be specific to the commodity.`,
    `${baseContext}\n\nResearch Plan: ${investmentPlan}\n\nIssue your trader proposal.`
  );

  // 9. Risk debate (Aggressive + Conservative + Neutral combined for efficiency)
  const riskAnalysis = await chat(
    client,
    config.deepModel,
    `You are the Portfolio Manager for energy commodities. You have three risk voices:
- AGGRESSIVE: pushes max conviction, larger size or full rejection
- CONSERVATIVE: prioritizes capital preservation, wider stops, smaller size
- NEUTRAL: balances both sides

Synthesize all views into a final structured decision with: rating, executive summary, investment thesis, price target, time horizon, and key risk factors.`,
    `Trader Proposal: ${traderPlan}\n\nResearch Plan: ${investmentPlan}\n\nTechnical: ${technicalReport.slice(0, 600)}\n\nS/D: ${supplyDemandReport.slice(0, 600)}\n\nMacro: ${macroReport.slice(0, 600)}\n\nGeo: ${geopoliticalReport.slice(0, 600)}\n\nIssue your final portfolio decision.`
  );

  return {
    commodity,
    tradeDate,
    technicalReport,
    supplyDemandReport,
    macroReport,
    geopoliticalReport,
    investmentPlan,
    traderPlan,
    finalDecision: riskAnalysis,
    rawData: {
      priceSummary: latestPrice
        ? `${latestPrice.date}: O=${latestPrice.open} H=${latestPrice.high} L=${latestPrice.low} C=${latestPrice.close}`
        : "No data",
      macroSummary: macroStr,
    },
  };
}
