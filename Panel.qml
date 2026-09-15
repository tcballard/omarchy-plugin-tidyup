import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui as Ui
import "Navigation.js" as Navigation
import "demo/fixtures/DemoData.js" as DemoData

Item {
  id: root
  property QtObject bar: null
  property Item anchorItem: null
  property var owner: null
  property bool opened: false
  readonly property string instanceId: String(Date.now()) + String(Math.random())
  property bool demo: false
  property string tab: "Apps"
  property var app: null
  property var apps: []
  property var items: []
  property var history: []
  property var selected: ({})
  property string query: ""
  property string status: ""
  property bool failed: false
  property string action: ""
  property string output: ""
  property string confirmation: ""
  property var confirmEntry: null
  property int cursor: 0
  property int rowAction: 0
  readonly property bool busy: worker.running
  readonly property color foreground: bar ? bar.barForeground : Color.foreground
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property int selectedCount: Object.keys(selected).length
  readonly property var rows: tab === "Recovery" ? history : tab === "Apps" && !app ? apps.filter(function(a) {
    return (a.name + " " + a.id).toLowerCase().indexOf(root.query.toLowerCase()) >= 0
  }) : items
  readonly property var targets: Navigation.targets(tab, !!app && tab === "Apps", rows.length, selectedCount, busy)
  readonly property string target: targets[Math.min(cursor, targets.length - 1)] || "tabs"
  readonly property string helper: decodeURIComponent(Qt.resolvedUrl("backend/tidyup.py").toString().replace(/^file:\/\//, ""))

  onTargetsChanged: cursor = Math.min(cursor, targets.length - 1)
  function diagnosticStatus() {
    return {revision: "native-3", instanceId: instanceId, configuredDemo: owner ? owner.setting("demoMode", false) : false, opened: opened, busy: busy, demo: demo, tab: tab, reviewing: !!app,
      rows: rows.length, selected: selectedCount, target: target, failed: failed,
      confirmation: confirmation, confirmIndex: confirmDialog.selectedIndex,
      searchFocused: search.activeFocus, keyFocused: keyCatcher.activeFocus,
      screen: panel.screen ? panel.screen.name : "", x: panel.cardOrigin.x,
      y: panel.cardOrigin.y, width: panel.contentWidth, height: panel.contentHeight}
  }
  function sizeText(bytes, partial) {
    var units = ["B", "KB", "MB", "GB", "TB"], n = Number(bytes || 0), i = 0
    while (n >= 1024 && i < 4) { n /= 1024; i++ }
    return (partial ? "≥ " : "") + n.toFixed(i ? 1 : 0) + " " + units[i]
  }
  function open(payloadJson) {
    if (!opened && !busy) {
      var payload = ({})
      try { if (String(payloadJson || "").length < 4096) payload = JSON.parse(payloadJson || "{}") || ({}) } catch (e) {}
      demo = payload.demo === true
      tab = "Apps"; app = null; items = []; selected = ({}); query = ""; cursor = 0
      if (demo) loadDemo(); else run("catalogue", [])
    }
    opened = true
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }
  function close() { opened = false; confirmation = ""; search.focus = false }
  function loadDemo() {
    apps = DemoData.apps()
    status = "Demo · fictional records; changes disabled."; failed = false
  }
  function run(kind, args) {
    if (busy || demo) return
    action = kind; output = ""; failed = false; status = kind === "scan" ? "Inspecting app folders…" : "Working…"
    worker.command = ["/usr/bin/python3", "-I", helper, kind].concat(args)
    worker.running = true
  }
  function consume(value) {
    if (!value.ok) { failed = true; status = value.error || "Operation failed. Refresh to retry."; return }
    if (action === "catalogue") {
      apps = value.apps; app = null; items = []; selected = ({})
      status = apps.length + " native apps · Arch and AUR"
    } else if (action === "scan") {
      items = value.items; selected = ({})
      status = value.warnings.length ? value.warnings.join("\n") : items.length ? "Close the app before moving any folders." : "No matching folders found."
    } else if (action === "history") {
      history = value.entries
      status = value.warnings.length ? value.warnings.join("\n") : "Restore files or delete them to reclaim space."
    } else {
      status = value.message
      if (value.failures && value.failures.length) { failed = true; status += "\n" + value.failures.join("\n") }
      if (action === "clean") { items = []; selected = ({}) }
      if (action === "restore" || action === "purge") history = history.filter(function(e) { return e.token !== root.confirmEntry.token })
    }
  }
  function chooseApp(value) {
    if (busy) return
    app = value; items = []; selected = ({}); rowAction = 0
    if (demo) items = DemoData.files(value.id); else run("scan", ["--app", value.id])
    setTarget("back")
  }
  function changeTab(value) {
    pointerGate.reset()
    if (busy) return
    tab = value; selected = ({}); app = null; items = []; cursor = 0; rowAction = 0
    if (demo) { if (value === "Apps") loadDemo(); else if (value === "Recovery") history = DemoData.recovery(); else items = []; return }
    if (value === "Recovery") run("history", [])
    else if (value === "Leftovers") run("scan", ["--app", "leftovers"])
    else run("catalogue", [])
  }
  function refresh() {
    if (tab === "Apps" && app) run("scan", ["--app", app.id])
    else changeTab(tab)
  }
  function setTarget(value) {
    var next = targets.indexOf(value)
    if (next >= 0) cursor = next
  }
  function focusSearch() {
    if (tab !== "Apps" || app) changeTab("Apps")
    setTarget("search"); search.forceActiveFocus()
  }
  function move(dx, dy) {
    pointerGate.reset()
    if (confirmation) { confirmDialog.selectedIndex = confirmDialog.selectedIndex === 0 ? 1 : 0; return }
    if (dx) {
      if (target === "tabs") changeTab(["Apps", "Leftovers", "Recovery"][Navigation.moved(["Apps", "Leftovers", "Recovery"].indexOf(tab), dx, 3)])
      else if (tab === "Recovery" && Navigation.rowIndex(target) >= 0) rowAction = Navigation.moved(rowAction, dx, 2)
      return
    }
    cursor = Navigation.moved(cursor, dy, targets.length); rowAction = 0
    var row = Navigation.rowIndex(target)
    if (row >= 0) list.positionViewAtIndex(row, ListView.Contain)
  }
  function ask(kind, entry) {
    if (busy) return
    confirmEntry = entry || null; confirmation = kind; confirmDialog.selectedIndex = 0
    keyCatcher.forceActiveFocus()
  }
  function activate() {
    pointerGate.reset()
    if (confirmation) { if (confirmDialog.selectedIndex === 0) confirmation = ""; else confirmAction(); return }
    if (target === "search") { focusSearch(); return }
    if (target === "back") { app = null; items = []; selected = ({}); setTarget("search"); return }
    if (target === "refresh") { refresh(); return }
    if (target === "uninstall") { ask("uninstall"); return }
    if (target === "clean") { ask("clean"); return }
    var row = Navigation.rowIndex(target)
    if (row < 0 || row >= rows.length || busy) return
    if (tab === "Apps" && !app) chooseApp(rows[row])
    else if (tab === "Recovery") ask(rowAction ? "purge" : "restore", rows[row])
    else selected = Navigation.selectionAfter(selected, rows[row])
  }
  function deleteCurrent() {
    var row = Navigation.rowIndex(target)
    if (tab === "Recovery" && row >= 0 && row < rows.length) ask("purge", rows[row])
  }
  function confirmAction() {
    var kind = confirmation; confirmation = ""
    if (demo) { status = "Demo · no files or packages were changed."; return }
    if (kind === "clean") {
      var chosen = Object.keys(selected).map(function(key) { return {id: key, fingerprint: root.selected[key].fingerprint} })
      run("clean", ["--app", tab === "Leftovers" ? "leftovers" : app.id, "--selection", JSON.stringify(chosen)])
    } else if (kind === "uninstall") run("uninstall", ["--app", app.id])
    else if (kind === "restore" || kind === "purge") run(kind, ["--token", confirmEntry.token])
  }
  Ui.PointerMoveGate { id: pointerGate; referenceItem: keyCatcher }
  Process {
    id: worker
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.output = text }
    stderr: StdioCollector { waitForEnd: true }
    onExited: function(exitCode) {
      try {
        var result = JSON.parse(root.output)
        if (exitCode !== 0 && result.ok) throw new Error("Helper failed")
        root.consume(result)
      } catch (e) { root.failed = true; root.status = "Unable to complete operation. Refresh to retry." }
    }
  }
  Ui.KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    bar: root.bar
    owner: root.owner || root
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(510))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)
    Ui.PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      blocked: search.activeFocus
      onMoveRequested: function(dx, dy) { root.move(dx, dy) }
      onActivateRequested: root.activate()
      onCloseRequested: { if (root.confirmation) root.confirmation = ""; else root.close() }
      onDeleteRequested: root.deleteCurrent()
      onTabRequested: function(direction) {
        if (root.confirmation) root.move(direction, 0)
        else if (root.owner) root.owner.switchPanel(direction)
      }
      onTextKey: function(t) {
        if (root.confirmation) return
        if (t === "/" || t === "f" || t === "\u0006") root.focusSearch()
        else if (t === "1" || t === "2" || t === "3") root.changeTab(["Apps", "Leftovers", "Recovery"][Number(t) - 1])
        else if (t === "r") root.refresh()
      }
      Keys.onReleased: function(event) {
        if (search.activeFocus) return
        if (event.key === Qt.Key_Delete) { root.deleteCurrent(); event.accepted = true }
        if (event.key === Qt.Key_Backspace && root.app && !root.confirmation) {
          root.app = null; root.items = []; root.selected = ({}); root.setTarget("search"); event.accepted = true
        }
      }
      Column {
        id: column
        width: parent.width
        spacing: Style.spacing.md
        enabled: !root.confirmation
        Ui.PanelHero {
          title: "TidyUp"
          meta: root.busy ? "Working…" : root.tab === "Apps" && root.app ? root.app.name : "Apps · leftovers · recovery"
          foreground: root.foreground; fontFamily: root.fontFamily
          iconComponent: Component { Text { text: "\uf1f8"; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.display } }
          trailingControl: Component { Ui.Button { text: "×"; tooltipText: "Close · Esc"; foreground: root.foreground; onClicked: root.close() } }
        }
        Ui.PanelSeparator { foreground: root.foreground }
        Row {
          width: parent.width; spacing: Style.spacing.sm
          Repeater {
            model: ["Apps", "Leftovers", "Recovery"]
            Ui.Button {
              required property string modelData
              text: modelData; selected: root.tab === modelData
              hasCursor: root.target === "tabs" && root.tab === modelData
              foreground: root.foreground; fontFamily: root.fontFamily
              enabled: !root.busy
              MouseArea {
                anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
                onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("tabs") }
              }
              onClicked: { root.changeTab(modelData); keyCatcher.forceActiveFocus() }
            }
          }
        }
        Ui.TextField {
          id: search
          width: parent.width
          visible: root.tab === "Apps" && !root.app
          placeholderText: "Search apps…  /"
          foreground: root.foreground; font.family: root.fontFamily
          hasCursor: root.target === "search"
          text: root.query
          onTextChanged: root.query = text
          Keys.onEscapePressed: { keyCatcher.forceActiveFocus(); root.setTarget("search") }
          Keys.onDownPressed: { keyCatcher.forceActiveFocus(); root.setTarget(root.rows.length ? "row:0" : "refresh") }
          Keys.onReturnPressed: { keyCatcher.forceActiveFocus(); root.setTarget(root.rows.length ? "row:0" : "refresh"); root.activate() }
          Keys.onTabPressed: { keyCatcher.forceActiveFocus(); root.setTarget(root.rows.length ? "row:0" : "refresh") }
          Keys.onBacktabPressed: { keyCatcher.forceActiveFocus(); root.setTarget("tabs") }
        }
        Ui.Button {
          visible: root.tab === "Apps" && !!root.app
          text: "‹  All apps"; foreground: root.foreground; hasCursor: root.target === "back"
          MouseArea {
              anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
              onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("back") }
            }
          onClicked: { root.setTarget("back"); root.activate(); keyCatcher.forceActiveFocus() }
        }
        Ui.PanelSectionHeader {
          width: parent.width
          text: root.tab === "Recovery" ? "SAVED FILES" : root.tab === "Apps" && !root.app ? "INSTALLED APPS" : "REVIEW FILES"
          foreground: root.foreground; fontFamily: root.fontFamily
        }
        Text {
          visible: root.tab === "Leftovers"
          width: parent.width
          text: "Native packages are absent. Other app installations may still use these folders."
          wrapMode: Text.WordWrap; color: root.foreground; opacity: .65; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
        }
        ListView {
          id: list
          width: parent.width
          height: Math.min(Style.space(290), Math.max(Style.space(100), contentHeight), Math.max(Style.space(80), panel.availableCardHeight - Style.space(370)))
          model: root.rows; clip: true; spacing: Style.spacing.xs
          delegate: Ui.Button {
            id: row
            required property var modelData
            required property int index
            readonly property bool appRow: root.tab === "Apps" && !root.app
            readonly property bool hasRowCursor: root.target === "row:" + index
            width: list.width
            implicitHeight: rowContent.implicitHeight + Style.spacing.controlPaddingY * 2 + Style.space(8)
            text: ""; foreground: root.foreground
            hasCursor: hasRowCursor
            selected: !appRow && !!root.selected[modelData.id]
            MouseArea {
              anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
              onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("row:" + row.index) }
            }
            onClicked: { root.setTarget("row:" + index); root.activate(); keyCatcher.forceActiveFocus() }
            Column {
              id: rowContent
              anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
              anchors.margins: Style.spacing.controlPaddingX
              spacing: Style.spacing.xs
              RowLayout {
                width: parent.width
                Text {
                  Layout.fillWidth: true; textFormat: Text.PlainText
                  text: row.appRow ? row.modelData.name : (root.tab === "Recovery" ? "" : root.selected[row.modelData.id] ? "☑  " : "☐  ") + row.modelData.kind
                  color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.font.body; elide: Text.ElideRight
                }
                Text {
                  text: row.appRow ? "›" : root.sizeText(row.modelData.bytes, row.modelData.partial)
                  color: root.foreground; opacity: .65; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
                }
              }
              Text {
                width: parent.width; textFormat: Text.PlainText
                text: row.appRow ? row.modelData.id : row.modelData.path
                elide: Text.ElideMiddle; color: root.foreground; opacity: .6; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
              }
              Text {
                visible: !row.appRow; width: parent.width; textFormat: Text.PlainText
                text: root.tab === "Recovery" ? "Saved " + (row.modelData.date || "") : row.modelData.reason || ""
                wrapMode: Text.WordWrap; color: root.foreground; opacity: .6; font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
              }
              Row {
                visible: root.tab === "Recovery"; spacing: Style.spacing.sm
                Ui.Button {
                  text: "Restore"; hasCursor: row.hasRowCursor && root.rowAction === 0; foreground: root.foreground
                  onClicked: root.ask("restore", row.modelData)
                }
                Ui.Button {
                  text: "Delete…"; hasCursor: row.hasRowCursor && root.rowAction === 1; foreground: root.foreground
                  onClicked: root.ask("purge", row.modelData)
                }
              }
            }
          }
          Text {
            anchors.centerIn: parent; width: parent.width; visible: root.rows.length === 0
            text: root.busy ? "Loading…" : root.failed ? "Unable to load. Refresh to retry." : root.tab === "Recovery" ? "Nothing in Recovery" : root.query && !root.app ? "No matching apps" : "No matching files"
            color: root.foreground; opacity: .6; font.family: root.fontFamily; font.pixelSize: Style.font.body
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
          }
        }
        Ui.PanelSeparator { foreground: root.foreground }
        Row {
          width: parent.width; spacing: Style.spacing.sm
          Ui.Button {
            text: "Refresh"; foreground: root.foreground; hasCursor: root.target === "refresh"; enabled: !root.busy
            MouseArea {
              anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
              onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("refresh") }
            }
            onClicked: root.refresh()
          }
          Ui.Button {
            text: "Uninstall…"; foreground: root.foreground; hasCursor: root.target === "uninstall"
            visible: root.tab === "Apps" && !!root.app; enabled: !root.busy
            MouseArea {
              anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
              onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("uninstall") }
            }
            onClicked: root.ask("uninstall")
          }
          Ui.Button {
            text: "Move " + root.selectedCount + " to Recovery…"; foreground: root.foreground; hasCursor: root.target === "clean"
            visible: root.selectedCount > 0; enabled: !root.busy
            MouseArea {
              anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
              onPositionChanged: function(mouse) { if (pointerGate.moved(parent, mouse)) root.setTarget("clean") }
            }
            onClicked: root.ask("clean")
          }
        }
        Text {
          width: parent.width; textFormat: Text.PlainText; text: root.status
          color: root.failed ? Color.urgent : root.foreground; opacity: root.failed ? 1 : .65
          font.family: root.fontFamily; font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight
        }
        Text {
          width: parent.width
          text: "↑↓ / j k Navigate · Enter Select · / Search · Esc Close"
          color: root.foreground; opacity: .5; font.family: root.fontFamily; font.pixelSize: Style.font.caption
          wrapMode: Text.WordWrap
        }
      }
      Ui.ConfirmDialog {
        id: confirmDialog
        anchors.fill: parent; opened: root.confirmation !== ""
        foreground: root.foreground; fontFamily: root.fontFamily
        selectedIndex: 0
        message: root.confirmation === "clean" ? "Move " + root.selectedCount + " selected folder(s) to Recovery? Close the app first. Settings and sessions may reset. Files still use disk space until deleted."
          : root.confirmation === "purge" ? "Permanently delete this recovery item? This cannot be undone.\n" + (root.confirmEntry ? root.confirmEntry.path : "")
          : root.confirmation === "restore" ? "Restore this folder? Close the app first. Existing files will not be overwritten."
          : "Open package removal for " + (root.app ? root.app.id : "") + "? Review and confirm the transaction in the terminal."
        confirmText: root.confirmation === "clean" ? "Move" : root.confirmation === "restore" ? "Restore" : root.confirmation === "purge" ? "Delete" : "Open"
        onCanceled: root.confirmation = ""
        onConfirmed: root.confirmAction()
      }
    }
  }
}
