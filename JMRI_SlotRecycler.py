# FreemoSlotRecycler.py
# JMRI Jython script to recycle Digitrax slots by dispatching/releasing idle locos/consists.
#
# Install:
#  1) Save this file somewhere on the JMRI PC.
#  2) JMRI Preferences -> Startup -> Add -> Run Script -> select this file.
#  3) Restart JMRI (or run once via Scripting -> Run Script).
#
# Behaviour:
#  - Scans LocoNet slots every SCAN_INTERVAL_SECONDS.
#  - Tracks "activity" by changes in speed/status/owner (where available).
#  - If speed==0 and no activity for IDLE_TIMEOUT_SECONDS:
#       - Dispatch (preferred) then optional Release fallback.
#  - Consists: only if enabled AND all members speed==0 AND consist idle > CONSIST_IDLE_TIMEOUT_SECONDS.
#
# Notes:
#  - API varies a bit between JMRI versions. This script is defensive and will skip things it cannot safely classify.
#  - "Include handheld throttles" can reclaim slots from real operators. Use only with an agreed operating rule.

import time
import os

import jmri
from jmri.jmrix.loconet import LocoNetSystemConnectionMemo

from java.util import Timer, TimerTask

# -----------------------------
# Configuration
# -----------------------------
SCAN_INTERVAL_SECONDS = 60

IDLE_TIMEOUT_SECONDS = 300               # 5 minutes for single locos
CONSIST_IDLE_TIMEOUT_SECONDS = 300       # 5 minutes for consists (set 600 if you want safer)

DISPATCH_THEN_RELEASE = True             # True = dispatch first, then release fallback; False = release only

INCLUDE_CONSISTS = True                  # True = attempt to dispatch idle consists too (conservative logic)
INCLUDE_HANDHELD_THROTTLES = True        # False (safe) = only act on JMRI/WiThrottle-owned slots (when detectable)
                                         # True (risky) = act on ANY idle slot after timeout, including handhelds

# If INCLUDE_HANDHELD_THROTTLES is False, we only touch slots whose throttle identity matches one of these IDs.
# If you know your JMRI throttle ID, add it here. If empty, script will try to detect and otherwise skip for safety.
ALLOWED_THROTTLE_IDS = []                # e.g. [0x12, 0x13]

# Protected addresses file: one DCC address per line (e.g., 12345)
# Those addresses will never be dispatched/released by this script.
BASE_DIR = r"C:\JMRI\FreemoSlotRecycler"
PROTECTED_ADDRESSES_FILE = os.path.join(BASE_DIR, "protected_addresses.txt")

# Logging
LOG_TO_CONSOLE = True
LOG_FILE = os.path.join(BASE_DIR, "FreemoSlotRecycler.log")


# Safety switches
DRY_RUN = False                          # Set True to see what it would do without sending any LocoNet messages
SKIP_SYSTEM_SLOTS = True                 # Skip system slots if detectable

# -----------------------------
# Internal state
# -----------------------------
_state_by_slot = {}   # slotNumber -> dict(lastSpeed,lastStatus,lastOwner,lastActivity,isConsist,consistId,address)
_timer = None

# -----------------------------
# Implementation
# -----------------------------
def _log(msg):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = "%s  %s" % (stamp, msg)
    if LOG_TO_CONSOLE:
        print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def _now():
    return int(time.time())

# Load protected addresses from file
def _load_protected_addresses():
    protected = set()
    try:
        if os.path.isfile(PROTECTED_ADDRESSES_FILE):
            with open(PROTECTED_ADDRESSES_FILE, "r") as f:
                for raw in f.readlines():
                    s = raw.strip()
                    if not s or s.startswith("#"):
                        continue
                    try:
                        protected.add(int(s))
                    except:
                        pass
    except:
        pass
    return protected

# Get the first LocoNet memo (assuming single LocoNet connection)
def _get_first_loconet_memo():
    memos = jmri.InstanceManager.getList(LocoNetSystemConnectionMemo)
    if memos is None or memos.size() == 0:
        return None
    return memos.get(0)

# Send a LocoNet message via the memo's traffic controller
def _send_ln_message(memo, msg):
    tc = memo.getLnTrafficController()
    tc.sendLocoNetMessage(msg)

# Helper to safely call a method and return default on failure
def _safe_get(obj, method_name, default=None):
    try:
        if hasattr(obj, method_name):
            m = getattr(obj, method_name)
            return m()
    except:
        return default
    return default

# Get slot number from slot object
def _slot_number(slot):
    # Different JMRI builds expose this differently.
    for name in ["getSlot", "slot", "slotNumber", "getSlotNumber"]:
        val = _safe_get(slot, name, None)
        if val is not None:
            return int(val)
    # Fallback: sometimes toString includes it, but we avoid parsing unless necessary.
    return None

# Get loco address from slot object
def _slot_address(slot):
    addr = _safe_get(slot, "locoAddr", None)
    if addr is None:
        addr = _safe_get(slot, "getLocoAddr", None)
    try:
        if addr is not None:
            return int(addr)
    except:
        pass
    return 0

# Get speed from slot object
def _slot_speed(slot):
    spd = _safe_get(slot, "speed", None)
    if spd is None:
        spd = _safe_get(slot, "getSpeed", None)
    try:
        if spd is not None:
            return int(spd)
    except:
        pass
    return 0

# Get slot status from slot object
def _slot_status(slot):
    st = _safe_get(slot, "slotStatus", None)
    if st is None:
        st = _safe_get(slot, "getSlotStatus", None)
    return st

# Check if slot is a system slot
def _slot_is_system(slot):
    if not SKIP_SYSTEM_SLOTS:
        return False
    val = _safe_get(slot, "isSystemSlot", None)
    if val is None:
        val = _safe_get(slot, "getIsSystemSlot", None)
    try:
        return bool(val)
    except:
        return False

# Get throttle identity from slot object
def _slot_throttle_id(slot):
    # Often available as getThrottleIdentity()
    tid = _safe_get(slot, "getThrottleIdentity", None)
    if tid is None:
        tid = _safe_get(slot, "throttleIdentity", None)
    try:
        if tid is not None:
            return int(tid)
    except:
        return None
    return None

# Detect consist ID from slot object
def _detect_consist_id(slot):
    # Consist detection varies widely. We try a few likely candidates.
    # If we cannot reliably determine consist membership, return None and treat as non-consist.
    # Some JMRI builds expose consist status/addr via slot fields.
    for name in ["consistAddr", "getConsistAddr", "getConsistAddress", "consistAddress"]:
        val = _safe_get(slot, name, None)
        try:
            if val is not None and int(val) != 0:
                return int(val)
        except:
            pass
    return None

# Check if throttle owner is allowed
def _is_allowed_owner(throttle_id):
    # If including handhelds, owner filter is irrelevant.
    if INCLUDE_HANDHELD_THROTTLES:
        return True

    # If we have an explicit allow-list, use it.
    if len(ALLOWED_THROTTLE_IDS) > 0:
        return throttle_id in ALLOWED_THROTTLE_IDS

    # If we don't know throttle IDs, we cannot safely act (we'd rather leak than steal).
    return False

# Retrieve all slots from slot manager
def _get_all_slots(slot_manager):
    # Try getSlots() first (common in many JMRI builds)
    if hasattr(slot_manager, "getSlots"):
        try:
            return list(slot_manager.getSlots())
        except:
            pass

    # Fallback: try range-based access. We attempt common methods.
    slots = []
    # Guess max slots; many Digitrax systems go higher, but we can cap for safety.
    max_guess = 128
    getter_names = ["get", "getSlot", "slot", "getSlotAt"]
    getter = None
    for gn in getter_names:
        if hasattr(slot_manager, gn):
            getter = getattr(slot_manager, gn)
            break
    if getter is None:
        return slots

    for i in range(1, max_guess + 1):
        try:
            s = getter(i)
            if s is not None:
                slots.append(s)
        except:
            pass
    return slots

# Dispatch slot via its dispatchSlot() method
def _dispatch_slot(memo, slot):
    # slot.dispatchSlot() returns a LocoNet message
    msg = None
    try:
        if hasattr(slot, "dispatchSlot"):
            msg = slot.dispatchSlot()
    except:
        msg = None
    if msg is None:
        return False, "dispatchSlot() unavailable"

    if DRY_RUN:
        return True, "DRY_RUN dispatch"
    try:
        _send_ln_message(memo, msg)
        return True, "dispatched"
    except Exception as e:
        return False, "dispatch send failed: %s" % str(e)

# Release slot via its releaseSlot() method
def _release_slot(memo, slot):
    msg = None
    try:
        if hasattr(slot, "releaseSlot"):
            msg = slot.releaseSlot()
    except:
        msg = None
    if msg is None:
        return False, "releaseSlot() unavailable"

    if DRY_RUN:
        return True, "DRY_RUN release"
    try:
        _send_ln_message(memo, msg)
        return True, "released"
    except Exception as e:
        return False, "release send failed: %s" % str(e)

# Mark activity in slot record
def _mark_activity(slot_no, rec, reason):
    rec["lastActivity"] = _now()
    # Keep a short reason for debugging
    rec["lastActivityReason"] = reason

# Update internal state for a slot object
def _update_state_for_slot(slot):
    slot_no = _slot_number(slot)
    if slot_no is None:
        return None, None

    addr = _slot_address(slot)
    spd = _slot_speed(slot)
    st = _slot_status(slot)
    tid = _slot_throttle_id(slot)

    if addr <= 0:
        return slot_no, None

    consist_id = _detect_consist_id(slot)

    rec = _state_by_slot.get(slot_no)
    if rec is None:
        rec = {
            "address": addr,
            "lastSpeed": spd,
            "lastStatus": st,
            "lastOwner": tid,
            "lastActivity": _now(),
            "lastActivityReason": "firstSeen",
            "consistId": consist_id,
        }
        _state_by_slot[slot_no] = rec
        return slot_no, rec

    # Address change means the slot got reused -> reset record
    if rec.get("address") != addr:
        rec["address"] = addr
        rec["lastSpeed"] = spd
        rec["lastStatus"] = st
        rec["lastOwner"] = tid
        _mark_activity(slot_no, rec, "addressChanged")
        rec["consistId"] = consist_id
        return slot_no, rec

    # Activity detection
    if rec.get("lastSpeed") != spd:
        rec["lastSpeed"] = spd
        _mark_activity(slot_no, rec, "speedChanged")

    # Status changes can indicate reacquire/ownership changes
    if rec.get("lastStatus") != st:
        rec["lastStatus"] = st
        _mark_activity(slot_no, rec, "statusChanged")

    if rec.get("lastOwner") != tid:
        rec["lastOwner"] = tid
        _mark_activity(slot_no, rec, "ownerChanged")

    rec["consistId"] = consist_id
    return slot_no, rec

# Build consist groups from slots
def _build_consist_groups(slots):
    # consistId -> list of slot objects
    groups = {}
    for slot in slots:
        cid = _detect_consist_id(slot)
        if cid is None or cid == 0:
            continue
        groups.setdefault(cid, []).append(slot)
    return groups

def _slot_idle_seconds(rec):
    return _now() - int(rec.get("lastActivity", _now()))

# Perform one cleanup pass
def _cleanup_once(memo):
    protected = _load_protected_addresses()

    slot_manager = memo.getSlotManager()
    slots = _get_all_slots(slot_manager)
    if len(slots) == 0:
        _log("No slots retrieved (slot manager API mismatch or no slot data yet).")
        return

    # Update state tracking
    live_slots = []
    for s in slots:
        if s is None:
            continue
        if _slot_is_system(s):
            continue
        slot_no, rec = _update_state_for_slot(s)
        if rec is None:
            continue
        live_slots.append(s)

    # Consist cleanup (conservative)
    handled_slot_numbers = set()
    if INCLUDE_CONSISTS:
        groups = _build_consist_groups(live_slots)
        for cid, members in groups.items():
            # Skip if any member is protected or unknown state
            member_recs = []
            ok = True
            for m in members:
                mno = _slot_number(m)
                if mno is None:
                    ok = False
                    break
                rec = _state_by_slot.get(mno)
                if rec is None:
                    ok = False
                    break
                if rec.get("address") in protected:
                    ok = False
                    break
                member_recs.append((m, mno, rec))

            if not ok or len(member_recs) == 0:
                continue

            # Must be fully stopped
            all_stopped = True
            for (m, mno, rec) in member_recs:
                if _slot_speed(m) != 0:
                    all_stopped = False
                    break
            if not all_stopped:
                continue

            # Must be idle long enough (use max lastActivity among members)
            last_activity = 0
            for (m, mno, rec) in member_recs:
                la = int(rec.get("lastActivity", 0))
                if la > last_activity:
                    last_activity = la
            idle = _now() - last_activity
            if idle <= CONSIST_IDLE_TIMEOUT_SECONDS:
                continue

            # Owner check
            if not INCLUDE_HANDHELD_THROTTLES:
                # Require all members owned by allowed throttle IDs (or we skip)
                owners = []
                for (m, mno, rec) in member_recs:
                    owners.append(rec.get("lastOwner"))
                if not all(_is_allowed_owner(o) for o in owners):
                    continue

            # Dispatch consist members
            _log("CONSIST idle -> cid=%s members=%d idle=%ss : dispatching" % (cid, len(member_recs), idle))
            for (m, mno, rec) in member_recs:
                addr = rec.get("address")
                if DISPATCH_THEN_RELEASE:
                    ok1, msg1 = _dispatch_slot(memo, m)
                    _log("  member addr=%s slot=%s dispatch=%s (%s)" % (addr, mno, ok1, msg1))
                    if not ok1:
                        ok2, msg2 = _release_slot(memo, m)
                        _log("  member addr=%s slot=%s release=%s (%s)" % (addr, mno, ok2, msg2))
                else:
                    ok2, msg2 = _release_slot(memo, m)
                    _log("  member addr=%s slot=%s release=%s (%s)" % (addr, mno, ok2, msg2))

                handled_slot_numbers.add(mno)

    # Single loco cleanup
    for s in live_slots:
        slot_no = _slot_number(s)
        if slot_no is None or slot_no in handled_slot_numbers:
            continue

        rec = _state_by_slot.get(slot_no)
        if rec is None:
            continue

        addr = int(rec.get("address", 0))
        if addr <= 0:
            continue
        if addr in protected:
            continue

        spd = _slot_speed(s)
        if spd != 0:
            continue

        idle = _slot_idle_seconds(rec)
        if idle <= IDLE_TIMEOUT_SECONDS:
            continue

        owner = rec.get("lastOwner")
        if not _is_allowed_owner(owner):
            continue

        cid = rec.get("consistId")
        if cid is not None and cid != 0:
            # If it looks like part of a consist but we didn't handle consists (disabled/undetected), skip for safety.
            if not INCLUDE_CONSISTS:
                continue

        # Action
        if DISPATCH_THEN_RELEASE:
            ok1, msg1 = _dispatch_slot(memo, s)
            _log("LOCO idle -> addr=%s slot=%s idle=%ss owner=%s dispatch=%s (%s)" %
                 (addr, slot_no, idle, owner, ok1, msg1))
            if not ok1:
                ok2, msg2 = _release_slot(memo, s)
                _log("LOCO idle -> addr=%s slot=%s release=%s (%s)" % (addr, slot_no, ok2, msg2))
        else:
            ok2, msg2 = _release_slot(memo, s)
            _log("LOCO idle -> addr=%s slot=%s idle=%ss owner=%s release=%s (%s)" %
                 (addr, slot_no, idle, owner, ok2, msg2))

# -----------------------------
# Timer management
# -----------------------------
def _start_timer():
    global _timer

    memo = _get_first_loconet_memo()
    if memo is None:
        _log("No LocoNet connection found. Script not started.")
        return

    _log("Freemo slot recycler starting. interval=%ss idle=%ss consistIdle=%ss dispatchThenRelease=%s includeConsists=%s includeHandheld=%s dryRun=%s" %
         (SCAN_INTERVAL_SECONDS, IDLE_TIMEOUT_SECONDS, CONSIST_IDLE_TIMEOUT_SECONDS,
          DISPATCH_THEN_RELEASE, INCLUDE_CONSISTS, INCLUDE_HANDHELD_THROTTLES, DRY_RUN))

    class Task(TimerTask):
        def run(self):
            try:
                _cleanup_once(memo)
            except Exception as e:
                _log("ERROR during cleanup: %s" % str(e))

    _timer = Timer("FreemoSlotRecyclerTimer", True)
    _timer.schedule(Task(), 2000, SCAN_INTERVAL_SECONDS * 1000)

# -----------------------------
# Public API
# -----------------------------
def stop_freemo_slot_recycler():
    # Call this from the JMRI script console if you ever need to stop it.
    global _timer
    if _timer is not None:
        try:
            _timer.cancel()
        except:
            pass
        _timer = None
        _log("Freemo slot recycler stopped.")

# Start immediately when script runs (startup action)
_start_timer()
