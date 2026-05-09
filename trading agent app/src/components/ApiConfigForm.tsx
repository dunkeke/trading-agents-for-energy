import { useState } from "react";
import { trpc } from "@/providers/trpc";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { KeyRound, CheckCircle, AlertCircle } from "lucide-react";

export function ApiConfigForm() {
  const utils = trpc.useUtils();
  const configQuery = trpc.config.get.useQuery();
  const upsertMutation = trpc.config.upsert.useMutation({
    onSuccess: () => {
      utils.config.get.invalidate();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [deepModel, setDeepModel] = useState("deepseek-chat");
  const [quickModel, setQuickModel] = useState("deepseek-chat");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    if (!apiKey.trim()) return;
    upsertMutation.mutate({
      apiKey: apiKey.trim(),
      baseUrl,
      deepModel,
      quickModel,
    });
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <KeyRound className="h-5 w-5" />
          DeepSeek API Configuration
        </CardTitle>
        <CardDescription>
          Configure your DeepSeek API key to run energy commodity analysis.
          Supports any OpenAI-compatible endpoint.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {configQuery.data?.hasKey && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-400">
            <CheckCircle className="h-4 w-4" />
            API key configured (provider: {configQuery.data.provider})
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="api-key">API Key</Label>
          <Input
            id="api-key"
            type="password"
            placeholder="sk-xxxxxxxxxxxxxxxx"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="base-url">Base URL</Label>
          <Input
            id="base-url"
            placeholder="https://api.deepseek.com"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Default: https://api.deepseek.com. Change for other OpenAI-compatible endpoints.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="deep-model">Deep Model</Label>
            <Input
              id="deep-model"
              value={deepModel}
              onChange={(e) => setDeepModel(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="quick-model">Quick Model</Label>
            <Input
              id="quick-model"
              value={quickModel}
              onChange={(e) => setQuickModel(e.target.value)}
            />
          </div>
        </div>

        {upsertMutation.error && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            {upsertMutation.error.message}
          </div>
        )}

        {saved && (
          <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-400">
            <CheckCircle className="h-4 w-4" />
            Configuration saved successfully!
          </div>
        )}

        <Button
          onClick={handleSave}
          disabled={!apiKey.trim() || upsertMutation.isPending}
          className="w-full"
        >
          {upsertMutation.isPending ? "Saving..." : "Save Configuration"}
        </Button>
      </CardContent>
    </Card>
  );
}
