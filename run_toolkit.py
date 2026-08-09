import os
import re
import subprocess
import sys
import PySimpleGUI as sg

# Resolve the adb executable: prefer the bundled adb/ subfolder next to this
# script so users don't need ADB on their system PATH.
def _find_adb():
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    local = os.path.join(script_dir, "adb", "adb.exe")
    return local if os.path.isfile(local) else "adb"

ADB = _find_adb()


# Fix 3: Replace global mutable state with a simple state container
class TVConnection:
    def __init__(self):
        self.connected = False
        self.ip = ""
        self.port = "5555"

    @property
    def target(self):
        return f"{self.ip}:{self.port}"


state = TVConnection()


# Fix 2: IP address validation
def is_valid_ip(ip):
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip)) and all(
        0 <= int(p) <= 255 for p in ip.split(".")
    )


# Fix 1 & 6: Use subprocess (not os.popen), scope reconnect check to specific device
def run_adb(*args):
    """Run an adb command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            [ADB, *args],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"adb not found at '{ADB}'. Make sure the adb/ folder is present next to this script.", 1
    except subprocess.TimeoutExpired:
        return "", "ADB command timed out.", 1


def reconnect_check():
    # Fix 6: scope device check to the connected target, not all devices
    if not state.connected or not state.ip:
        return False
    stdout, _, _ = run_adb("devices")
    if state.target not in stdout:
        stdout, _, rc = run_adb("connect", state.target)
        if rc == 0 and ("connected" in stdout or "already connected" in stdout):
            return True
        state.connected = False
        return False
    return True


safe_apps = [
    ("Android TV Recommendations", "com.google.android.tvrecommendations"),
    ("Google Shop Row", "com.google.android.leanbacklauncher.recommendations"),
    ("Chromecast Built-In", "com.google.android.gms.cast.receiver"),
    ("Google Backdrop", "com.google.android.backdrop"),
    ("Google Play Movies & TV", "com.google.android.videos"),
    ("Google Play Games", "com.google.android.play.games"),
    ("Google Mediashell", "com.google.android.apps.mediashell"),
    ("Google Smart Connect", "com.google.android.apps.nbu.smartconnect.tv"),
    ("Google Feedback", "com.google.android.feedback"),
    ("One-Time Initializer", "com.google.android.onetimeinitializer"),
    ("Calendar Sync Adapter", "com.google.android.syncadapters.calendar"),
    ("Google Partner Setup", "com.google.android.partnersetup"),
    ("Android Easter Egg", "com.android.egg"),
    ("Print Spooler", "com.android.printspooler"),
    ("TalkBack (Accessibility)", "com.google.android.marvin.talkback"),
    ("Android Screensaver", "com.android.dreams.basic"),
    ("Calendar Provider", "com.android.providers.calendar"),
    ("Contacts Provider", "com.android.providers.contacts"),
    ("User Dictionary", "com.android.providers.userdictionary"),
    ("TCL Gallery", "com.tcl.gallery"),
    ("TCL Notes & Reminders", "com.tcl.notereminder"),
    ("TCL MessageBox", "com.tcl.messagebox"),
    ("TCL Antivirus (Guard)", "com.tcl.guard"),
    ("TCL Antivirus Overlay", "com.tcl.tvweishi"),
    ("TCL App Market", "com.tcl.appmarket2"),
    ("TCL Stickers", "com.tcl.esticker"),
    ("TCL PVR Player", "com.tcl.pvr.pvrplayer"),
    ("TCL Video Player", "com.tcl.videoplayer"),
    ("TCL Overseas App Ads", "com.tcl.overseasappshow"),
    ("TCL Boot Ads", "com.tcl.bootadservice"),
    ("TCL Dashboard", "com.tcl.dashboard"),
    ("Netflix TV App", "com.netflix.ninja"),
    ("AOS TV", "com.aos.aostv"),
    ("Freeview Explore", "uk.co.freeview.explore"),
    ("Freeview On Now", "uk.co.freeview.onnow"),
]

apps = [
    ("Chromecast Built-In", "com.google.android.gms.cast.receiver", "✅"),
    ("Google Play Movies & TV", "com.google.android.videos", "✅"),
    ("Android TV Recommendations", "com.google.android.tvrecommendations", "✅"),
    ("TCL Launcher", "com.tcl.usercenter2", "✅"),
    ("TCL User Center", "com.tcl.usercenter", "✅"),
    ("TCL Web Browser", "com.tcl.browser", "✅"),
    ("Notes and Reminders", "com.tcl.notereminder", "✅"),
    ("Gallery App", "com.tcl.gallery", "✅"),
    ("Netflix TV App", "com.netflix.ninja", "✅"),
    ("Freeview Explore", "uk.co.freeview.explore", "✅"),
    ("AOS TV", "com.aos.aostv", "✅"),
    ("Google Assistant", "com.google.android.googlequicksearchbox", "⚠️"),
    ("Google Play Store", "com.android.vending", "⚠️"),
    ("YouTube for Android TV", "com.google.android.youtube.tv", "⚠️"),
    ("TCL HDMI Service", "com.tcl.tv", "⚠️"),
    ("TCL Setup Wizard", "com.tcl.initsetup", "⚠️"),
    ("TCL Multiscreen Interaction", "com.tcl.MultiScreenInteraction_TV", "⚠️"),
    ("System UI", "com.android.systemui", "🚫"),
    ("Google Play Services", "com.google.android.gms", "🚫"),
    ("TCL Framework Core", "com.tcl.framework.custom", "🚫"),
]


def pair_and_connect():
    """Android 11+ / Chromecast: pair with a code first, then connect."""
    layout = [
        [sg.Text("Step 1 — Pairing (from your TV's Wireless Debugging screen)")],
        [sg.Text("TV IP Address:"), sg.InputText(key="IP", size=(20, 1))],
        [sg.Text("Pairing Port: "), sg.InputText(key="PAIR_PORT", size=(10, 1))],
        [sg.Text("Pairing Code: "), sg.InputText(key="PAIR_CODE", size=(15, 1))],
        [sg.HorizontalSeparator()],
        [sg.Text("Step 2 — Connection port (shown under 'IP address & Port' on your TV)")],
        [sg.Text("Debug Port:   "), sg.InputText(key="DEBUG_PORT", default_text="5555", size=(10, 1))],
        [sg.Button("Pair & Connect"), sg.Button("Cancel")],
    ]
    window = sg.Window("Pair & Connect (Android 11+ / Chromecast)", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        if event == "Pair & Connect":
            ip = values["IP"].strip()
            pair_port = values["PAIR_PORT"].strip()
            pair_code = values["PAIR_CODE"].strip()
            debug_port = values["DEBUG_PORT"].strip() or "5555"

            if not is_valid_ip(ip):
                sg.popup("❌ Invalid IP address. Enter a valid IPv4 address (e.g. 192.168.1.100).")
                continue
            if not pair_port.isdigit() or not debug_port.isdigit():
                sg.popup("❌ Ports must be numbers.")
                continue
            if not pair_code:
                sg.popup("❌ Pairing code cannot be empty.")
                continue

            # Step 1: pair
            stdout, stderr, rc = run_adb("pair", f"{ip}:{pair_port}", pair_code)
            if rc != 0 or ("successfully" not in stdout.lower() and "paired" not in stdout.lower()):
                detail = stderr.strip() or stdout.strip() or "Unknown error"
                sg.popup(f"❌ Pairing failed.\n\n{detail}\n\nCheck the IP, port, and code shown on your TV.")
                continue

            # Step 2: connect
            state.ip = ip
            state.port = debug_port
            stdout, stderr, rc = run_adb("connect", state.target)
            if rc == 0 and ("connected" in stdout or "already connected" in stdout):
                state.connected = True
                sg.popup(f"✅ Paired and connected to {state.target} successfully!\n\nNow choose Safe Debloat, Advanced Debloat, Install APK, etc. from the main menu.")
                break
            else:
                state.connected = False
                detail = stderr.strip() or stdout.strip() or "Unknown error"
                sg.popup(f"⚠️ Paired OK but connection failed.\n\n{detail}\n\nCheck the debug port shown under 'IP address & Port' on your TV.")
            break
    window.close()


def connect_to_tv():
    layout = [
        [sg.Text("Enter TV IP Address:")],
        [sg.InputText(key="IP")],
        [sg.Button("Connect"), sg.Button("Cancel")],
    ]
    window = sg.Window("Connect to TV", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        if event == "Connect":
            ip = values["IP"].strip()
            # Fix 2: validate IP before using it in any command
            if not is_valid_ip(ip):
                sg.popup("❌ Invalid IP address. Please enter a valid IPv4 address (e.g. 192.168.1.100).")
                continue
            state.ip = ip
            # Fix 1: subprocess with list args — no shell, no injection
            stdout, stderr, rc = run_adb("connect", state.target)
            # Fix 5: check return code, not just string content
            if rc == 0 and ("connected" in stdout or "already connected" in stdout):
                state.connected = True
                sg.popup(f"✅ Connected to {state.target} successfully!\n\nNow choose Safe Debloat, Advanced Debloat, Install APK, etc. from the main menu.")
            else:
                state.connected = False
                detail = stderr.strip() or stdout.strip() or "Unknown error"
                sg.popup(f"❌ Failed to connect.\n\n{detail}\n\nCheck your TV IP and ADB Debugging settings.")
            break
    window.close()


def install_apk():
    if not reconnect_check():
        sg.popup("❌ Not connected. Use 'Connect to TV' first.")
        return
    layout = [
        [sg.Text("Select APK to install:")],
        [sg.Input(), sg.FileBrowse(file_types=(("APK Files", "*.apk"),))],
        [sg.Button("Install"), sg.Button("Cancel")],
    ]
    window = sg.Window("Install APK", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        if event == "Install":
            apk_path = values[0]
            if not apk_path:
                sg.popup("No file selected.")
                continue
            remote_path = f"/sdcard/{os.path.basename(apk_path)}"
            # Fix 1 & 4: subprocess list args; Fix 4: use state.target (consistent port)
            push_out, push_err, push_rc = run_adb("-s", state.target, "push", apk_path, "/sdcard/")
            install_out, install_err, install_rc = run_adb(
                "-s", state.target, "shell", "pm", "install", "-r", remote_path
            )
            # Fix 5: surface errors clearly
            lines = []
            lines.append(f"Push {'✅ OK' if push_rc == 0 else '❌ Failed'}:")
            lines.append(push_out or push_err)
            lines.append(f"\nInstall {'✅ OK' if install_rc == 0 else '❌ Failed'}:")
            lines.append(install_out or install_err)
            sg.popup_scrolled("\n".join(lines), title="APK Install Log", size=(60, 20))
            break
    window.close()


GOOGLE_LAUNCHERS = (
    "com.google.android.apps.tv.launcherx",
    "com.google.android.tvlauncher",
    "com.google.android.leanbacklauncher",
)


def _find_google_launcher(installed):
    for pkg in GOOGLE_LAUNCHERS:
        if pkg in installed:
            return pkg
    return None


def _home_capable_non_google(installed):
    """Return third-party packages that can act as a launcher (HOME activity)."""
    stdout, _, rc = run_adb(
        "-s", state.target, "shell", "cmd", "package", "query-activities",
        "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME",
    )
    if rc != 0:
        return []
    candidates = set()
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("packageName="):
            continue
        pkg = line.split("=", 1)[1].strip()
        if pkg in installed and not any(
            pkg.startswith(base) or pkg == base for base in GOOGLE_LAUNCHERS
        ):
            candidates.add(pkg)
    candidates.discard("com.android.tv.settings")
    candidates.discard("com.google.android.tungsten.setupwraith")
    return sorted(candidates)


def disable_google_launcher():
    if not reconnect_check():
        sg.popup("❌ TV not connected. Use 'Connect to TV' first.")
        return
    installed = _installed_packages()
    google_launcher = _find_google_launcher(installed)
    if google_launcher is None:
        sg.popup("ℹ️ No Google TV launcher found on this device.\n\nYour TV likely uses a different launcher, so there is nothing to disable.")
        return

    alt_launchers = _home_capable_non_google(installed)
    if not alt_launchers:
        sg.popup(
            "🛑 Refusing to disable the launcher.\n\n"
            "No alternative launcher was detected (e.g. Projectivy, FLauncher).\n"
            "Install one from the Play Store first, then try again.\n\n"
            "Disabling the only launcher can leave your TV stuck on a black screen."
        )
        return

    layout = [
        [sg.Text(f"Current Google launcher: {google_launcher}")],
        [sg.Text("Select a backup launcher to switch to before disabling the Google one:")],
        [sg.Combo(alt_launchers, key="ALT", default_value=alt_launchers[0], size=(45, 1))],
        [sg.HorizontalSeparator()],
        [sg.Text("Recovery: to undo everything later, just enable 'com.google.android.tvlauncher'.\n"
                 "Press Home (🏠) once to confirm the new launcher opens.")],
        [sg.Button("Switch & Disable"), sg.Button("Cancel")],
    ]
    window = sg.Window("Disable Google TV Launcher", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        if event == "Switch & Disable":
            alt = values["ALT"]
            home_activity = None
            if alt:
                stdout, _, rc = run_adb(
                    "-s", state.target, "shell", "cmd", "package", "resolve-activity",
                    "--brief", "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.HOME", alt,
                )
                lines = [l.strip() for l in stdout.splitlines() if l.strip()]
                if rc == 0 and lines:
                    home_activity = lines[-1]
            if not home_activity:
                sg.popup("❌ Could not determine a HOME activity for that launcher. Nothing was changed.")
                break

            set_out, set_err, set_rc = run_adb(
                "-s", state.target, "shell", "cmd", "package", "set-home-activity", home_activity
            )
            if set_rc != 0:
                sg.popup_scrolled(set_err or set_out or "Failed to set default launcher.",
                                  title="❌ Setting Home Launcher Failed")
                break

            dis_out, dis_err, dis_rc = run_adb(
                "-s", state.target, "shell", "pm", "disable-user", "--user", "0", google_launcher
            )
            lines = []
            lines.append(f"Step 1 — Home switched to {alt} ({home_activity})")
            lines.append("        ✅ OK" if set_rc == 0 else f"        ❌ {set_err or set_out}")
            lines.append(f"\nStep 2 — Disabled Google launcher ({google_launcher})")
            lines.append(f"        {'✅ Launcher disabled' if dis_rc == 0 else '❌ ' + (dis_err or dis_out)}")
            lines.append("\nPress HOME on your remote — the alternate launcher should open.")
            lines.append("To go back to the Google TV launcher, use the")
            lines.append(f"'Restore Google TV Launcher' button ({google_launcher}).")
            sg.popup_scrolled("\n".join(lines), title="Launcher Swap Result", size=(60, 20))
            break
    window.close()


def _installed_packages():
    """Return the set of package names installed on the connected TV."""
    stdout, _, rc = run_adb("-s", state.target, "shell", "pm", "list", "packages")
    if rc != 0:
        return set()
    packages = set()
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.add(line.split(":", 1)[1])
    return packages


def _disabled_packages():
    """Return the set of package names currently disabled on the connected TV."""
    stdout, _, rc = run_adb("-s", state.target, "shell", "pm", "list", "packages", "-d")
    if rc != 0:
        return set()
    packages = set()
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.add(line.split(":", 1)[1])
    return packages


def _package_statuses():
    """Return a dict: package name -> 'disabled' | 'installed' | 'missing'."""
    installed = _installed_packages()
    disabled = _disabled_packages()
    statuses = {}
    for pkg in installed:
        statuses[pkg] = "disabled" if pkg in disabled else "installed"
    return statuses


def restore_google_launcher():
    if not reconnect_check():
        sg.popup("❌ TV not connected. Use 'Connect to TV' first.")
        return
    installed = _installed_packages()
    google_launcher = _find_google_launcher(installed)
    if google_launcher is None:
        sg.popup("ℹ️ No Google TV launcher found on this device — nothing to restore.")
        return

    disabled = _disabled_packages()
    if google_launcher not in disabled:
        sg.popup(
            f"ℹ️ {google_launcher} is not disabled.\n\n"
            "Press Home (🏠) on your remote — the Google launcher should already be loading."
        )
        return

    en_out, en_err, en_rc = run_adb(
        "-s", state.target, "shell", "pm", "enable", google_launcher
    )
    if en_rc != 0:
        sg.popup(f"❌ Failed to re-enable the Google launcher.\n\n{en_err or en_out}")
        return

    home_activity = None
    stdout, _, rc = run_adb(
        "-s", state.target, "shell", "cmd", "package", "resolve-activity",
        "--brief", "-a", "android.intent.action.MAIN",
        "-c", "android.intent.category.HOME", google_launcher,
    )
    lines_h = [l.strip() for l in stdout.splitlines() if l.strip()]
    if rc == 0 and lines_h:
        home_activity = lines_h[-1]

    lines = [f"✅ Re-enabled {google_launcher}"]
    if home_activity:
        set_out, set_err, set_rc = run_adb(
            "-s", state.target, "shell", "cmd", "package", "set-home-activity", home_activity
        )
        if set_rc == 0:
            lines.append(f"✅ Set it back as the default home ({home_activity})")
            lines.append("\nPress Home (🏠) — the Google TV launcher should now load.")
        else:
            lines.append(f"⚠️ Could not set default home: {set_err or set_out}")
            lines.append(f"\nSet it manually with:\n  adb shell cmd package set-home-activity {home_activity}")
    else:
        lines.append("\nPress Home (🏠) — the Google TV launcher should now load.")
    sg.popup_scrolled("\n".join(lines), title="Launcher Restored", size=(60, 16))


def _run_debloat(app_list):
    """Shared debloat logic: disables each package and returns a result string."""
    installed = _installed_packages()
    output_lines = []
    for label, pkg in app_list:
        if pkg not in installed:
            output_lines.append(f"{label} ({pkg}): ℹ️ Skipped — not installed on this TV")
            continue
        stdout, stderr, rc = run_adb(
            "-s", state.target, "shell", "pm", "disable-user", "--user", "0", pkg
        )
        # Fix 5: use return code, not fragile string matching
        if rc == 0 and "new state: disabled" in stdout:
            status = "✅ Disabled"
        elif "already" in stdout.lower() or "already" in stderr.lower():
            status = "⚠️ Already disabled"
        elif rc != 0:
            detail = (stderr or stdout).strip()
            status = f"❌ Error — {detail}"
        else:
            status = f"⚠️ Unexpected response — {stdout.strip()}"
        output_lines.append(f"{label} ({pkg}): {status}")
    output_lines.append("\nDebloating complete.")
    return "\n".join(output_lines)


def _run_enable(app_list):
    """Shared restore logic: re-enables each package and returns a result string."""
    installed = _installed_packages()
    output_lines = []
    for label, pkg in app_list:
        if pkg not in installed:
            output_lines.append(f"{label} ({pkg}): ℹ️ Skipped — not installed on this TV")
            continue
        stdout, stderr, rc = run_adb(
            "-s", state.target, "shell", "pm", "enable", pkg
        )
        if rc == 0 and ("new state: enabled" in stdout or "already" in stdout.lower()):
            status = "✅ Re-enabled"
        elif rc != 0:
            detail = (stderr or stdout).strip()
            status = f"❌ Error — {detail}"
        else:
            status = f"⚠️ Unexpected response — {stdout.strip()}"
        output_lines.append(f"{label} ({pkg}): {status}")
    output_lines.append("\nRestore complete.")
    return "\n".join(output_lines)


def _debloat_checkbox_rows(app_list, statuses, risk_map=None):
    """Build checkbox rows; mark ✅ enabled, 🔴 disabled, ℹ️ not on this TV."""
    rows = []
    for item in app_list:
        if risk_map is None:
            label, pkg = item
        else:
            label, pkg, risk = item
        state = statuses.get(pkg, "missing")
        mark = {"disabled": "🔴", "installed": "✅"}.get(state, "ℹ️")
        prefix = "" if risk_map is None else f"{risk} "
        rows.append([
            sg.Checkbox(
                f"{mark} {prefix}{label}",
                key=pkg,
                default=state == "installed",
                tooltip=pkg,
            )
        ])
    return rows


def safe_debloat_checklist():
    if not reconnect_check():
        sg.popup("❌ Not connected. Use 'Connect to TV' first.")
        return
    statuses = _package_statuses()
    present = [pkg for _, pkg in safe_apps if pkg in statuses]
    disabled = [pkg for _, pkg in safe_apps if statuses.get(pkg) == "disabled"]
    checkbox_layout = _debloat_checkbox_rows(safe_apps, statuses)
    layout = [
        [sg.Text("Select the safe apps you want to disable  (✅ enabled    🔴 disabled    ℹ️ not on this TV)")],
        [sg.Text(f"{len(present)} of {len(safe_apps)} apps installed   ·   {len(disabled)} already disabled", text_color="blue")],
        [sg.Column(checkbox_layout, scrollable=True, size=(500, 400))],
        [sg.Button("Select All"), sg.Button("Select Only Enabled"), sg.Button("Deselect All")],
        [sg.Button("Apply Selected Changes"), sg.Button("Cancel")],
    ]
    window = sg.Window("Safe Debloat (Choose Apps)", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        elif event == "Select All":
            for _, package in safe_apps:
                if statuses.get(package) == "installed":
                    window[package].update(value=True)
        elif event == "Select Only Enabled":
            for _, package in safe_apps:
                if statuses.get(package) == "installed":
                    window[package].update(value=True)
                else:
                    window[package].update(value=False)
        elif event == "Deselect All":
            for _, package in safe_apps:
                window[package].update(value=False)
        elif event == "Apply Selected Changes":
            selected = [(lbl, pkg) for lbl, pkg in safe_apps if values[pkg]]
            if not selected:
                sg.popup("No apps selected.")
                continue
            output = _run_debloat(selected)
            sg.popup_scrolled(output, title="Safe Debloat Result", size=(60, 20))
            break
    window.close()


def advanced_debloat():
    if not reconnect_check():
        sg.popup("❌ Not connected. Use 'Connect to TV' first.")
        return
    risk_map = {pkg: risk for _, pkg, risk in apps}
    statuses = _package_statuses()
    present = [pkg for _, pkg, _ in apps if pkg in statuses]
    disabled = [pkg for _, pkg, _ in apps if statuses.get(pkg) == "disabled"]
    checkbox_layout = _debloat_checkbox_rows(apps, statuses, risk_map)
    layout = [
        [sg.Text("Legend:  ✅ Safe   ⚠️ Caution   🚫 Critical", text_color="blue")],
        [sg.Text("Row marks:  ✅ enabled    🔴 disabled    ℹ️ not on this TV")],
        [sg.Text(f"{len(present)} of {len(apps)} apps installed   ·   {len(disabled)} already disabled", text_color="blue")],
        [sg.Column(checkbox_layout, scrollable=True, size=(500, 400))],
        [sg.Button("Select All Safe Apps"), sg.Button("Select Only Enabled"), sg.Button("Deselect All")],
        [sg.Button("Apply Selected Changes"), sg.Button("Cancel")],
    ]
    window = sg.Window("Advanced Debloat", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        elif event == "Select All Safe Apps":
            for label, package, risk in apps:
                if risk == "✅" and statuses.get(package) == "installed":
                    window[package].update(value=True)
        elif event == "Select Only Enabled":
            for _, package, _ in apps:
                if statuses.get(package) == "installed":
                    window[package].update(value=True)
                else:
                    window[package].update(value=False)
        elif event == "Deselect All":
            for _, package, _ in apps:
                window[package].update(value=False)
        elif event == "Apply Selected Changes":
            selected = [(lbl, pkg) for lbl, pkg, _ in apps if values[pkg]]
            if not selected:
                sg.popup("No apps selected.")
                continue
            output = _run_debloat(selected)
            sg.popup_scrolled(output, title="Advanced Debloat Result", size=(60, 20))
            break
    window.close()


def restore_debloated_apps():
    if not reconnect_check():
        sg.popup("❌ Not connected. Use 'Connect to TV' first.")
        return
    statuses = _package_statuses()
    all_apps = list(safe_apps) + [(label, pkg) for label, pkg, _ in apps]
    known = {pkg: label for label, pkg in all_apps}
    disabled_only = [
        (label, pkg) for pkg, label in known.items() if statuses.get(pkg) == "disabled"
    ]
    if not disabled_only:
        sg.popup("ℹ️ No debloated (disabled) apps found — nothing to restore.")
        return

    checkbox_layout = [
        [sg.Checkbox(f"🔴 {label}", key=pkg, default=True, tooltip=pkg)]
        for label, pkg in disabled_only
    ]
    layout = [
        [sg.Text("Re-enable apps that were disabled by Safe/Advanced Debloat:")],
        [sg.Text(f"{len(disabled_only)} disabled app(s) found", text_color="blue")],
        [sg.Column(checkbox_layout, scrollable=True, size=(500, 400))],
        [sg.Button("Select All"), sg.Button("Deselect All")],
        [sg.Button("Restore Selected Changes"), sg.Button("Cancel")],
    ]
    window = sg.Window("Restore Debloated Apps", layout)
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Cancel"):
            break
        elif event == "Select All":
            for _, pkg in disabled_only:
                window[pkg].update(value=True)
        elif event == "Deselect All":
            for _, pkg in disabled_only:
                window[pkg].update(value=False)
        elif event == "Restore Selected Changes":
            selected = [(lbl, pkg) for lbl, pkg in disabled_only if values[pkg]]
            if not selected:
                sg.popup("No apps selected.")
                continue
            output = _run_enable(selected)
            sg.popup_scrolled(output, title="Restore Result", size=(60, 20))
            break
    window.close()


def show_safe_debloat_list():
    lines = ["Apps disabled in Safe Debloat mode:\n"]
    for label, package in safe_apps:
        lines.append(f"  • {label}  ({package})")
    sg.popup_scrolled("\n".join(lines), title="Apps Disabled in Safe Debloat Mode", size=(80, 30))


def main_menu():
    layout = [
        [sg.Text("🔴 Not Connected", key="STATUS", text_color="red", font=("Segoe UI", 11, "bold"))],
        [sg.HorizontalSeparator()],
        [sg.Button("Connect to TV")],
        [sg.Button("Pair & Connect (Android 11+ / Chromecast)")],
        [sg.Button("Safe Debloat")],
        [sg.Button("Advanced Debloat")],
        [sg.Button("Restore Debloated Apps")],
        [sg.Button("Install APK")],
        [sg.Button("Disable Google TV Launcher")],
        [sg.Button("Restore Google TV Launcher")],
        [sg.Button("View Safe Debloat App List")],
        [sg.Button("Exit")],
    ]
    window = sg.Window("Android TV Toolkit v1.2", layout)
    while True:
        event, _ = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        elif event == "Connect to TV":
            connect_to_tv()
        elif event == "Pair & Connect (Android 11+ / Chromecast)":
            pair_and_connect()
        elif event == "Safe Debloat":
            safe_debloat_checklist()
        elif event == "Advanced Debloat":
            advanced_debloat()
        elif event == "Restore Debloated Apps":
            restore_debloated_apps()
        elif event == "Install APK":
            install_apk()
        elif event == "Disable Google TV Launcher":
            disable_google_launcher()
        elif event == "Restore Google TV Launcher":
            restore_google_launcher()
        elif event == "View Safe Debloat App List":
            show_safe_debloat_list()
        if state.connected and state.ip:
            window["STATUS"].update(
                f"🟢 Connected to {state.target}", text_color="green"
            )
        else:
            window["STATUS"].update("🔴 Not Connected", text_color="red")
    window.close()


if __name__ == "__main__":
    main_menu()
