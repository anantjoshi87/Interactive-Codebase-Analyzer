                           ┌────────────────────┐
                           │       USERS        │
                           ├────────────────────┤
                           │ PK id (Clerk ID)   │
                           │ email              │
                           │ createdAt          │
                           └─────────┬──────────┘
                                     │
                             1       │       N
                                     │
                                     ▼
                      ┌──────────────────────────┐
                      │       WORKSPACES         │
                      ├──────────────────────────┤
                      │ PK id (LangGraph Thread) │
                      │ title                    │
                      │ createdAt                │
                      │ updatedAt                │
                      │ FK userId               │────────────┐
                      │ FK repoId               │            │
                      └──────────┬──────────────┘            │
                                 │                           │
                         1       │       N                   │
                                 ▼                           │
                    ┌────────────────────────┐               │
                    │       MESSAGES         │               │
                    ├────────────────────────┤               │
                    │ PK id                  │               │
                    │ FK workspaceId         │               │
                    │ role                   │               │
                    │ content                │               │
                    │ createdAt              │               │
                    └────────────────────────┘               │
                                                             │
                                                             │
                                                             │
                       ┌────────────────────────────┐         │
                       │      REPOSITORIES          │◄────────┘
                       ├────────────────────────────┤
                       │ PK id                      │
                       │ githubUrl                  │
                       │ latestCommit               │
                       │ createdAt                  │
                       └──────┬───────────┬─────────┘
                              │           │
                     1         │           │        1
                              ▼           ▼
              ┌────────────────────┐   ┌────────────────────┐
              │ REPOSITORY_INDEXES │   │    GRAPH_CACHES    │
              ├────────────────────┤   ├────────────────────┤
              │ PK id              │   │ PK id              │
              │ FK repositoryId    │   │ FK repositoryId    │
              │ embeddingModel     │   │ nodesJson          │
              │ parserVersion      │   │ edgesJson          │
              │ status             │   │ generatedAt        │
              │ totalChunks        │   └────────────────────┘
              │ totalNodes         │
              │ totalEdges         │
              │ indexedCommit      │
              │ indexedAt          │
              └────────────────────┘





Relationship Summary
Parent	    Child	        Relationship	Why?
User	    Workspace	    1 → Many	A user can analyze many repositories or create multiple chats.
Repository	Workspace	    1 → Many	Many workspaces (even from different users) can use the same indexed repository.
Workspace	Message	        1 → Many	One conversation contains many messages.
Repository	RepositoryIndex	1 → 1	    One current indexing state per repository.
Repository	GraphCache	    1 → 1	    One cached React Flow graph per repository.