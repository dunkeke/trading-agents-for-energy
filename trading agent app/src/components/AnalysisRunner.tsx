import { useState } from "react";
import { useNavigate } from "react-router";
import { trpc } from "@/providers/trpc";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Activity, AlertCircle, Loader2 } from "lucide-react";

const COMMODITIES = [
  { value: "BRENT", label: "Brent Crude Oil (BZ=F)", icon: "🛢️" },
  { value: "WTI", label: "WTI Crude Oil (CL=F)", icon: "🛢️" },
  { value: "HH", label: "Henry Hub Natural Gas (NG=F)", icon: "🔥" },
  { value: "TTF", label: "TTF Dutch Gas (TTF=F)", icon: "🔥" },
  { value: "JKM", label: "JKM LNG Marker (JKM=F)", icon: "🚢" },
  { value: "LPG", label: "LPG (LPG=F)", icon: "⛽" },
];

export function AnalysisRunner() {
  const navigate = useNavigate();
  const utils = trpc.useUtils();
  const configQuery = trpc.config.get.useQuery();

  const [commodity, setCommodity] = useState("BRENT");
  const [tradeDate, setTradeDate] = useState(
    new Date(Date.now() - 86400000).toISOString().split("T")[0]
  );
  const [progress, setProgress] = useState(0);

  const runMutation = trpc.analysis.run.useMutation({
    onSuccess: (data) => {
      setProgress(100);
      utils.analysis.list.invalidate();
      setTimeout(() => {
        navigate(`/analysis/${data.id}`);
      }, 500);
    },
  });

  const handleRun = () => {
    setProgress(10);
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + 5, 90));
    }, 2000);
    runMutation.mutate(
      { commodity: commodity as any, tradeDate },
      {
        onSettled: () => clearInterval(interval),
      }
    );
  };

  const isConfigured = configQuery.data?.hasKey ?? false;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5" />
          Run Energy Analysis
        </CardTitle>
        <CardDescription>
          Select a commodity and trade date to launch the multi-agent analysis
          pipeline.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConfigured && (
          <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:bg-amber-950 dark:text-amber-400">
            <AlertCircle className="h-4 w-4" />
            Please configure your DeepSeek API key above first.
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="commodity">Commodity</Label>
          <Select value={commodity} onValueChange={setCommodity}>
            <SelectTrigger id="commodity">
              <SelectValue placeholder="Select commodity" />
            </SelectTrigger>
            <SelectContent>
              {COMMODITIES.map((c) => (
                <SelectItem key={c.value} value={c.value}>
                  <span className="mr-2">{c.icon}</span>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="trade-date">Trade Date</Label>
          <Input
            id="trade-date"
            type="date"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
          />
        </div>

        {runMutation.isPending && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Running multi-agent analysis pipeline...
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {runMutation.error && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            {runMutation.error.message}
          </div>
        )}

        <Button
          onClick={handleRun}
          disabled={!isConfigured || runMutation.isPending}
          className="w-full"
        >
          {runMutation.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            "Launch Analysis Pipeline"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
