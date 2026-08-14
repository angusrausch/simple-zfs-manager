# Simple ZFS Manager

A lightweight, no-database NAS management tool designed for ARM-based hardware and minimal overhead.

I wanted to move my NAS setup to a Raspberry Pi, but TrueNAS does not support the platform natively. Simple ZFS Manager is my solution: a straightforward web interface for managing ZFS datasets, snapshots, and network shares without the bloat of a full operating system distribution.

---

## Design Philosophy

The project is built around being unopinionated and lightweight, serving as a clean management layer rather than a restrictive ecosystem.

*   **No Database:** System state is determined directly from the underlying OS configuration. This avoids sync issues and prevents data corruption caused by a broken software state.
*   **System-Native Auth:** Uses Linux PAM authentication. Your system users are your web interface users.
*   **Direct File Modification:** Configuration changes (such as Samba or NFS exports) are written directly to system files safely and predictably.
*   **Target Audience:** Users running low-compute or ARM-based hardware (like the Raspberry Pi), or home lab hobbyists who want a simple web UI over ZFS without handing total control of their Linux installation over to OpenMediaVault or TrueNAS.

### Tech Stack
*   **Backend:** Python 3 with Flask
*   **Frontend:** Plain JavaScript, HTML, and CSS
*   **Authentication:** PAM (Pluggable Authentication Modules)

---

## Technical Scope

The tool interacts directly with standard Linux CLI utilities to expose a web-based management layer for:

*   **ZFS Lifecycle:** Dataset creation, deletion, capacity tracking, and tuning properties.
*   **Data Protection:** Automated snapshotting schedules and dataset replication tasks.
*   **Network Storage:** Generating and managing SMB (Samba) and NFS shares natively.

---

## Roadmap

- [ ] Initialize Flask application boilerplate
- [ ] Implement PAM authentication and session handling for the login page
- [ ] Integrate core ZFS dataset parsing and creation controls
- [ ] Implement ZFS snapshot management and replication triggers
- [ ] Integrate SMB share parsing and file generation
- [ ] Integrate NFS share parsing and export configuration
- [ ] Harden security model (mitigate raw root-privilege execution)

---

## Contributing

This is a personal, spare-time project. If you are interested in the design concepts, want to test it on your own ARM hardware, or want to suggest architecture improvements, please open an Issue or start a Discussion thread.
