const form = document.getElementById('launch-form')
const err = document.getElementById('launch-error')
const lines = (v) => v.split('\n').map((s) => s.trim()).filter(Boolean)
const RECENT = 'bsb:recent'

function recent() {
  try { return JSON.parse(localStorage.getItem(RECENT) || '[]') } catch { return [] }
}

function renderRecent() {
  const list = recent()
  const ul = document.getElementById('recent-list')
  ul.replaceChildren()
  for (const r of list) {
    const li = document.createElement('li')
    const a = document.createElement('a')
    a.href = `/p/${r.slug}`
    a.textContent = r.title
    li.append(a)
    ul.append(li)
  }
  document.getElementById('recent').hidden = list.length === 0
}

form.addEventListener('submit', async (e) => {
  e.preventDefault()
  err.hidden = true
  const fd = new FormData(form)
  const title = String(fd.get('title') || '').trim()
  if (!title) {
    err.textContent = 'Add your thesis title first.'
    err.hidden = false
    form.title.focus()
    return
  }
  const btn = form.querySelector('button[type=submit]')
  btn.disabled = true
  btn.textContent = 'Launching…'
  try {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, team: fd.get('team'), members: lines(String(fd.get('members') || '')), milestones: lines(String(fd.get('milestones') || '')) })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'launch_failed')
    localStorage.setItem(`bsb:key:${data.slug}`, data.editKey)
    localStorage.setItem(RECENT, JSON.stringify([{ slug: data.slug, title }, ...recent().filter((r) => r.slug !== data.slug)].slice(0, 8)))
    document.getElementById('edit-link').value = location.origin + data.editUrl
    document.getElementById('view-link').value = location.origin + data.viewUrl
    document.getElementById('open-edit').href = data.viewUrl
    document.getElementById('launched').hidden = false
    document.getElementById('launch-panel').hidden = true
    renderRecent()
    document.getElementById('launched').scrollIntoView({ block: 'start' })
  } catch (x) {
    err.textContent = `Could not launch the bottle (${x.message}). Check your connection and try again.`
    err.hidden = false
  } finally {
    btn.disabled = false
    btn.textContent = 'Launch bottle'
  }
})

document.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-copy]')
  if (!b) return
  const input = document.getElementById(b.dataset.copy)
  try {
    await navigator.clipboard.writeText(input.value)
    b.textContent = 'Copied'
  } catch {
    input.select()
    b.textContent = 'Press Ctrl+C to copy'
  }
})

renderRecent()
