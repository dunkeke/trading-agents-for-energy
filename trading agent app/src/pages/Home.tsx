import { ApiConfigForm } from "@/components/ApiConfigForm";
import { AnalysisRunner } from "@/components/AnalysisRunner";
import { HistoryList } from "@/components/HistoryList";
import { Flame, TrendingUp, BarChart3 } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Flame className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">
                EnergyTradingAgents
              </h1>
              <p className="text-xs text-muted-foreground">
                Multi-Agent LLM Energy Commodity Analysis Engine
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-4 text-sm text-muted-foreground sm:flex">
            <div className="flex items-center gap-1">
              <BarChart3 className="h-4 w-4" />
              DeepSeek API
            </div>
            <div className="flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              yfinance Data
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-4 py-6">
        {/* Pipeline Overview */}
        <div className="mb-6 rounded-lg border bg-card p-4">
          <h2 className="mb-2 text-sm font-semibold text-muted-foreground">
            ANALYSIS PIPELINE
          </h2>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {[
              "Technical Analyst",
              "Supply/Demand Analyst",
              "Macro Analyst",
              "Geopolitical Analyst",
              "Bull/Bear Debate",
              "Research Manager",
              "Trader",
              "Risk Debate",
              "Portfolio Manager",
            ].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                  {step}
                </span>
                {i < 8 && (
                  <span className="text-muted-foreground">→</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column: Config + Runner */}
          <div className="space-y-6 lg:col-span-1">
            <ApiConfigForm />
            <AnalysisRunner />
          </div>

          {/* Right Column: History */}
          <div className="lg:col-span-2">
            <HistoryList />
          </div>
        </div>
      </main>
    </div>
  );
}
