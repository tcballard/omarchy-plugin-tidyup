.pragma library

function apps() {
  return [{id: "chromium", name: "Chromium"}, {id: "obsidian", name: "Obsidian"},
    {id: "spotify", name: "Spotify"}, {id: "vlc", name: "VLC media player"}]
}
function files(appId) {
  return [{id: "Cache:example", kind: "Cache", path: "~/.cache/" + appId, bytes: 485490688,
    reason: "Known app folder. Review before cleanup."},
    {id: "Settings:example", kind: "Settings", path: "~/.config/" + appId, bytes: 132120576,
    reason: "Profiles, preferences and saved sessions."}]
}
function recovery() {
  return [{id: "Cache:example", token: "fictional", kind: "Cache", path: "~/.cache/example-app",
    bytes: 67108864, date: "2026-09-14 09:00"}]
}
