/**
 * Technical indicator calculations for energy commodity analysis.
 */

export interface OHLCV {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

function sma(prices: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      const slice = prices.slice(i - period + 1, i + 1);
      result.push(slice.reduce((a, b) => a + b, 0) / period);
    }
  }
  return result;
}

function ema(prices: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i === 0) {
      result.push(prices[0]);
    } else {
      result.push(prices[i] * k + result[i - 1] * (1 - k));
    }
  }
  return result;
}

function rsi(prices: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = [];
  let gains = 0;
  let losses = 0;
  for (let i = 1; i <= period; i++) {
    const change = prices[i] - prices[i - 1];
    if (change > 0) gains += change;
    else losses -= change;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = 0; i < prices.length; i++) {
    if (i < period) {
      result.push(null);
      continue;
    }
    if (i > period) {
      const change = prices[i] - prices[i - 1];
      const gain = change > 0 ? change : 0;
      const loss = change < 0 ? -change : 0;
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
    }
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result.push(100 - 100 / (1 + rs));
  }
  return result;
}

function macd(
  prices: number[]
): { macd: number[]; signal: number[]; histogram: number[] } {
  const ema12 = ema(prices, 12);
  const ema26 = ema(prices, 26);
  const macdLine = ema12.map((v, i) => v - ema26[i]);
  const signalLine = ema(macdLine, 9);
  const histogram = macdLine.map((v, i) => v - signalLine[i]);
  return { macd: macdLine, signal: signalLine, histogram };
}

function atr(ohlc: { h: number; l: number; c: number }[], period = 14): (number | null)[] {
  const trs: number[] = [];
  for (let i = 0; i < ohlc.length; i++) {
    if (i === 0) {
      trs.push(ohlc[i].h - ohlc[i].l);
    } else {
      const tr1 = ohlc[i].h - ohlc[i].l;
      const tr2 = Math.abs(ohlc[i].h - ohlc[i - 1].c);
      const tr3 = Math.abs(ohlc[i].l - ohlc[i - 1].c);
      trs.push(Math.max(tr1, tr2, tr3));
    }
  }
  return sma(trs, period);
}

function bollinger(
  prices: number[],
  period = 20,
  mult = 2
): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  const mid = sma(prices, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      upper.push(null);
      lower.push(null);
    } else {
      const slice = prices.slice(i - period + 1, i + 1);
      const mean = slice.reduce((a, b) => a + b, 0) / period;
      const std = Math.sqrt(slice.reduce((sq, n) => sq + (n - mean) ** 2, 0) / period);
      upper.push(mean + mult * std);
      lower.push(mean - mult * std);
    }
  }
  return { upper, middle: mid, lower };
}

export interface TechIndicators {
  sma20: (number | null)[];
  sma60: (number | null)[];
  rsi14: (number | null)[];
  macdLine: number[];
  macdSignal: number[];
  macdHistogram: number[];
  atr14: (number | null)[];
  bollUpper: (number | null)[];
  bollMiddle: (number | null)[];
  bollLower: (number | null)[];
}

export function computeIndicators(ohlcv: OHLCV[]): {
  indicators: TechIndicators;
  latest: Record<string, number | null>;
} {
  const closes = ohlcv.map((d) => d.close);
  const ohl = ohlcv.map((d) => ({ h: d.high, l: d.low, c: d.close }));

  const sma20 = sma(closes, 20);
  const sma60 = sma(closes, 60);
  const rsi14 = rsi(closes, 14);
  const macdResult = macd(closes);
  const atr14 = atr(ohl, 14);
  const boll = bollinger(closes, 20, 2);

  const last = (arr: (number | null)[]) => arr[arr.length - 1] ?? null;

  return {
    indicators: {
      sma20,
      sma60,
      rsi14,
      macdLine: macdResult.macd,
      macdSignal: macdResult.signal,
      macdHistogram: macdResult.histogram,
      atr14,
      bollUpper: boll.upper,
      bollMiddle: boll.middle,
      bollLower: boll.lower,
    },
    latest: {
      close: last(closes.map((c) => c)),
      sma20: last(sma20),
      sma60: last(sma60),
      rsi14: last(rsi14),
      macd: last(macdResult.macd.map((m) => m)),
      macdSignal: last(macdResult.signal.map((s) => s)),
      macdHistogram: last(macdResult.histogram.map((h) => h)),
      atr14: last(atr14),
      bollUpper: last(boll.upper),
      bollMiddle: last(boll.middle),
      bollLower: last(boll.lower),
    },
  };
}

export function formatPriceData(ohlcv: OHLCV[], maxRows = 60): string {
  const recent = ohlcv.slice(-maxRows);
  return recent
    .map(
      (d) =>
        `${d.date},${d.open.toFixed(2)},${d.high.toFixed(2)},${d.low.toFixed(2)},${d.close.toFixed(2)},${d.volume}`
    )
    .join("\n");
}

export function formatIndicators(ind: TechIndicators, ohlcv: OHLCV[]): string {
  const n = ohlcv.length;
  const start = Math.max(0, n - 30);
  const rows: string[] = [];
  for (let i = start; i < n; i++) {
    const vals = [
      ohlcv[i].date,
      ind.sma20[i] !== null ? (ind.sma20[i] as number).toFixed(2) : "-",
      ind.sma60[i] !== null ? (ind.sma60[i] as number).toFixed(2) : "-",
      ind.rsi14[i] !== null ? (ind.rsi14[i] as number).toFixed(2) : "-",
      ind.macdHistogram[i].toFixed(3),
      ind.atr14[i] !== null ? (ind.atr14[i] as number).toFixed(2) : "-",
    ];
    rows.push(vals.join(","));
  }
  return "date,sma20,sma60,rsi,macd_hist,atr\n" + rows.join("\n");
}
