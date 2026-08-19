# Flask Server-Driven Runtime — Master Tasks

## Foundation
- ✅ layered application factory / blueprints / services
- ✅ SQLAlchemy models separated from routes
- ✅ environment configuration
- ✅ mobile-first Arabic RTL control plane
- ✅ audit logging foundation

## Runtime
- ✅ versioned immutable releases
- ✅ /runtime/bootstrap
- ✅ /runtime/manifest
- ✅ /runtime/resources
- ✅ /runtime/sync
- ✅ /runtime/events/ack
- ✅ /runtime/devices/register
- ✅ WebSocket boundary registered at app startup
- ✅ managed Data API: list/create/read/update/patch/delete
- ✅ record version/checksum + optimistic conflict responses

## UI / STAC
- ✅ full raw STAC screen editing
- ✅ routing/home/login metadata
- ⬜ visual drag/drop builder
- ⬜ reusable component library

## Actions / Workflows
- ✅ server-defined actions
- ✅ server-defined workflows
- ✅ action permission field
- ⬜ workflow validator/compiler
- ⬜ idempotency/compensation engine
- ⬜ action test runner

## Data Plane
- ✅ managed Data Models
- ✅ managed Data Records
- ✅ version/checksum
- ✅ query + pagination API
- ✅ schema required/type validation foundation
- ⬜ advanced filter/sort/query DSL
- ⬜ schema migration UI

## API Gateway
- ✅ API profiles
- ✅ endpoint definitions
- ✅ host allowlist + TLS policy
- ⬜ connectivity tester UI
- ⬜ secret vault
- ⬜ rate limiting

## Extensibility
- ✅ Code Assets storage
- ✅ stored_only execution policy
- ⬜ signed handler registry
- ⬜ sandboxed handlers

## Realtime
- ✅ persisted events
- ✅ websocket route registered
- ✅ websocket ACK handling foundation
- ✅ device token registration
- ⬜ broker/pubsub
- ⬜ FCM/APNs server delivery

## Security / Quality
- ✅ no .env tracked
- ✅ outbound proxy restrictions
- 🟡 CSRF protection
- ⬜ rate limiting
- 🟡 comprehensive Flutter contract suite
- ⬜ production deployment CI/CD
- ⬜ database migration scripts / schema upgrade policy

## Next verification gate
1. GitHub Actions: compileall + pytest must pass on the latest head.
2. Verify Runtime bootstrap → manifest → resources → data CRUD → sync → event ACK.
3. Connect this backend to the existing Flutter Runtime using the versioned endpoints.
4. Then add advanced admin builders, API connectivity tester, workflow validator and production security/deployment hardening.
