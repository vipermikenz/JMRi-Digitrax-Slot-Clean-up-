# README.md — Freemo Digitrax Slot Recycler (JMRI Jython)

This repo contains a JMRI Jython script that helps prevent Digitrax "Slot=Max" failures during large operating sessions (e.g., Freemo) by automatically reclaiming truly abandoned locomotives and consists.

It does this by periodically sending **dispatch** (preferred) and optional **release** LocoNet messages back to the Digitrax command station for idle slots.

## What this does (and what it does not)

### It does
- Reclaim **idle** locomotives and (optionally) consists that have been stopped and untouched for longer than a timeout.
- Reduce slot pressure without needing a command station reset mid-session.
- Log every action so operators can audit what happened.

### It does NOT
- "Delete" slots from the Digitrax command station instantly.
- Force the slot list to visually shrink in real-time.
- Replace operator discipline (Stop -> Dispatch -> Disconnect).

Digitrax slots are managed in the command station firmware; JMRI can only request that slots be dispatched/released so they become eligible for reuse.

## Freemo ops rule (plain English)

**Purpose**
Keep the Digitrax slot table from filling during big sessions and avoid Slot=Max failures.

**Normal operator behaviour**
1. Bring speed to **0** when finished.
2. **Dispatch/Release** your loco/consist in your throttle app before disconnecting.

**Automatic clean-up (safety net)**
- Any loco or consist that is:
  - at **speed 0**, and
  - has had **no activity** for more than **N minutes**
  may be automatically dispatched to free resources.

**No activity means**
- No speed or direction changes
- No function activity (lights/horn etc.), if tracked
- No re-acquire/reconnect touch

If any activity occurs, the timer resets.

**Consists**
- A consist is only cleaned up if **all members are speed 0** and the **entire consist** has been inactive longer than the consist timeout.

**Protection**
- Addresses listed in `protected_addresses.txt` are never touched.

## Running in JMRI (live)

### 1) Install
- Copy `FreemoSlotRecycler.py` to a known folder.
- In JMRI:
  - Preferences -> Startup -> Add -> Run Script
  - select `FreemoSlotRecycler.py`
- Restart JMRI.

### 2) Safety first
Start with:
- `DRY_RUN = True`
- `INCLUDE_HANDHELD_THROTTLES = False`

Run a session, review the log, then enable sending and/or include handheld throttles if your ops rule allows reclaiming any idle slot after N minutes.

### 3) Recommended settings for Freemo
- Scan interval: 60 seconds
- Idle timeout (single locos): 5–10 minutes
- Idle timeout (consists): 10–15 minutes (safer)
- Mode: dispatch then release fallback
- Protected list enabled
- Logging enabled

## Testing without a layout (simulation)

Because Digitrax slots live in the command station, JMRI can’t load a fake slot table from CSV into the real Slot Monitor.

Instead, this repo provides a simple **offline simulation** approach:

- `sample_slots.csv` is a repeatable snapshot of a "slot table"
- A simulator script (optional) can read the CSV and print what the recycler *would* dispatch/release

### CSV simulation workflow (recommended for GitHub CI)
1. Edit `sample_slots.csv` to represent scenarios:
   - 5 active locos (speed > 0)
   - 5 idle locos (speed = 0, old lastActivity)
   - optionally an idle consist
2. Run your simulator (or just review expected behaviour).
3. Confirm the recycler chooses the right candidates.

This is purely for validating decision logic; it does not generate real LocoNet traffic.

## Files

- `FreemoSlotRecycler.py`  
  The JMRI Jython script (startup + periodic scan + dispatch/release + optional consists).

- `sample_slots.csv`  
  A sample slot-table fixture for offline testing.

- `protected_addresses.txt`  
  One DCC address per line. Those addresses are never touched.

## Licence

Recommended: MIT licence (simple, permissive). Add a `LICENSE` file if publishing publicly.

## Disclaimer

If you enable "include handheld throttles", this tool can reclaim slots from real operators who pause longer than your timeout. Only enable that if the operating group explicitly agrees to the rule.
