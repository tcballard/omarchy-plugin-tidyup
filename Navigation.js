.pragma library

function targets(tab, reviewing, rowCount, selectedCount, busy) {
  var result = ["tabs"]
  if (tab === "Apps") result.push(reviewing ? "back" : "search")
  for (var i = 0; i < rowCount; i++) result.push("row:" + i)
  result.push("refresh")
  if (!busy && reviewing) result.push("uninstall")
  if (!busy && selectedCount > 0) result.push("clean")
  return result
}
function moved(index, delta, count) { return Math.max(0, Math.min(Math.max(0, count - 1), index + delta)) }
function rowIndex(target) { return target && target.indexOf("row:") === 0 ? Number(target.slice(4)) : -1 }
function selectionAfter(selected, item) {
  var next = Object.assign({}, selected)
  if (next[item.id]) delete next[item.id]
  else next[item.id] = item
  return next
}
