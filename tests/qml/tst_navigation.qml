import QtQuick
import QtTest
import "../../Navigation.js" as Navigation
import "../../demo/fixtures/DemoData.js" as DemoData

TestCase {
  name: "TidyUpKeyboardNavigation"
  function test_all_apps_reachable() {
    var targets = Navigation.targets("Apps", false, 100, 0, false)
    compare(targets[0], "tabs")
    compare(targets[1], "search")
    compare(targets[101], "row:99")
    compare(targets[102], "refresh")
  }
  function test_cleanup_actions_reachable() {
    var targets = Navigation.targets("Apps", true, 2, 1, false)
    verify(targets.indexOf("back") >= 0)
    verify(targets.indexOf("uninstall") >= 0)
    verify(targets.indexOf("clean") >= 0)
    compare(Navigation.targets("Apps", true, 2, 1, true).indexOf("clean"), -1)
  }
  function test_recovery_and_empty_states() {
    compare(Navigation.targets("Recovery", false, 0, 0, false), ["tabs", "refresh"])
    compare(Navigation.rowIndex("row:14"), 14)
    compare(Navigation.rowIndex("refresh"), -1)
  }
  function test_demo_fixture() {
    compare(DemoData.apps().length, 4)
    compare(DemoData.files("chromium").length, 2)
    compare(DemoData.recovery()[0].token, "fictional")
  }
  function test_boundaries() {
    compare(Navigation.moved(0, -1, 5), 0)
    compare(Navigation.moved(4, 1, 5), 4)
    compare(Navigation.moved(3, -1, 5), 2)
    compare(Navigation.moved(0, 1, 0), 0)
  }
  function test_selection_parity() {
    var selected = Navigation.selectionAfter({}, {id:"Cache:example"})
    compare(Object.keys(selected).length, 1)
    var cleared = Navigation.selectionAfter(selected, {id:"Cache:example"})
    compare(Object.keys(cleared).length, 0)
    compare(Object.keys(selected).length, 1)
  }
}
