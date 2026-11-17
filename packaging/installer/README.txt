KNC BOINC installer (Windows 10/11, built-in Windows PowerShell 5.1)

Extract the whole folder to a writable local folder outside the BOINC data directory.
Keep package, scripts and launchers together. No Python or runtime download is needed.
Double-click Install KNC BOINC.cmd and approve UAC. Review data/install paths and
card settings in the form, then confirm the change. On updates, the installed
knc_wrapper.cfg is preserved byte for byte. Keep the SSH private key outside this folder.
Windows OpenSSH Client, BOINC and attachment to MilkyWay must already be provisioned.
The BOINC account must be able to read its key and known_hosts, including for services.

Uninstall KNC BOINC.cmd removes recorded KNC files, keeping stock files and tasks.
Restore KNC BOINC backup.cmd asks for a backup folder containing backup.json and data.
Restore replaces ALL BOINC state; avoid replaying already reported tasks from old state.
Every operation saves the current data first. Keep backups and logs for review.
Foreign app_info.xml/app_config.xml cause refusal without changing BOINC data.
Older manual installations have no ownership marker and need lead review first.
Shutdown waits 90 seconds and never kills a process. If it times out, close the
BOINC client through Manager and retry. Backups/logs live next to these launchers.
Client/Manager restart is requested through the interactive Windows desktop.
If restart fails, the dialog retains the result and backup path; open Manager from Start.
See docs/TRY-IT.md in the source checkout for the offline sample and owner checks.
