import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, BarChart3, Globe, Zap, Shield, Target, Scale } from "lucide-react";

interface ReportViewerProps {
  data: {
    commodity: string;
    tradeDate: string;
    technicalReport: string | null;
    supplyDemandReport: string | null;
    macroReport: string | null;
    geopoliticalReport: string | null;
    investmentPlan: string | null;
    traderPlan: string | null;
    finalDecision: string | null;
    rawData?: any;
    status: string | null;
  };
}

function extractRating(text: string): { rating: string; color: string } {
  const lower = text.toLowerCase();
  if (lower.includes("buy") && !lower.includes("underweight") && !lower.includes("sell")) {
    if (lower.includes("overweight")) return { rating: "OVERWEIGHT", color: "bg-green-600" };
    return { rating: "BUY", color: "bg-emerald-600" };
  }
  if (lower.includes("sell")) {
    if (lower.includes("underweight")) return { rating: "UNDERWEIGHT", color: "bg-orange-600" };
    return { rating: "SELL", color: "bg-red-600" };
  }
  return { rating: "HOLD", color: "bg-yellow-500" };
}

export function ReportViewer({ data }: ReportViewerProps) {
  const { rating, color } = extractRating(data.finalDecision || "");

  const reports = [
    {
      title: "Technical Analysis",
      icon: <BarChart3 className="h-4 w-4" />,
      content: data.technicalReport,
      border: "border-l-blue-500",
    },
    {
      title: "Supply & Demand",
      icon: <Zap className="h-4 w-4" />,
      content: data.supplyDemandReport,
      border: "border-l-amber-500",
    },
    {
      title: "Macro Analysis",
      icon: <Globe className="h-4 w-4" />,
      content: data.macroReport,
      border: "border-l-purple-500",
    },
    {
      title: "Geopolitical Risk",
      icon: <Shield className="h-4 w-4" />,
      content: data.geopoliticalReport,
      border: "border-l-red-500",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">
            {data.commodity} Analysis
          </h1>
          <p className="text-sm text-muted-foreground">
            Trade Date: {data.tradeDate}
          </p>
        </div>
        {data.status === "completed" && (
          <Badge className={`${color} text-white px-4 py-1.5 text-sm font-bold`}>
            {rating === "BUY" && <TrendingUp className="mr-1 h-4 w-4" />}
            {rating === "SELL" && <TrendingDown className="mr-1 h-4 w-4" />}
            {rating === "HOLD" && <Minus className="mr-1 h-4 w-4" />}
            {rating}
          </Badge>
        )}
      </div>

      {/* Raw data summary */}
      {data.rawData && (
        <Card className="bg-muted/50">
          <CardContent className="py-3">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
              <span>Latest: {data.rawData.priceSummary}</span>
              <span>Macro: {data.rawData.macroSummary}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analyst Reports */}
      <div className="grid gap-4 md:grid-cols-2">
        {reports.map((r) => (
          <Card key={r.title} className={`border-l-4 ${r.border}`}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                {r.icon}
                {r.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="prose dark:prose-invert prose-sm max-h-80 overflow-y-auto max-w-none">
              {r.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {r.content}
                </ReactMarkdown>
              ) : (
                <p className="text-muted-foreground">No report available.</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Investment Plan */}
      {data.investmentPlan && (
        <Card className="border-l-4 border-l-indigo-500">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4" />
              Research Manager Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="prose dark:prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {data.investmentPlan}
            </ReactMarkdown>
          </CardContent>
        </Card>
      )}

      {/* Trader Plan */}
      {data.traderPlan && (
        <Card className="border-l-4 border-l-cyan-500">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Scale className="h-4 w-4" />
              Trader Proposal
            </CardTitle>
          </CardHeader>
          <CardContent className="prose dark:prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {data.traderPlan}
            </ReactMarkdown>
          </CardContent>
        </Card>
      )}

      {/* Final Decision */}
      {data.finalDecision && (
        <Card className="border-2 border-primary">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Scale className="h-5 w-5" />
              Final Portfolio Decision
            </CardTitle>
          </CardHeader>
          <CardContent className="prose dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {data.finalDecision}
            </ReactMarkdown>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
