import QtQuick
import Quickshell.Io
import qs.Commons
import qs.Ui as Ui

Ui.BarWidget {
  id: root
  moduleName: "io.github.tcballard.tidyup"
  property string omarchyPath: ""
  property var shell: null
  property var manifest: null
  property bool popoutSwitching: false
  property bool popoutSwitchClosing: false
  readonly property bool opened: view.opened
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  function open() { view.open(JSON.stringify({demo: root.setting("demoMode", false)})) }
  function close() { view.close() }
  function toggle() { opened ? close() : open() }
  function closeForPopoutSwitch() {
    popoutSwitchClosing = true
    close()
    Qt.callLater(function() { root.popoutSwitchClosing = false })
  }
  function switchPanel(direction) {
    return bar && bar.switchPanelFrom ? bar.switchPanelFrom(root, direction) : false
  }
  IpcHandler {
    target: root.moduleName
    // Read-only, bounded diagnostics for lifecycle tests; no file paths or records.
    function status(): string { return JSON.stringify(view.diagnosticStatus()) }
  }
  Ui.WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\uf1f8"
    fontSize: Style.font.icon
    active: root.opened
    tooltipText: "TidyUp · apps, leftovers and recovery"
    onPressed: function(mouseButton) { if (mouseButton === Qt.LeftButton) root.toggle() }
  }
  Panel {
    id: view
    bar: root.bar
    anchorItem: button
    owner: root
  }
}
