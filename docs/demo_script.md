# AutoHeal EvidenceFirst — 4-Minute Demo Script
**CTRL+AI Challenge PS-12 Auto-Heal**

## Roles
- **Speaker (Lead)**: Delivers problem context, explains hypotheses formulation, and presents postmortem findings.
- **Operator**: Controls chaos injections, clicks "Investigate", reviews approval card, and executes approvals.
- **Backup**: Monitors console logs and prepares to switch to fallback policy if offline.

---

## Act 1: The Cold Cache Outage (60 seconds)
1. **Operator**: In sidebar, click **Cache Outage**.
2. **Speaker**:
   > "At 02:00 UTC, a spike in orders_api 503 errors and 2,400ms latency triggers an alert. Watch the mission control board formulate three competing hypotheses in real-time."
3. **Operator**: Click **Investigate & Auto-Heal**.
4. **Speaker**:
   > "AutoHeal begins with read-only diagnostics: querying metrics, pinging dependencies, and checking database health. It confirms Redis is unreachable and immediately eliminates the database pool hypothesis. It applies the reversible fix `restart_cache`, verifies recovery over 3 consecutive passes, and writes the postmortem to incident memory."

---

## Act 2: Memory-Accelerated Repeat Outage (45 seconds)
1. **Operator**: In sidebar, click **Cache Outage** a second time.
2. **Speaker**:
   > "Suppose the issue recurs. AutoHeal queries its incident memory and recognizes the exact symptom signature `orders_api_errors|cache_unreachable|worker_queue_high`."
3. **Operator**: Click **Investigate & Auto-Heal**.
4. **Speaker**:
   > "Notice how AutoHeal retrieves the prior runbook, conducts ONE confirmation check, and executes the fix immediately. Notice the Plotly comparison chart: recovery time dropped by over 60% with half the diagnostic steps."

---

## Act 3: Bad Config & Human Approval Gate (75 seconds)
1. **Operator**: In sidebar, click **Bad Config**.
2. **Speaker**:
   > "Deployment v2.4.1 just shipped, and orders_api is in a CrashLoopBackOff with a 100% error rate."
3. **Operator**: Click **Investigate & Auto-Heal**.
4. **Speaker**:
   > "AutoHeal inspects the configuration diff and spots that `DATABASE_URL` was dropped. Because rolling back a deployment carries production impact, AutoHeal encounters our code-enforced safety gate. It pauses in `AWAITING_APPROVAL`."
5. **Operator**: Point to the amber Approval Card detailing cause, confidence (98%), proposed action, and rollback plan. Click **Approve Proposed Rollback**.
6. **Speaker**:
   > "With supervisor sign-off, AutoHeal restores v2.4.0, runs 3-pass verification, and resolves the outage."

---

## Act 4: Database Integrity Fault & Supervised Escalation (60 seconds)
1. **Operator**: In sidebar, click **DB Integrity**.
2. **Speaker**:
   > "Our final test: a corrupted disk block generates a checksum failure on the orders table. The agent sees this critical issue."
3. **Operator**: Click **Investigate & Auto-Heal**.
4. **Speaker**:
   > "AutoHeal's prompt might want to fix it, but our Python guardrail strictly blocks `repair_database`. Notice the red timeline entry: 'BLOCKED by code policy'. AutoHeal immediately escalates, paging human on-call with a complete evidence packet, logs snapshot, and recommended PITR restore steps. No repair button is offered to the machine."
