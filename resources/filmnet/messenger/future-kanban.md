# Messenger Future Kanban

Use only when designing Option C or durable Messenger jobs. Do not load for normal send/reply work.

## Option C: JSONL plus Kanban later

Implement only after Option A is stable.

Use Kanban for durable Messenger jobs such as:
- send approved message and track reply until a deadline
- follow up when no reply is received
- escalate failed delivery
- summarize pending communication status

Keep JSONL as the canonical event layer. Kanban should reference JSONL request/event IDs instead of replacing the event log.

## Boundary

Kanban can coordinate work, deadlines, and retries, but Messenger safety rules remain unchanged:
- no sending without `approval_status: approved_by_farzan`
- no recipient selection by Messenger
- no rewriting approved content
- no recipient text entering Hermes as an agent-control prompt
