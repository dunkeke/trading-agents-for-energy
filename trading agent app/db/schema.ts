import {
  mysqlTable,
  serial,
  varchar,
  text,
  timestamp,
  json,
} from "drizzle-orm/mysql-core";

export const apiConfigs = mysqlTable("api_configs", {
  id: serial("id").primaryKey(),
  provider: varchar("provider", { length: 32 }).notNull().default("deepseek"),
  apiKey: varchar("api_key", { length: 512 }).notNull(),
  baseUrl: varchar("base_url", { length: 512 }).default("https://api.deepseek.com"),
  deepModel: varchar("deep_model", { length: 64 }).default("deepseek-chat"),
  quickModel: varchar("quick_model", { length: 64 }).default("deepseek-chat"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow().onUpdateNow(),
});

export const analyses = mysqlTable("analyses", {
  id: serial("id").primaryKey(),
  commodity: varchar("commodity", { length: 16 }).notNull(),
  tradeDate: varchar("trade_date", { length: 16 }).notNull(),
  status: varchar("status", { length: 16 }).notNull().default("pending"),
  technicalReport: text("technical_report"),
  supplyDemandReport: text("supply_demand_report"),
  macroReport: text("macro_report"),
  geopoliticalReport: text("geopolitical_report"),
  investmentPlan: text("investment_plan"),
  traderPlan: text("trader_plan"),
  finalDecision: text("final_decision"),
  rawData: json("raw_data"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow().onUpdateNow(),
});
