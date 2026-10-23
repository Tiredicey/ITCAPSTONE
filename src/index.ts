import { Hono, type Context } from 'hono'
import { computeProgress, cleanText, isDate, isStatus, slugify, randomToken, sha256Hex, timingSafeEqual, summaryText, type Member, type Milestone, type Task } from './progress.ts'
import { progressCard } from './png.ts'
import { pageShell, homeBody, projectBody } from './views.ts'

type Bindings = { DB: D1Database }
type Env = { Bindings: Bindings }
type ProjectRow = { id: number; slug: string; title: string; team: string; edit_key_hash: string; version: number; created_at: string; updated_at: string }

const app = new Hono<Env>()

const LIMITS = { members: 12, milestones: 20, tasks: 400 }

app.onError((err, c) => {
  console.error(err)
  return c.json({ error: 'server_error' }, 500)
})

async function loadProject(c: Context<Env>, slug: string): Promise<ProjectRow | null> {
  return c.env.DB.prepare('SELECT * FROM projects WHERE slug = ?').bind(slug).first<ProjectRow>()
}

async function requireEditor(c: Context<Env>, slug: string): Promise<ProjectRow | Response> {
  const p = await loadProject(c, slug)
  if (!p) return c.json({ error: 'not_found' }, 404)
  const key = c.req.header('x-edit-key') || ''
  if (!key || !timingSafeEqual(await sha256Hex(key), p.edit_key_hash)) return c.json({ error: 'edit_key_required' }, 401)
  return p
}

async function bump(c: Context<Env>, projectId: number, text: string) {
  await c.env.DB.batch([
    c.env.DB.prepare("UPDATE projects SET version = version + 1, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?").bind(projectId),
    c.env.DB.prepare('INSERT INTO activity (project_id, text) VALUES (?, ?)').bind(projectId, text.slice(0, 200))
  ])
}

async function fullState(c: Context<Env>, p: ProjectRow) {
  const [members, milestones, tasks, activity] = await c.env.DB.batch([
    c.env.DB.prepare('SELECT id, name, role FROM members WHERE project_id = ? ORDER BY id').bind(p.id),
    c.env.DB.prepare('SELECT id, title, weight, position, due_date FROM milestones WHERE project_id = ? ORDER BY position, id').bind(p.id),
    c.env.DB.prepare('SELECT t.id, t.milestone_id, t.title, t.member_id, t.status, t.updated_at FROM tasks t JOIN milestones m ON m.id = t.milestone_id WHERE m.project_id = ? ORDER BY t.id').bind(p.id),
    c.env.DB.prepare('SELECT id, text, created_at FROM activity WHERE project_id = ? ORDER BY id DESC LIMIT 15').bind(p.id)
  ])
  const mem = members.results as unknown as Member[]
  const ms = milestones.results as unknown as Milestone[]
  const ts = tasks.results as unknown as Task[]
  return {
    project: { slug: p.slug, title: p.title, team: p.team, version: p.version, created_at: p.created_at, updated_at: p.updated_at },
    members: mem,
    milestones: ms,
    tasks: ts,
    activity: activity.results,
    progress: computeProgress(ms, ts, mem)
  }
}

async function body(c: Context<Env>): Promise<Record<string, unknown>> {
  try {
    const b = await c.req.json()
    return b && typeof b === 'object' ? (b as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

const weightOf = (v: unknown, fallback: number) => (Number.isInteger(v) && (v as number) >= 1 && (v as number) <= 100 ? (v as number) : fallback)

app.use('/api/*', async (c, next) => {
  await next()
  c.header('Cache-Control', 'no-store')
})

app.post('/api/projects', async (c) => {
  const b = await body(c)
  const title = cleanText(b.title, 80)
  if (!title) return c.json({ error: 'title_required' }, 400)
  const team = cleanText(b.team, 80)
  const members = (Array.isArray(b.members) ? b.members : []).map((m) => cleanText(m, 40)).filter(Boolean).slice(0, LIMITS.members)
  const milestones = (Array.isArray(b.milestones) ? b.milestones : []).map((m) => cleanText(m, 60)).filter(Boolean).slice(0, LIMITS.milestones)
  const editKey = randomToken(18)
  const hash = await sha256Hex(editKey)
  let slug = ''
  let projectId = 0
  for (let i = 0; i < 4 && !projectId; i++) {
    slug = slugify(title, randomToken(4).slice(0, 6))
    const r = await c.env.DB.prepare('INSERT OR IGNORE INTO projects (slug, title, team, edit_key_hash) VALUES (?, ?, ?, ?)').bind(slug, title, team, hash).run()
    if (r.meta.changes === 1) projectId = Number(r.meta.last_row_id)
  }
  if (!projectId) return c.json({ error: 'slug_collision' }, 500)
  const stmts: D1PreparedStatement[] = []
  members.forEach((name) => stmts.push(c.env.DB.prepare('INSERT INTO members (project_id, name) VALUES (?, ?)').bind(projectId, name)))
  milestones.forEach((t, i) => stmts.push(c.env.DB.prepare('INSERT INTO milestones (project_id, title, position) VALUES (?, ?, ?)').bind(projectId, t, i)))
  stmts.push(c.env.DB.prepare('INSERT INTO activity (project_id, text) VALUES (?, ?)').bind(projectId, `Bottle launched: ${title}`))
  await c.env.DB.batch(stmts)
  return c.json({ slug, editKey, viewUrl: `/p/${slug}`, editUrl: `/p/${slug}#key=${editKey}` }, 201)
})

app.get('/api/projects/:slug', async (c) => {
  const p = await loadProject(c, c.req.param('slug'))
  if (!p) return c.json({ error: 'not_found' }, 404)
  return c.json(await fullState(c, p))
})

app.get('/api/projects/:slug/version', async (c) => {
  const r = await c.env.DB.prepare('SELECT version FROM projects WHERE slug = ?').bind(c.req.param('slug')).first<{ version: number }>()
  if (!r) return c.json({ error: 'not_found' }, 404)
  return c.json({ version: r.version })
})

app.post('/api/projects/:slug/verify', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  return c.json({ ok: true })
})

app.get('/api/projects/:slug/summary', async (c) => {
  const p = await loadProject(c, c.req.param('slug'))
  if (!p) return c.json({ error: 'not_found' }, 404)
  const s = await fullState(c, p)
  const url = new URL(`/p/${p.slug}`, c.req.url).toString()
  return c.text(summaryText(p.title, p.team, s.progress, url, new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC'))
})

app.post('/api/projects/:slug/members', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const b = await body(c)
  const name = cleanText(b.name, 40)
  if (!name) return c.json({ error: 'name_required' }, 400)
  const n = await c.env.DB.prepare('SELECT COUNT(*) AS n FROM members WHERE project_id = ?').bind(p.id).first<{ n: number }>()
  if ((n?.n ?? 0) >= LIMITS.members) return c.json({ error: 'member_limit' }, 409)
  const r = await c.env.DB.prepare('INSERT INTO members (project_id, name, role) VALUES (?, ?, ?)').bind(p.id, name, cleanText(b.role, 40)).run()
  await bump(c, p.id, `${name} joined the crew`)
  return c.json({ id: Number(r.meta.last_row_id) }, 201)
})

app.delete('/api/projects/:slug/members/:id', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const id = Number(c.req.param('id'))
  const m = await c.env.DB.prepare('SELECT name FROM members WHERE id = ? AND project_id = ?').bind(id, p.id).first<{ name: string }>()
  if (!m) return c.json({ error: 'not_found' }, 404)
  await c.env.DB.batch([
    c.env.DB.prepare('UPDATE tasks SET member_id = NULL WHERE member_id = ?').bind(id),
    c.env.DB.prepare('DELETE FROM members WHERE id = ?').bind(id)
  ])
  await bump(c, p.id, `${m.name} left the crew`)
  return c.json({ ok: true })
})

app.post('/api/projects/:slug/milestones', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const b = await body(c)
  const title = cleanText(b.title, 60)
  if (!title) return c.json({ error: 'title_required' }, 400)
  const due = isDate(b.due_date) ? b.due_date : null
  const n = await c.env.DB.prepare('SELECT COUNT(*) AS n, COALESCE(MAX(position), -1) AS mx FROM milestones WHERE project_id = ?').bind(p.id).first<{ n: number; mx: number }>()
  if ((n?.n ?? 0) >= LIMITS.milestones) return c.json({ error: 'milestone_limit' }, 409)
  const r = await c.env.DB.prepare('INSERT INTO milestones (project_id, title, weight, position, due_date) VALUES (?, ?, ?, ?, ?)').bind(p.id, title, weightOf(b.weight, 1), (n?.mx ?? -1) + 1, due).run()
  await bump(c, p.id, `New sail rigged: ${title}`)
  return c.json({ id: Number(r.meta.last_row_id) }, 201)
})

app.patch('/api/projects/:slug/milestones/:id', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const id = Number(c.req.param('id'))
  const m = await c.env.DB.prepare('SELECT * FROM milestones WHERE id = ? AND project_id = ?').bind(id, p.id).first<Milestone>()
  if (!m) return c.json({ error: 'not_found' }, 404)
  const b = await body(c)
  const title = cleanText(b.title, 60) || m.title
  const due = b.due_date === null || b.due_date === '' ? null : isDate(b.due_date) ? b.due_date : m.due_date
  await c.env.DB.prepare('UPDATE milestones SET title = ?, weight = ?, due_date = ? WHERE id = ?').bind(title, weightOf(b.weight, m.weight), due, id).run()
  await bump(c, p.id, `Sail adjusted: ${title}`)
  return c.json({ ok: true })
})

app.delete('/api/projects/:slug/milestones/:id', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const id = Number(c.req.param('id'))
  const m = await c.env.DB.prepare('SELECT title FROM milestones WHERE id = ? AND project_id = ?').bind(id, p.id).first<{ title: string }>()
  if (!m) return c.json({ error: 'not_found' }, 404)
  await c.env.DB.batch([
    c.env.DB.prepare('DELETE FROM tasks WHERE milestone_id = ?').bind(id),
    c.env.DB.prepare('DELETE FROM milestones WHERE id = ?').bind(id)
  ])
  await bump(c, p.id, `Sail struck: ${m.title}`)
  return c.json({ ok: true })
})

async function memberInProject(c: Context<Env>, projectId: number, v: unknown) {
  return c.env.DB.prepare('SELECT id FROM members WHERE id = ? AND project_id = ?').bind(Number(v), projectId).first<{ id: number }>()
}

app.post('/api/projects/:slug/tasks', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const b = await body(c)
  const title = cleanText(b.title, 100)
  if (!title) return c.json({ error: 'title_required' }, 400)
  const ms = await c.env.DB.prepare('SELECT id FROM milestones WHERE id = ? AND project_id = ?').bind(Number(b.milestone_id), p.id).first<{ id: number }>()
  if (!ms) return c.json({ error: 'milestone_not_found' }, 400)
  let memberId: number | null = null
  if (b.member_id !== null && b.member_id !== undefined && b.member_id !== '') {
    const mem = await memberInProject(c, p.id, b.member_id)
    if (!mem) return c.json({ error: 'member_not_found' }, 400)
    memberId = mem.id
  }
  const n = await c.env.DB.prepare('SELECT COUNT(*) AS n FROM tasks t JOIN milestones m ON m.id = t.milestone_id WHERE m.project_id = ?').bind(p.id).first<{ n: number }>()
  if ((n?.n ?? 0) >= LIMITS.tasks) return c.json({ error: 'task_limit' }, 409)
  const r = await c.env.DB.prepare('INSERT INTO tasks (milestone_id, title, member_id) VALUES (?, ?, ?)').bind(ms.id, title, memberId).run()
  await bump(c, p.id, `Task added: ${title}`)
  return c.json({ id: Number(r.meta.last_row_id) }, 201)
})

async function taskInProject(c: Context<Env>, projectId: number, id: number) {
  return c.env.DB.prepare('SELECT t.* FROM tasks t JOIN milestones m ON m.id = t.milestone_id WHERE t.id = ? AND m.project_id = ?').bind(id, projectId).first<Task>()
}

app.patch('/api/projects/:slug/tasks/:id', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const t = await taskInProject(c, p.id, Number(c.req.param('id')))
  if (!t) return c.json({ error: 'not_found' }, 404)
  const b = await body(c)
  const status = isStatus(b.status) ? b.status : t.status
  const title = cleanText(b.title, 100) || t.title
  let memberId = t.member_id
  if (b.member_id === null || b.member_id === '') memberId = null
  else if (b.member_id !== undefined) {
    const mem = await memberInProject(c, p.id, b.member_id)
    if (!mem) return c.json({ error: 'member_not_found' }, 400)
    memberId = mem.id
  }
  await c.env.DB.prepare("UPDATE tasks SET status = ?, title = ?, member_id = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?").bind(status, title, memberId, t.id).run()
  const verb = status !== t.status ? (status === 'done' ? 'Done' : status === 'doing' ? 'In progress' : 'Reopened') : 'Edited'
  await bump(c, p.id, `${verb}: ${title}`)
  return c.json({ ok: true })
})

app.delete('/api/projects/:slug/tasks/:id', async (c) => {
  const p = await requireEditor(c, c.req.param('slug'))
  if (p instanceof Response) return p
  const t = await taskInProject(c, p.id, Number(c.req.param('id')))
  if (!t) return c.json({ error: 'not_found' }, 404)
  await c.env.DB.prepare('DELETE FROM tasks WHERE id = ?').bind(t.id).run()
  await bump(c, p.id, `Task removed: ${t.title}`)
  return c.json({ ok: true })
})

app.get('/og/:file', async (c) => {
  const p = await loadProject(c, c.req.param('file').replace(/\.png$/, ''))
  if (!p) return c.notFound()
  const s = await fullState(c, p)
  const png = await progressCard(s.progress.percent, s.progress.milestones, s.progress.tasksDone, s.progress.tasksTotal)
  return new Response(png, { headers: { 'Content-Type': 'image/png', 'Cache-Control': 'public, max-age=60' } })
})

app.get('/', (c) => c.html(pageShell({ title: 'Bote sa Bote · Capstone progress in a bottle', description: 'Track your capstone team progress as a ship in a bottle. Share one link in your Messenger group chat.', body: homeBody(), script: 'home' })))

app.get('/p/:slug', async (c) => {
  const p = await loadProject(c, c.req.param('slug'))
  if (!p) return c.html(pageShell({ title: 'Bottle not found', description: 'This bottle does not exist.', body: '<main class="page"><h1>Bottle not found</h1><p><a href="/">Launch a new one</a></p></main>', script: '' }), 404)
  const s = await fullState(c, p)
  const origin = new URL(c.req.url).origin
  return c.html(pageShell({
    title: `${p.title}: ${s.progress.percent}% · Bote sa Bote`,
    description: `${s.progress.tasksDone}/${s.progress.tasksTotal} tasks done across ${s.progress.milestones.length} milestones${p.team ? ' · ' + p.team : ''}.`,
    image: `${origin}/og/${p.slug}.png?v=${p.version}`,
    url: `${origin}/p/${p.slug}`,
    body: projectBody(p.slug),
    script: 'project'
  }))
})

export default app
