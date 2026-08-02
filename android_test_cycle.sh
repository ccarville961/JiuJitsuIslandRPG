#!/usr/bin/env bash
set -u

ADB="$HOME/Library/Android/sdk/platform-tools/adb"
PACKAGE="com.jiujitsuislandrpg.jiujitsuislandrpg"
ACTIVITY="$PACKAGE/org.kivy.android.PythonActivity"
PROJECT="$HOME/JiuJitsuIslandRPG"
REPORT="$PROJECT/android-latest-report.txt"
RAW_LOG="$PROJECT/android-latest-logcat.txt"

cd "$PROJECT" || exit 1

echo "========================================"
echo " JiuJitsu Island Android Test Cycle"
echo "========================================"

if [ ! -x "$ADB" ]; then
    echo "ERROR: adb not found at:"
    echo "$ADB"
    exit 1
fi

if ! "$ADB" get-state >/dev/null 2>&1; then
    echo "ERROR: No Android emulator/device connected."
    exit 1
fi

APK="$(ls -t "$PROJECT"/bin/*.apk 2>/dev/null | head -1)"

if [ -z "${APK:-}" ]; then
    echo "ERROR: No APK found in $PROJECT/bin"
    exit 1
fi

echo
echo "Using APK:"
echo "$APK"

echo
echo "Uninstalling old app..."
"$ADB" uninstall "$PACKAGE" >/dev/null 2>&1 || true

echo "Installing APK..."
if ! "$ADB" install -r "$APK"; then
    echo "ERROR: APK installation failed."
    exit 1
fi

echo "Clearing logcat..."
"$ADB" logcat -c

echo "Launching app..."
"$ADB" shell am start -n "$ACTIVITY"

echo
echo "Use the emulator now."
echo "Reproduce the problem."
echo "This script will watch until the app closes."
echo

START_TIME=$(date +%s)
SEEN_PROCESS=0

while true; do
    PID="$("$ADB" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"

    if [ -n "$PID" ]; then
        SEEN_PROCESS=1
    elif [ "$SEEN_PROCESS" -eq 1 ]; then
        echo
        echo "App process ended. Capturing diagnostics..."
        break
    fi

    NOW=$(date +%s)
    ELAPSED=$((NOW - START_TIME))

    if [ "$ELAPSED" -ge 300 ]; then
        echo
        echo "Five-minute timeout reached. Capturing diagnostics..."
        break
    fi

    sleep 1
done

"$ADB" logcat -d -v time > "$RAW_LOG"

{
    echo "========================================"
    echo "JIUJITSU ISLAND ANDROID DIAGNOSTIC REPORT"
    echo "========================================"
    echo
    echo "APK:"
    echo "$APK"
    echo
    echo "Device ABI:"
    "$ADB" shell getprop ro.product.cpu.abi
    echo
    echo "Supported ABIs:"
    "$ADB" shell getprop ro.product.cpu.abilist
    echo
    echo "========================================"
    echo "PYTHON TRACEBACKS"
    echo "========================================"
    grep -A180 -B30 "Traceback" "$RAW_LOG" | tail -400 || true
    echo
    echo "========================================"
    echo "GAME / ASSET / AUDIO ERRORS"
    echo "========================================"
    grep -iE \
    "Tuxemon Error|Error starting action|Could not find sprite|Couldn't open asset|Failed to load|does not exist|FileNotFoundError|ModuleNotFoundError|ImportError|pygame.error|subsurface|TypeError|ValueError|AttributeError|KeyError|mixer|audio|sound" \
    "$RAW_LOG" | tail -300 || true
    echo
    echo "========================================"
    echo "NATIVE / SDL / ANDROID CRASHES"
    echo "========================================"
    grep -iE \
    "Fatal signal|SIGABRT|SIGSEGV|FORTIFY|destroyed mutex|FATAL EXCEPTION|AndroidRuntime|SDLActivity|crash_dump" \
    "$RAW_LOG" | tail -300 || true
    echo
    echo "========================================"
    echo "TOUCH OVERLAY"
    echo "========================================"
    grep -iE \
    "Controller overlay set up successfully|Touch detected on|FINGERDOWN|FINGERUP|FINGERMOTION" \
    "$RAW_LOG" | tail -200 || true
} > "$REPORT"

echo
echo "Diagnostic report created:"
echo "$REPORT"
echo
echo "Raw log created:"
echo "$RAW_LOG"
echo
echo "Opening report..."
open "$REPORT"
