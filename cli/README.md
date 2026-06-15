# refaver

Reset Safari's cached favicons for a site — without Terminal gymnastics.

Safari caches favicons in a private, TCC-protected store that survives "Clear
History," cache emptying, and hard reloads. During local development a changed
favicon can stay stuck for days. `refaver` fixes it in one command.

> macOS only · Safari 14+ · requires Full Disk Access for your terminal

```bash
refaver doctor                        # check Full Disk Access + paths
refaver reset http://localhost:5173   # soft, non-destructive (quit Safari first)
```

Commands: `reset` (soft default, `--hard` to delete), `gc`, `nuke`, `doctor`.
Every mutating command backs up the database first.

Full documentation, the reverse-engineering write-up, and contribution guide:
https://github.com/icy-house/refaver
