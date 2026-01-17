# Automatic Slot Clean-Up Policy

**For Freemo / Digitrax / JMRI Layouts**

## Why We Need This

Right, so here's the problem: on big Freemo layouts, the Digitrax command station slot table fills up bloody quickly during ops sessions. When that happens, trains just stop responding and you're stuck doing a command station reset — which nobody wants mid-session.

This policy lays out a sensible way to clean up abandoned locos and consists (including ones people have walked away from while still holding throttles) without stuffing up anyone who's actually running trains.

**Bottom line:** we want the layout to keep running smoothly through long sessions without drama.

---

## Let's Be Real About What's Possible

Digitrax doesn't actually support a proper slot purge. There's no magic button.

What you've got to work with is:
- Dispatch
- Release to common

That's it. This policy works within those constraints. It won't instantly clear slots or make the slot list shorter. What it *will* do is stop genuinely abandoned slots from piling up and causing grief.

---

## What Operators Should Actually Do

When you're done with a loco or consist:

1. Bring the speed to **0**
2. **Dispatch or release** it from your throttle
3. *Then* disconnect or hand the throttle back

If you're just grabbing a coffee and coming straight back, stay connected and leave the loco under your control. No worries.

---

## The Automatic Clean-Up Rule (Safety Net)

Any loco or consist — whether it's controlled by JMRI, WiThrottle, or a handheld throttle — can be automatically dispatched if *all* of these are true:

- Speed's been sitting at **0**
- There's been **no activity** at all
- It's been inactive for **more than 5 minutes**

This is a backup for genuinely abandoned trains, yeah? It's not a replacement for people doing the right thing in the first place.

---

## What Counts as "No Activity"

A loco or consist is only considered inactive if there's been absolutely no:

- Speed change
- Direction change
- Function use (lights, horn, bell, whatever)
- Throttle re-acquire or reconnect (yep, this includes handheld throttles too)

**Any activity at all resets the timer.** Doesn't matter if you're using an app or a physical throttle — same rules apply.

---

## What Never Gets Touched

The system won't automatically clean up:

- Anything that's **moving** (speed above 0)
- Anything that's had **activity in the last 5 minutes**
- Anything **explicitly marked as protected** by session control

Doesn't matter who owns the throttle if there's actual activity happening.

---

## Consists (Pay Attention Here)

Consists get handled carefully.

A consist will **only** be cleaned up if:

- *All* member locos are at speed **0**, **and**
- The *entire* consist has had **zero activity for more than 5 minutes**

We'll only break a consist after the timeout has well and truly passed.

---

## Protected Operations

Yardmasters or session controllers can mark specific locos or consists as **protected**. This covers things like:

- Long-term staging holds
- Display or parked trains
- Planned pauses during an ops session

Protected items won't get touched by automatic clean-up, regardless of throttle type.

---

## Keeping Things Transparent

Every automatic action gets logged with:

- Time
- Loco or consist details
- How long it was inactive
- What action was taken

This means if anything goes sideways, we can review it calmly after the session and work out what happened.

---

## Configuration

See the [Technical Implementation README](TECHNICAL.md) for script installation and configuration details.

---

## Questions?

If you've got questions about this policy or how it works in practice, have a chat with your session controller or yardmaster.

---

## License

This policy and associated scripts are released under the MIT License. See LICENSE file for details.
