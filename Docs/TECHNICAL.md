# JMRI Automatic Slot Clean-Up Script

## Technical Implementation Guide

This document explains how the [Automatic Slot Clean-Up Policy](README.md) is implemented in JMRI, including how it safely handles handheld throttles.

---

## Core Design Principle

**Behaviour beats ownership.**

The script doesn't try to figure out whether a throttle is JMRI, WiThrottle, or handheld. Instead, it watches for actual inactivity.

- If a slot shows activity → it's left alone
- If it shows bugger-all activity for long enough → it's assumed to be abandoned

Simple as that.

---

## System Requirements

- JMRI 4.x or later
- Digitrax command station (tested with DCS100, DCS200, DCS240)
- LocoNet connection configured in JMRI

---

## Installation

### Step 1: Download the Script

Place the script file in your JMRI scripts directory:

- **Windows:** `C:\Users\[YourName]\JMRI\jython\`
- **Mac:** `/Users/[YourName]/JMRI/jython/`
- **Linux:** `/home/[YourName]/JMRI/jython/`

### Step 2: Add as Startup Action

1. Open JMRI PanelPro or DecoderPro
2. Go to **Edit → Preferences → Startup**
3. Click **Add → Run Script**
4. Browse to and select the clean-up script
5. Click **Save** and restart JMRI

The script will now run automatically when JMRI starts.

---

## Configuration

### Timing Settings

Default values (edit in script if needed):

```python
SCAN_INTERVAL = 60        # Scan slot table every 60 seconds
LOCO_TIMEOUT = 300        # 5 minutes for single locos
CONSIST_TIMEOUT = 480     # 8 minutes for consists (optional)
```
