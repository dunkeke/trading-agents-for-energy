import { z } from "zod";
import { createRouter, publicQuery } from "../middleware";
import { getDb } from "../queries/connection";
import { analyses, apiConfigs } from "@db/schema";
import { eq, desc } from "drizzle-orm";
import { runAnalysis } from "../lib/analysis-engine";

export const analysisRouter = createRouter({
  list: publicQuery.query(async () => {
    const db = getDb();
    return db
      .select({
        id: analyses.id,
        commodity: analyses.commodity,
        tradeDate: analyses.tradeDate,
        status: analyses.status,
        finalDecision: analyses.finalDecision,
        createdAt: analyses.createdAt,
      })
      .from(analyses)
      .orderBy(desc(analyses.createdAt))
      .limit(100);
  }),

  get: publicQuery
    .input(z.object({ id: z.number() }))
    .query(async ({ input }) => {
      const db = getDb();
      const rows = await db
        .select()
        .from(analyses)
        .where(eq(analyses.id, input.id))
        .limit(1);
      return rows[0] ?? null;
    }),

  run: publicQuery
    .input(
      z.object({
        commodity: z.enum(["BRENT", "WTI", "HH", "TTF", "JKM", "LPG"]),
        tradeDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      })
    )
    .mutation(async ({ input }) => {
      const db = getDb();

      // Get API config
      const configs = await db
        .select()
        .from(apiConfigs)
        .orderBy(apiConfigs.id)
        .limit(1);
      if (configs.length === 0) {
        throw new Error(
          "No API config found. Please configure your DeepSeek API key first."
        );
      }
      const config = configs[0];

      // Create analysis record
      const insertResult = await db.insert(analyses).values({
        commodity: input.commodity,
        tradeDate: input.tradeDate,
        status: "running",
      });
      const analysisId = Number(insertResult[0].insertId);

      try {
        const result = await runAnalysis(input.commodity, input.tradeDate, {
          apiKey: config.apiKey,
          baseUrl: config.baseUrl || "https://api.deepseek.com",
          deepModel: config.deepModel || "deepseek-chat",
          quickModel: config.quickModel || "deepseek-chat",
        });

        await db
          .update(analyses)
          .set({
            status: "completed",
            technicalReport: result.technicalReport,
            supplyDemandReport: result.supplyDemandReport,
            macroReport: result.macroReport,
            geopoliticalReport: result.geopoliticalReport,
            investmentPlan: result.investmentPlan,
            traderPlan: result.traderPlan,
            finalDecision: result.finalDecision,
            rawData: result.rawData as any,
            updatedAt: new Date(),
          })
          .where(eq(analyses.id, analysisId));

        return { success: true, id: analysisId };
      } catch (err: any) {
        await db
          .update(analyses)
          .set({
            status: "failed",
            finalDecision: `Error: ${err.message || "Unknown error"}`,
            updatedAt: new Date(),
          })
          .where(eq(analyses.id, analysisId));
        throw err;
      }
    }),
});
