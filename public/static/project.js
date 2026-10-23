const root = document.getElementById('project')
const slug = root.dataset.slug
const KEY = `bsb:key:${slug}`
const POLL_MS = 4000
const reduced = matchMedia('(prefers-reduced-motion: reduce)')
const $ = (id) => document.getElementById(id)
const SVGNS = 'http://www.w3.org/2000/svg'

let state = null
let version = 0
let editKey = ''
let lastSync = 0

const hashKey = new URLSearchParams(location.hash.slice(1)).get('key')
if (hashKey) {
  localStorage.setItem(KEY, hashKey)
  history.replaceState(null, '', location.pathname)
}
editKey = localStorage.getItem(KEY) || ''

function el(tag, attrs = {}, text) {
  const n = document.createElement(tag)
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v)
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? '' : v)
  }
  if (text !== undefined) n.textContent = text
  return n
}

function svg(tag, attrs = {}) {
  const n = document.createElementNS(SVGNS, tag)
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v)
  return n
}

async function api(path, opts = {}) {
  const res = await fetch(`/api/projects/${slug}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(editKey ? { 'x-edit-key': editKey } : {}), ...(opts.headers || {}) }
  })
  const data = res.headers.get('content-type')?.includes('json') ? await res.json() : await res.text()
  if (!res.ok) {
    if (res.status === 401) setEditor(false, 'That captain key does not match this bottle.')
    throw new Error(data.error || res.statusText)
  }
  return data
}

function wavePath(y) {
  return `M30 ${y} q30 -10 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 V260 H30 Z`
}

function drawBottle(p) {
  const s = $('bottle')
  s.querySelectorAll(':scope > :not(desc)').forEach((n) => n.remove())
  const defs = svg('defs')
  const clip = svg('clipPath', { id: 'glass-clip' })
  clip.append(svg('rect', { x: 30, y: 40, width: 480, height: 220, rx: 90 }))
  const hatch = svg('pattern', { id: 'hatch', width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(35)' })
  hatch.append(svg('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: '#2b1e12', 'stroke-width': 1, opacity: 0.35 }))
  defs.append(clip, hatch)
  s.append(defs)
  s.append(svg('rect', { x: 120, y: 268, width: 300, height: 18, rx: 4, fill: '#6b4a2b' }))
  s.append(svg('rect', { x: 120, y: 268, width: 300, height: 18, rx: 4, fill: 'url(#hatch)' }))
  const glass = svg('g', { 'clip-path': 'url(#glass-clip)' })
  glass.append(svg('rect', { x: 30, y: 40, width: 480, height: 220, fill: '#e9e2cc' }))
  const waveY = 246 - 96 * (p.percent / 100)
  glass.append(svg('path', { d: wavePath(waveY), fill: '#2f6a73' }))
  glass.append(svg('path', { d: wavePath(waveY), fill: 'url(#hatch)' }))
  const ms = p.milestones
  const n = Math.max(1, ms.length)
  const hullY = waveY - 2
  const hullX0 = 110, hullX1 = 430
  const ship = svg('g', { class: 'ship' })
  ship.append(svg('path', { d: `M${hullX0} ${hullY - 18} L${hullX1} ${hullY - 18} L${hullX1 - 30} ${hullY + 8} L${hullX0 + 20} ${hullY + 8} Z`, fill: '#5a3a22', stroke: '#2b1e12', 'stroke-width': 2 }))
  const span = (hullX1 - hullX0 - 40) / n
  ms.forEach((m, i) => {
    const cx = hullX0 + 20 + span * (i + 0.5)
    const top = Math.max(48, hullY - 150)
    ship.append(svg('line', { x1: cx, y1: top, x2: cx, y2: hullY - 18, stroke: '#2b1e12', 'stroke-width': 2 }))
    const h = (hullY - 30 - top) * (0.25 + 0.75 * m.ratio)
    const w = Math.min(span * 0.42, 34)
    const sail = svg('path', { d: `M${cx - w} ${hullY - 26} Q${cx} ${hullY - 26 - h * 0.55} ${cx - w + 2} ${hullY - 26 - h} L${cx + w - 2} ${hullY - 26 - h} Q${cx + w * 1.2} ${hullY - 26 - h * 0.5} ${cx + w} ${hullY - 26} Z`, fill: m.total > 0 && m.done === m.total ? '#b08434' : '#f4ecd6', stroke: '#2b1e12', 'stroke-width': 1.5 })
    const t = svg('title')
    t.textContent = `${m.title}: ${m.done}/${m.total}`
    sail.append(t)
    ship.append(sail)
  })
  glass.append(ship)
  s.append(glass)
  s.append(svg('rect', { x: 30, y: 40, width: 480, height: 220, rx: 90, fill: 'none', stroke: '#2b1e12', 'stroke-width': 4 }))
  s.append(svg('path', { d: 'M70 70 Q150 52 260 56', fill: 'none', stroke: '#fffaf0', 'stroke-width': 5, 'stroke-linecap': 'round', opacity: 0.7 }))
  s.append(svg('rect', { x: 506, y: 112, width: 70, height: 76, rx: 10, fill: '#2b1e12' }))
  s.append(svg('rect', { x: 512, y: 118, width: 92, height: 64, rx: 8, fill: '#8a5a32' }))
  for (let i = 0; i < 6; i++) s.append(svg('line', { x1: 520 + i * 14, y1: 120, x2: 514 + i * 14, y2: 180, stroke: '#2b1e12', 'stroke-width': 1.2, opacity: 0.5 }))
  if (!reduced.matches) {
    s.classList.remove('settle')
    void s.getBoundingClientRect()
    s.classList.add('settle')
  }
}

function statusLabel(s) {
  return s === 'done' ? 'Done' : s === 'doing' ? 'Doing' : 'To do'
}

function memberSelect(attrs, members, selected) {
  const sel = el('select', attrs)
  sel.append(el('option', { value: '' }, 'Unassigned'))
  for (const mem of members) sel.append(el('option', { value: mem.id, selected: mem.id === selected }, mem.name))
  return sel
}

function render() {
  const { project, progress: p, milestones, tasks, members, activity } = state
  document.title = `${project.title}: ${p.percent}% · Bote sa Bote`
  $('title').textContent = project.title
  $('team').textContent = project.team || 'Capstone team'
  $('pct').textContent = p.percent.toFixed(1).replace(/\.0$/, '')
  $('pct-detail').textContent = `${p.tasksDone} of ${p.tasksTotal} tasks done · ${p.sails} of ${milestones.length} sails full · weighted ${p.exact}`
  drawBottle(p)
  const editable = Boolean(editKey)
  const memberName = new Map(members.map((m) => [m.id, m.name]))
  const ol = $('milestones')
  ol.replaceChildren()
  if (milestones.length === 0) ol.append(el('li', { class: 'empty' }, editable ? 'No milestones yet. Add your first sail below.' : 'No milestones yet.'))
  for (const m of p.milestones) {
    const li = el('li', { class: 'milestone' })
    const head = el('div', { class: 'ms-head' })
    head.append(el('h3', {}, m.title))
    head.append(el('span', { class: 'ms-count' }, `${m.done}/${m.total}${m.weight > 1 ? ` · ×${m.weight}` : ''}${m.due_date ? ` · due ${m.due_date}` : ''}`))
    if (editable) head.append(el('button', { class: 'btn small ghost', 'aria-label': `Delete milestone ${m.title}`, onclick: () => confirm(`Delete "${m.title}" and its tasks?`) && mutate(`/milestones/${m.id}`, { method: 'DELETE' }) }, 'Delete'))
    li.append(head)
    const meter = el('div', { class: 'meter', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': 100, 'aria-valuenow': Math.round(m.ratio * 100), 'aria-label': `${m.title} progress` })
    meter.append(el('span', { style: `inline-size:${(m.ratio * 100).toFixed(1)}%` }))
    li.append(meter)
    const ul = el('ul', { class: 'tasks' })
    for (const t of tasks.filter((x) => x.milestone_id === m.id)) {
      const row = el('li', { class: `task ${t.status}` })
      if (editable) {
        const sel = el('select', { 'aria-label': `Status of ${t.title}`, onchange: (e) => mutate(`/tasks/${t.id}`, { method: 'PATCH', body: JSON.stringify({ status: e.target.value }) }) })
        for (const v of ['todo', 'doing', 'done']) sel.append(el('option', { value: v, selected: v === t.status }, statusLabel(v)))
        row.append(sel, el('span', { class: 'task-title' }, t.title))
        row.append(memberSelect({ 'aria-label': `Assignee of ${t.title}`, onchange: (e) => mutate(`/tasks/${t.id}`, { method: 'PATCH', body: JSON.stringify({ member_id: e.target.value || null }) }) }, members, t.member_id))
        row.append(el('button', { class: 'btn small ghost', 'aria-label': `Delete task ${t.title}`, onclick: () => mutate(`/tasks/${t.id}`, { method: 'DELETE' }) }, '✕'))
      } else {
        row.append(el('span', { class: `chip ${t.status}` }, statusLabel(t.status)), el('span', { class: 'task-title' }, t.title), el('span', { class: 'who' }, memberName.get(t.member_id) || 'Unassigned'))
      }
      ul.append(row)
    }
    li.append(ul)
    if (editable) {
      const f = el('form', { class: 'inline-form' })
      const lab = el('label', { class: 'grow' })
      lab.append(document.createTextNode('New task'), el('input', { name: 'title', maxlength: 100, required: true }))
      f.append(lab, memberSelect({ name: 'member_id', 'aria-label': 'Assign to' }, members, null), el('button', { class: 'btn' }, 'Add task'))
      f.addEventListener('submit', (e) => {
        e.preventDefault()
        const fd = new FormData(f)
        mutate('/tasks', { method: 'POST', body: JSON.stringify({ milestone_id: m.id, title: fd.get('title'), member_id: fd.get('member_id') || null }) })
      })
      li.append(f)
    }
    ol.append(li)
  }
  const crew = $('crew')
  crew.replaceChildren()
  if (p.members.length === 0) crew.append(el('li', { class: 'empty' }, 'No crew listed yet.'))
  for (const m of p.members) {
    const li = el('li', { class: 'member' })
    li.append(el('strong', {}, m.name))
    if (m.role) li.append(el('span', { class: 'role' }, m.role))
    li.append(el('span', { class: 'stat' }, `${m.done} done · ${m.doing} doing · ${m.total} assigned`))
    if (editable) li.append(el('button', { class: 'btn small ghost', 'aria-label': `Remove ${m.name}`, onclick: () => confirm(`Remove ${m.name}? Their tasks become unassigned.`) && mutate(`/members/${m.id}`, { method: 'DELETE' }) }, 'Remove'))
    crew.append(li)
  }
  const log = $('activity')
  log.replaceChildren()
  for (const a of activity) {
    const li = el('li')
    li.append(el('time', { datetime: a.created_at }, new Date(a.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })))
    li.append(document.createTextNode(' ' + a.text))
    log.append(li)
  }
  document.querySelectorAll('.editor-only').forEach((n) => { n.hidden = !editable })
}

function setEditor(on, msg) {
  if (!on) {
    editKey = ''
    localStorage.removeItem(KEY)
  }
  $('captain-status').textContent = msg || (on ? 'Captain mode: this device can edit.' : 'View only. Paste the captain key to edit.')
  $('key-form').hidden = on
  $('lock-btn').hidden = !on
  if (state) render()
}

function stamp() {
  const s = Math.round((Date.now() - lastSync) / 1000)
  $('sync').textContent = navigator.onLine ? `Live · synced ${s < 5 ? 'just now' : s + ' s ago'}` : 'Offline · showing last synced data'
}

async function load() {
  state = await api('')
  version = state.project.version
  lastSync = Date.now()
  render()
  stamp()
}

async function mutate(path, opts) {
  try {
    await api(path, opts)
    await load()
  } catch (x) {
    $('share-note').textContent = `Change not saved (${x.message}).`
  }
}

async function poll() {
  if (document.visibilityState === 'visible' && navigator.onLine) {
    try {
      const v = await api('/version')
      lastSync = Date.now()
      if (v.version !== version) await load()
    } catch {}
  }
  stamp()
  setTimeout(poll, POLL_MS)
}

async function copy(text, label) {
  try {
    await navigator.clipboard.writeText(text)
    $('share-note').textContent = `${label} copied. Paste it in your Messenger group chat.`
  } catch {
    $('share-note').textContent = 'Copy blocked by the browser. Long-press the address bar to copy the link.'
  }
}

const viewUrl = `${location.origin}/p/${slug}`
$('copy-link').addEventListener('click', () => copy(viewUrl, 'View link'))
$('copy-summary').addEventListener('click', async () => copy(await api('/summary'), 'Progress text'))
$('share-btn').addEventListener('click', async () => {
  const text = await api('/summary')
  if (navigator.share) {
    try { await navigator.share({ title: state?.project.title, text, url: viewUrl }); return } catch (x) { if (x.name === 'AbortError') return }
  }
  copy(text, 'Progress text')
})
$('key-form').addEventListener('submit', async (e) => {
  e.preventDefault()
  const k = new FormData(e.target).get('key').toString().trim()
  if (!k) return
  editKey = k
  try {
    await api('/verify', { method: 'POST' })
    localStorage.setItem(KEY, k)
    setEditor(true)
  } catch {}
})
$('lock-btn').addEventListener('click', () => setEditor(false))
$('add-member').addEventListener('submit', (e) => {
  e.preventDefault()
  const fd = new FormData(e.target)
  mutate('/members', { method: 'POST', body: JSON.stringify({ name: fd.get('name'), role: fd.get('role') }) }).then(() => e.target.reset())
})
$('add-milestone').addEventListener('submit', (e) => {
  e.preventDefault()
  const fd = new FormData(e.target)
  mutate('/milestones', { method: 'POST', body: JSON.stringify({ title: fd.get('title'), weight: Number(fd.get('weight')) || 1, due_date: fd.get('due_date') || null }) }).then(() => e.target.reset())
})
addEventListener('online', stamp)
addEventListener('offline', stamp)
document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && load().catch(() => {}))

;(async () => {
  try {
    await load()
    if (editKey) {
      try { await api('/verify', { method: 'POST' }); setEditor(true) } catch {}
    } else setEditor(false)
  } catch (x) {
    $('title').textContent = 'Could not load this bottle'
    $('sync').textContent = `Error: ${x.message}. Retrying…`
  }
  setTimeout(poll, POLL_MS)
})()
