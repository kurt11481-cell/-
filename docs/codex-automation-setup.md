# Codex Automation Setup: Morning Tactical Opportunity Radar

## Intended configuration

- Name: `Morning Tactical Opportunity Radar`
- Platform: Codex automation only
- Schedule: Tuesday through Saturday at 07:45 `Asia/Seoul`
- Workspace: `E:\사업\##금동한\코덱스저장소`
- Windows Task Scheduler: not installed and not permitted by this design

The automation must use the exact prompt in
`stock-strategy-system/TACTICAL_RADAR_AUTOMATION_PROMPT_EN.md`.

## Manual fallback

Current API result: `CODEX_AUTOMATION_REQUIRES_MANUAL_SETUP`. This task already
has the active `미국 주식 매매시점 점검` heartbeat, and the Codex surface
permits only one heartbeat per task. The existing 07:30 holding-risk automation
was intentionally left unchanged; a cron or Windows scheduler workaround was
not created.

If native Codex automation creation is unavailable:

1. Open Codex Automations.
2. Create a recurring heartbeat named `Morning Tactical Opportunity Radar`.
3. Set the schedule to Tuesday through Saturday at 07:45 in the
   `Asia/Seoul` timezone.
4. Select the workspace `E:\사업\##금동한\코덱스저장소`.
5. Paste the complete content of
   `stock-strategy-system/TACTICAL_RADAR_AUTOMATION_PROMPT_EN.md` as the
   automation prompt.
6. Keep notification preferences outside the prompt.
7. Do not install or invoke Windows Task Scheduler.

After setup, the first valid run must verify the latest completed official U.S.
session, preserve `quantity=null`, write only tactical runtime/audit artifacts,
and explicitly report that no order was placed or scheduled.
