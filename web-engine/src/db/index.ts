// src/db/index.ts
import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import * as schema from "./schema"; // Import the Drizzle schema we created earlier

// Ensure the environment variable exists
if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL is missing in environment variables");
}

// 1. Initialize the Neon HTTP connection
const sql = neon(process.env.DATABASE_URL);

// 2. Wrap it with Drizzle and pass the schema for type-safe queries
export const db = drizzle(sql, { schema });
