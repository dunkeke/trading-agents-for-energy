import { useNavigate } from "react-router";
import { trpc } from "@/providers/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Clock, BarChart3 } from "lucide-react";

const COMMODITY_LABELS: Record<string, string> = {
  BRENT: "Brent Crude",
  WTI: "WTI Crude",
  HH: "Henry Hub",
  TTF: "TTF Gas",
  JKM: "JKM LNG",
  LPG: "LPG",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

export function HistoryList() {
  const navigate = useNavigate();
  const listQuery = trpc.analysis.list.useQuery();

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Clock className="h-5 w-5" />
          Analysis History
        </CardTitle>
      </CardHeader>
      <CardContent>
        {listQuery.isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )}

        {listQuery.data && listQuery.data.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <BarChart3 className="mb-2 h-8 w-8 opacity-50" />
            <p className="text-sm">No analyses yet. Run your first analysis above.</p>
          </div>
        )}

        {listQuery.data && listQuery.data.length > 0 && (
          <ScrollArea className="h-[400px]">
            <div className="space-y-2">
              {listQuery.data.map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(`/analysis/${item.id}`)}
                  className="flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors hover:bg-muted"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-semibold text-primary">
                      {COMMODITY_LABELS[item.commodity] || item.commodity}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {item.tradeDate}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={STATUS_COLORS[item.status || "pending"] || ""}
                    >
                      {item.status}
                    </Badge>
                  </div>
                </button>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
