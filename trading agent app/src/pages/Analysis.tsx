import { useParams, useNavigate } from "react-router";
import { trpc } from "@/providers/trpc";
import { ReportViewer } from "@/components/ReportViewer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, AlertCircle } from "lucide-react";

export default function Analysis() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const analysisId = parseInt(id || "0", 10);

  const analysisQuery = trpc.analysis.get.useQuery(
    { id: analysisId },
    { enabled: analysisId > 0 }
  );

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/")}
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-xl font-bold">Analysis Report</h1>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {analysisQuery.isLoading && (
          <div className="space-y-4">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {analysisQuery.isError && (
          <div className="flex flex-col items-center justify-center py-12 text-red-600">
            <AlertCircle className="mb-2 h-8 w-8" />
            <p>Failed to load analysis report.</p>
            <p className="text-sm text-muted-foreground">
              {analysisQuery.error?.message}
            </p>
          </div>
        )}

        {analysisQuery.data && (
          <ReportViewer data={analysisQuery.data} />
        )}
      </main>
    </div>
  );
}
