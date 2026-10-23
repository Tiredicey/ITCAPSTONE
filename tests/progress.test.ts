import { test } from 'node:test'
import assert from 'node:assert/strict'
import { computeProgress, cleanText, isDate, slugify, summaryText, sha256Hex, timingSafeEqual } from '../src/progress.ts'
import { progressCard } from '../src/png.ts'

const ms = [
  { id: 1, title: 'Ch1', weight: 1, position: 0, due_date: null },
  { id: 2, title: 'Prototype', weight: 3, position: 1, due_date: '2027-01-15' }
]
const mem = [{ id: 7, name: 'Ana', role: '' }, { id: 8, name: 'Ben', role: 'Dev' }]
const t = (id: number, m: number, s: 'todo' | 'doing' | 'done', who: number | null = null) => ({ id, milestone_id: m, title: 't' + id, member_id: who, status: s, updated_at: '' })

test('empty project is 0%', () => {
  const p = computeProgress([], [], [])
  assert.equal(p.percent, 0)
  assert.equal(p.exact, '0/0')
})

test('weighted percent is exact and floored to 0.1', () => {
  const p = computeProgress(ms, [t(1, 1, 'done', 7), t(2, 1, 'todo'), t(3, 2, 'done', 8), t(4, 2, 'doing', 8), t(5, 2, 'todo')], mem)
  assert.equal(p.exact, '4/11')
  assert.equal(p.percent, 36.3)
  assert.equal(p.tasksDone, 2)
  assert.deepEqual(p.members.map((m) => [m.done, m.doing, m.total]), [[1, 0, 1], [1, 1, 2]])
})

test('100% only when every task is done; sails count full milestones', () => {
  const p = computeProgress(ms, [t(1, 1, 'done'), t(2, 2, 'done')], mem)
  assert.equal(p.percent, 100)
  assert.equal(p.sails, 2)
})

test('milestone with no tasks is not a full sail', () => {
  const p = computeProgress(ms, [t(1, 1, 'done')], mem)
  assert.equal(p.sails, 1)
})

test('input cleaning', () => {
  assert.equal(cleanText('  a\n\tb  ', 10), 'a b')
  assert.equal(cleanText(5, 10), '')
  assert.ok(isDate('2027-02-28'))
  assert.ok(!isDate('2027-02-30'))
  assert.equal(slugify('Smart Queue! STI Lipa', 'ab12'), 'smart-queue-sti-lipa-ab12')
})

test('summary text lists every milestone and member', () => {
  const p = computeProgress(ms, [t(1, 1, 'done', 7)], mem)
  const s = summaryText('Thesis', 'BSIT 3A', p, 'https://x/p/a', '2026-10-23 10:00 UTC')
  assert.match(s, /Ch1: 1\/1/)
  assert.match(s, /Prototype: 0\/0 · due 2027-01-15/)
  assert.match(s, /Ana: 1 done/)
})

test('hash and compare', async () => {
  const h = await sha256Hex('abc')
  assert.equal(h, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  assert.ok(timingSafeEqual(h, h))
  assert.ok(!timingSafeEqual(h, h.slice(1) + '0'))
})

test('OG card is a valid PNG', async () => {
  const png = await progressCard(42.5, [{ ratio: 1 }, { ratio: 0.3 }], 3, 7)
  assert.deepEqual([...png.slice(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10])
})
