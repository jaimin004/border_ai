# BORDER-AI — Security & Privacy Design Notes

**Status: design document only.** Nothing described here is implemented in the
hackathon prototype — this exists so the security architecture is fully
thought through and can be presented honestly to judges as "designed for,"
not "built." Implementing real authentication, TLS termination, and a
production audit-log store is out of scope for a 1–2 week build; the goal
here is to show the platform was architected with these requirements in
mind from the start, not bolted on as an afterthought.

---

## 1. Role-Based Access Control (RBAC)

Four roles, matching the report's Section 12. Each role is scoped to what
that person actually needs to do their job — nobody gets more access than
their function requires.

| Role | Can do | Cannot do |
|---|---|---|
| **Admin** | Full system configuration: add/remove cameras, define restricted zones, manage user accounts and role assignments, set risk-score thresholds, add/remove watchlist entries | Nothing restricted — but every admin action is logged (see Section 3) precisely because this role is the most powerful |
| **Operator** | View live camera feeds and the event dashboard, acknowledge/dismiss alerts, trigger event replay, view evidence for events they're actively working | Cannot change zone definitions, cannot add/remove watchlist entries, cannot access raw unmasked footage outside of an active event review, cannot manage user accounts |
| **Supervisor** | Everything an Operator can do, plus: review dismissed/closed alerts, view aggregate KPI/analytics dashboards, approve watchlist additions proposed by an Admin | Cannot change system-level configuration (zones, camera onboarding, thresholds) — that stays with Admin to keep a separation between "who watches the system" and "who configures it" |
| **Auditor** | Read-only access to the audit log and historical event records, for compliance and after-action review | Cannot view live feeds, cannot acknowledge or act on alerts, cannot modify anything — this role exists purely for independent oversight, which only works if it has no operational power |

**Why this split matters:** the Operator/Supervisor/Admin separation means a
single compromised or careless account can't silently reconfigure the
system's sensitivity or remove someone from a watchlist — that requires
Admin access specifically, which should be the smallest, most tightly
controlled group of accounts.

---

## 2. Where TLS fits in the architecture

Every network hop in the pipeline is a place data could be intercepted if
left unencrypted, so TLS is planned at each of these boundaries:

- **Edge node → central server**: event metadata, snapshots, and short
  evidence clips are synchronized over TLS, not plain HTTP. This matters
  even more given the low-bandwidth/offline design (Section 11 of the main
  report) — batched sync traffic after a period offline is exactly the kind
  of traffic worth protecting, since it may contain a backlog of sensitive
  evidence.
- **Dashboard ↔ backend API**: the React dashboard talks to FastAPI over
  HTTPS only. No operator credential, session token, or event data should
  ever cross the network in plaintext.
- **Any external integration** (a future Vahan/CCTNS lookup, for example):
  TLS is non-negotiable here regardless of whether the integration itself
  is live yet, since these would carry the most sensitive data in the
  system.

Camera-to-edge-node traffic (RTSP from existing CCTV hardware) is the one
segment that may not support TLS at all, since it depends on the existing,
already-deployed camera hardware — this is a real, acknowledged limitation
of working with legacy infrastructure, not an oversight. Where the
camera hardware doesn't support encrypted streaming, that segment stays
within a physically controlled, trusted network segment at the outpost, and
TLS begins at the edge node's outbound connection instead.

---

## 3. Audit logging

Every action that changes system state or accesses sensitive data gets
logged, following the same "who, did what, when, from where" structure
described in the report:

- **Who**: the authenticated user ID and role
- **Did what**: the specific action (e.g. `zone_updated`, `watchlist_entry_added`,
  `alert_dismissed`, `evidence_viewed`)
- **When**: timestamp, same UTC ISO format as the event schema
- **From where**: originating IP/device, and which camera or event the
  action relates to, where applicable

Audit entries are treated as append-only — they are never edited or
deleted through the normal application, which is what makes them useful
as an actual record rather than just another log a compromised account
could quietly rewrite. A believable production version of this would use
a write-once store or the hash-chaining approach mentioned in the report's
future roadmap (Section on tamper-evident evidence logging), but for the
prototype, an audit entry is simply appended to its own table separate
from the operational event data, and Operators/Supervisors have no delete
permission on it at all — only Auditors and Admins can even read it, and
neither role can write to it directly (writes only happen automatically,
as a side effect of another logged action).

---

## 4. How this connects to what's already built

- `mask_privacy()` (Day 2) is the practical, working half of the
  privacy-by-design principle described here — faces and plates are
  blurred before evidence is stored, regardless of who later views it.
- The `face_match` field in the event schema (Day 1) is deliberately
  structured as a name + confidence, not a raw face image, which limits
  what even an Operator-level account is exposed to during normal alert
  review.
- The `synced` field (reserved Day 1, used from Day 6) is the field an
  audit entry would reference to confirm exactly when a given piece of
  evidence left the edge node and crossed the network boundary described
  in Section 2 above.

This document intentionally stays at the design level. If asked in Q&A,
the honest answer is: "we've architected the RBAC roles, TLS boundaries,
and audit-log structure to match production security requirements, and
implemented the privacy-masking piece directly — full auth and a
production audit store are the next build phase beyond this prototype."
