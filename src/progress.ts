export type Status = 'todo' | 'doing' | 'done'

export interface Member { id: number; name: string; role: string }
export interface Task { id: number; milestone_id: number; title: string; member_id: number | null; status: Status; updated_at: string }
export interface Milestone { id: number; title: string; weight: number; position: number; due_date: string | null }

export interface MilestoneProgress { id: number; title: string; weight: number; due_date: string | null; done: number; total: number; ratio: number }
export interface MemberProgress { id: number; name: string; role: string; done: number; doing: number; total: number }
export interface Progress { percent: number; exact: string; milestones: MilestoneProgress[]; members: MemberProgress[]; sails: number; tasksDone: number; tasksTotal: number }

export function computeProgress(milestones: Milestone[], tasks: Task[], members: Member[]): Progress {
  const ordered = [...milestones].sort((a, b) => a.position - b.position || a.id - b.id)
  let num = 0
  let den = 0
  const ms: MilestoneProgress[] = ordered.map((m) => {
    const own = tasks.filter((t) => t.milestone_id === m.id)
    const done = own.filter((t) => t.status === 'done').length
    const ratio = own.length === 0 ? 0 : done / own.length
    num += m.weight * done
    den += m.weight * own.length
    return { id: m.id, title: m.title, weight: m.weight, due_date: m.due_date, done, total: own.length, ratio }
  })
  const percent = den === 0 ? 0 : Math.floor((num / den) * 1000) / 10
  const mem: MemberProgress[] = members.map((p) => {
    const own = tasks.filter((t) => t.member_id === p.id)
    return {
      id: p.id,
      name: p.name,
      role: p.role,
      done: own.filter((t) => t.status === 'done').length,
      doing: own.filter((t) => t.status === 'doing').length,
      total: own.length
    }
  })
  return {
    percent,
    exact: `${num}/${den}`,
    milestones: ms,
    members: mem,
    sails: ms.filter((m) => m.total > 0 && m.done === m.total).length,
    tasksDone: tasks.filter((t) => t.status === 'done').length,
    tasksTotal: tasks.length
  }
}

export function cleanText(v: unknown, max: number): string {
  if (typeof v !== 'string') return ''
  return v.replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max)
}

export function isDate(v: unknown): v is string {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false
  const d = new Date(v + 'T00:00:00Z')
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === v
}

export function isStatus(v: unknown): v is Status {
  return v === 'todo' || v === 'doing' || v === 'done'
}

export function slugify(title: string, suffix: string): string {
  const base = title.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 32)
  return `${base || 'capstone'}-${suffix}`
}

export function randomToken(bytes: number): string {
  const a = new Uint8Array(bytes)
  crypto.getRandomValues(a)
  return Array.from(a, (b) => b.toString(36).padStart(2, '0')).join('').slice(0, Math.ceil(bytes * 1.6))
}

export async function sha256Hex(s: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('')
}

export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let r = 0
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return r === 0
}

export function summaryText(title: string, team: string, p: Progress, url: string, asOf: string): string {
  const bar = (r: number) => {
    const n = Math.round(r * 10)
    return '▰'.repeat(n) + '▱'.repeat(10 - n)
  }
  const lines = [
    `⛵ ${title}${team ? ' · ' + team : ''}`,
    `${bar(p.percent / 100)} ${p.percent}% (${p.tasksDone}/${p.tasksTotal} tasks, weighted ${p.exact})`,
    ''
  ]
  for (const m of p.milestones) lines.push(`${m.total > 0 && m.done === m.total ? '✓' : '·'} ${m.title}: ${m.done}/${m.total}${m.due_date ? ' · due ' + m.due_date : ''}`)
  lines.push('')
  for (const m of p.members) lines.push(`👤 ${m.name}: ${m.done} done, ${m.doing} doing, ${m.total} assigned`)
  lines.push('', `As of ${asOf}`, url)
  return lines.join('\n')
}
