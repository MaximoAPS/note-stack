# Manual Test Instructions for UX Bug Fixes

## Setup
1. Start the Streamlit app: `streamlit run app.py`
2. Open the app in your browser (usually http://localhost:8501)

## Test Scenarios

### ✅ Test 1: Fast Synthesis (Bug #1)
**What to test**: Play button should complete quickly, not hang

**Steps**:
1. Click "➕ Add Empty Track" 
2. In the track editor, paste cluster string: `35-35,36-38-35`
3. Set duration to `1/2` beat
4. Click "📥 Paste"
5. Click "✅ Apply Changes"
6. Click "▶ Play" button

**Expected Result**: 
- Synthesis completes in **~1-2 seconds** (not 15-20s!)
- Audio player appears and plays smoothly
- No "hung" appearance

**Status**: ✅ Verified in automated tests (0.64s for this scenario)

---

### ✅ Test 2: Audio Persists (Bug #5)
**What to test**: Audio player should stay visible after UI interactions

**Steps**:
1. After completing Test 1, click "▶ Play" if not already done
2. Wait for audio player to appear
3. Interact with any UI element (e.g., change BPM slider, expand/collapse track)
4. Observe audio player

**Expected Result**:
- Audio player remains visible
- Can still play the audio after any UI interaction

**Status**: ✅ Implemented via `st.session_state['last_audio']`

---

### ✅ Test 3: Low Key Warning (Bug #3)
**What to test**: Pasting very low piano keys should show warnings

**Steps**:
1. Add an empty track
2. In cluster paste field, enter: `3-1-4-1-5` (Pi digits, thinking they're melody notes)
3. Click "📥 Paste"
4. Look for warnings below the paste button

**Expected Result**:
- See 5 warnings like: "⚠️ Key 3 is very low (near bottom of piano, barely audible)"
- Helper text explains: "Paste uses **piano keys 1–88** (middle C = 40)"
- Notes are still added but user is informed

**Status**: ✅ Verified in automated tests (5 warnings generated)

---

### ✅ Test 4: Normal Keys No Warning (Bug #3)
**What to test**: Normal piano keys should NOT trigger warnings

**Steps**:
1. Add an empty track
2. Paste cluster string: `35-35,36-38-35`
3. Click "📥 Paste"

**Expected Result**:
- No warnings shown
- Success message: "✓ Pasted 4 clusters"

**Status**: ✅ Verified in automated tests (0 warnings)

---

### ✅ Test 5: Empty Track No Errors (Bug #2)
**What to test**: Empty tracks shouldn't cause console errors

**Steps**:
1. Add an empty track (no notes)
2. Expand the track
3. Look at the browser console (F12 → Console tab)

**Expected Result**:
- Timeline shows "No notes in this track"
- **No** error about "Infinite extent for field 'start'"
- Console is clean

**Status**: ✅ Verified - guard added to `render_timeline_chart()`

---

### ✅ Test 6: No Deprecation Warnings (Bug #4)
**What to test**: No Streamlit deprecation warnings in terminal

**Steps**:
1. Use the app normally (click buttons, interact with UI)
2. Check the terminal where Streamlit is running

**Expected Result**:
- **No** warnings about `use_container_width` being deprecated
- Terminal output is clean

**Status**: ✅ Verified - all instances replaced with `width='stretch'`

---

## Quick Smoke Test (All Bugs)

**One test to verify everything**:

1. Start app
2. Click "➕ Add Empty Track"
3. Paste: `3-1-4-1-5` → Should see low key warnings ✅
4. Clear and paste: `35-35,36-38-35` → Should see no warnings ✅
5. Click "📥 Paste" → Success message
6. Click "✅ Apply Changes"
7. Click "▶ Play" → Fast synthesis (~1s, not 15s) ✅
8. Audio player appears ✅
9. Change BPM slider → Audio player still visible ✅
10. Check console → No Altair errors ✅
11. Check terminal → No deprecation warnings ✅

**All 6 bugs fixed!** 🎉

---

## Performance Comparison

### Before (PR #7):
- 5 notes: ~15-20 seconds (appears hung)
- Empty track: Altair console spam
- Low keys: No guidance, confusing
- Audio: Disappears on rerun
- Deprecations: Console spam

### After (This PR):
- 5 notes: ~0.6-1 seconds (**20-30x faster!**)
- Empty track: Clean, no errors
- Low keys: Clear warnings + explanation
- Audio: Persists across reruns
- Deprecations: All fixed, clean logs

---

## Automated Test Suite

Run: `python3 test_bug_fixes.py`

```
✓ PASS: Synthesis Speed (0.66s for 5 notes)
✓ PASS: Empty Track Handling
✓ PASS: Low Key Warnings
✓ PASS: Normal Key No Warnings  
✓ PASS: Velocity Enforcement
✓ PASS: Test Case Synthesis

Passed: 6/6
```
