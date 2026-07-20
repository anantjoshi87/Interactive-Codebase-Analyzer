// src/db/schema.ts
import { relations } from "drizzle-orm";
import {
  pgTable,
  pgEnum,
  text,
  timestamp,
  uuid,
  integer,
  jsonb,
  index,
} from "drizzle-orm/pg-core";

// -----------------------------------------------------------------------------
// TABLE DEFINITIONS
// -----------------------------------------------------------------------------

export const users = pgTable("users", {
  id: text("id").primaryKey(), // Clerk ID (e.g., user_2aZ...)
  email: text("email").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const repositories = pgTable("repositories", {
  id: uuid("id").primaryKey().defaultRandom(),
  githubUrl: text("github_url").notNull().unique(),
  currentCommit: text("current_commit").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const indexingStatusEnum = pgEnum("indexing_status", [
  "pending",
  "processing",
  "completed",
  "failed",
]);

export const repositoryIndexes = pgTable(
  "repository_indexes",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    embeddingModel: text("embedding_model").notNull(),
    parserVersion: text("parser_version").notNull(),
    status: indexingStatusEnum("status").default("pending").notNull(),
    totalChunks: integer("total_chunks").default(0).notNull(),
    totalNodes: integer("total_nodes").default(0).notNull(),
    totalEdges: integer("total_edges").default(0).notNull(),
    indexedAt: timestamp("indexed_at").defaultNow().notNull(),
    repositoryId: uuid("repository_id")
      .notNull()
      .unique()
      .references(() => repositories.id, {
        onDelete: "cascade",
      }),
    indexedCommit: text("indexed_commit").notNull(),
  },
  (table) => [index("repository_id_idx").on(table.repositoryId)],
);

export const workspaces = pgTable(
  "workspaces",
  {
    id: text("id").primaryKey(), // LangGraph thread_id
    title: text("title").notNull(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .defaultNow()
      .$onUpdate(() => new Date()) // Drizzle's equivalent to @updatedAt
      .notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    repoId: uuid("repo_id")
      .notNull()
      .references(() => repositories.id, { onDelete: "cascade" }),
  },
  (table) => [
    index("workspace_user_id_idx").on(table.userId),
    index("workspace_repo_id_idx").on(table.repoId),
  ],
);

export const messages = pgTable(
  "messages",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    role: text("role").notNull(),
    content: text("content").notNull(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
  },
  (table) => [index("message_workspace_id_idx").on(table.workspaceId)],
);

export const graphCaches = pgTable("graph_caches", {
  id: uuid("id").primaryKey().defaultRandom(),
  repositoryId: uuid("repository_id")
    .notNull()
    .unique() // Enforces the 1-to-1 relationship per repo branch
    .references(() => repositories.id, { onDelete: "cascade" }),
  nodesJson: jsonb("nodes_json").notNull(), // jsonb is highly optimized in Postgres
  edgesJson: jsonb("edges_json").notNull(),
  generatedAt: timestamp("generated_at").defaultNow().notNull(),
});

// -----------------------------------------------------------------------------
// RELATIONS (Used for `db.query.users.findMany(...)` capabilities)
// -----------------------------------------------------------------------------

export const usersRelations = relations(users, ({ many }) => ({
  workspaces: many(workspaces),
}));

export const repositoriesRelations = relations(
  repositories,
  ({ many, one }) => ({
    workspaces: many(workspaces),
    index: one(repositoryIndexes),
    graphCache: one(graphCaches), // 1-to-1 based on the unique constraint
  }),
);

export const repositoryIndexesRelations = relations(
  repositoryIndexes,
  ({ one }) => ({
    repository: one(repositories, {
      fields: [repositoryIndexes.repositoryId],
      references: [repositories.id],
    }),
  }),
);

export const workspacesRelations = relations(workspaces, ({ one, many }) => ({
  user: one(users, {
    fields: [workspaces.userId],
    references: [users.id],
  }),
  repository: one(repositories, {
    fields: [workspaces.repoId],
    references: [repositories.id],
  }),
  messages: many(messages),
}));

export const messagesRelations = relations(messages, ({ one }) => ({
  workspace: one(workspaces, {
    fields: [messages.workspaceId],
    references: [workspaces.id],
  }),
}));

export const graphCachesRelations = relations(graphCaches, ({ one }) => ({
  repository: one(repositories, {
    fields: [graphCaches.repositoryId],
    references: [repositories.id],
  }),
}));
