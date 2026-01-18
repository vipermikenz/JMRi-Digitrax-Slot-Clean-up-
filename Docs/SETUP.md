# SETUP — Freemo Digitrax Slot Recycler (JMRI)

This document explains how to install, configure, test, and safely enable
**FreemoSlotRecycler.py** in JMRI.

The purpose of this script is to reduce Digitrax slot exhaustion during large
operating sessions (e.g. Freemo) by automatically reclaiming *truly idle*
locomotives and consists.

---

## IMPORTANT LIMITATION (READ FIRST)

JMRI’s **LocoNet Simulator does NOT emulate Digitrax slot allocation**.

This means:
- Slot Monitor will remain empty when using the simulator
- Slot recycling behaviour cannot be tested in simulator mode
- Dispatch/release behaviour cannot be validated without real hardware

This is a JMRI limitation, not a script issue.

**All meaningful testing must be done against a real Digitrax command station.**

---

## Prerequisites

You will need:

- JMRI (PanelPro or DecoderPro)
- A real Digitrax command station
- A Digitrax interface (PR3, PR4, LocoBuffer-USB, etc.)
- JMRI connected to the command station via LocoNet

You do **not** need:
- a layout
- locomotives on the track

Slot allocation works with the command station alone.

---

## Recommended file layout

Create a stable folder on the JMRI PC, for example:

C:\JMRI\FreemoSlotRecycler\

Place the following files in this folder:

- FreemoSlotRecycler.py
- protected_addresses.txt

Using a fixed path avoids Windows user-profile and permission issues.

---

## Script path configuration

Edit the following lines near the top of FreemoSlotRecycler.py:

BASE_DIR = r"C:\JMRI\FreemoSlotRecycler"

PROTECTED_ADDRESSES_FILE = os.path.join(BASE_DIR, "protected_addresses.txt")

LOG_FILE = os.path.join(BASE_DIR, "FreemoSlotRecycler.log")

This ensures:
- logs always go to a known location
- protected addresses are reliably loaded

---

## First-run safety settings (DO THIS FIRST)

Before running on real hardware, set:

DRY_RUN = True

INCLUDE_HANDHELD_THROTTLES = False

IDLE_TIMEOUT_SECONDS = 120

CONSIST_IDLE_TIMEOUT_SECONDS = 300

This configuration:
- prevents dispatch/release messages being sent
- limits clean-up to JMRI/WiThrottle slots only
- uses short timeouts so behaviour is visible quickly

Do **not** skip this step.

---

## Manual test (recommended)

Before enabling startup execution:

1. Open JMRI
2. Go to Scripting → Run Script…
3. Select FreemoSlotRecycler.py
4. Open the Script Output window

You should see a message similar to:

Freemo slot recycler starting. interval=60s idle=120s ...

If nothing appears in the console, check the log file:

C:\JMRI\FreemoSlotRecycler\FreemoSlotRecycler.log

The log file is the authoritative record.

---

## Enable on startup

Once manual testing is successful:

1. Open Edit → Preferences
2. Go to Startup
3. Click Add…
4. Choose Run Script
5. Select FreemoSlotRecycler.py
6. Click Save
7. Restart JMRI

After restart, confirm the log file shows:
- a startup message
- periodic scan messages (once per minute by default)

---

## Connect to real Digitrax hardware

The script only functions when JMRI is connected to a real Digitrax command station.

1. Open Preferences → Connections
2. Set:
   - Manufacturer: Digitrax
   - Connection: PR3 / PR4 / LocoBuffer-USB / etc.
3. Save and restart JMRI

To verify:
- Open LocoNet → Monitor Slots
- Acquire a locomotive address using a JMRI throttle
- A slot should appear immediately

If Slot Monitor does not populate on real hardware, this is a connection issue,
not a script issue.

---

## Verifying behaviour (safe mode)

With DRY_RUN = True:

1. Acquire several locomotive addresses
2. Leave at least one at speed 0 longer than the idle timeout
3. Check the log file

The log will report which slots would be reclaimed, without sending any
dispatch or release commands.

---

## Enabling live dispatch/release

Once you are satisfied with dry-run behaviour:

DRY_RUN = False

Leave handheld throttles disabled initially:

INCLUDE_HANDHELD_THROTTLES = False

This still provides benefit by cleaning up JMRI/WiThrottle slots without
interfering with physical throttles.

---

## Handheld throttles (Freemo agreement required)

If the operating group agrees that any idle slot may be reclaimed:

INCLUDE_HANDHELD_THROTTLES = True

Recommended timeouts when this is enabled:

IDLE_TIMEOUT_SECONDS = 600
CONSIST_IDLE_TIMEOUT_SECONDS = 900

This reduces the risk of reclaiming a slot from someone who has paused briefly.

---

## Protected addresses

The file protected_addresses.txt contains one DCC address per line.
Any address listed here is never dispatched or released by the script.

Example:

9999
12345
2001

Typical uses:
- yardmaster locomotives
- long-term staging holds
- parked consists
- test locomotives

---

## Recommended deployment order

1. Enable DRY_RUN
2. Limit to JMRI/WiThrottle slots only
3. Validate against real hardware
4. Enable dispatch/release
5. Optionally enable handheld throttles (with agreed ops rule)

---

## Summary

This script is designed to:
- reduce Digitrax slot exhaustion during large operating sessions
- behave conservatively by default
- provide full transparency via logging
- avoid unexpected interference unless explicitly enabled

Always validate changes on real hardware before Freemo deployment.
