const esc = (s: string) => s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] as string)

export function pageShell(o: { title: string; description: string; body: string; script: string; image?: string; url?: string }): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(o.title)}</title>
<meta name="description" content="${esc(o.description)}">
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(o.title)}">
<meta property="og:description" content="${esc(o.description)}">
${o.image ? `<meta property="og:image" content="${esc(o.image)}">
<meta property="og:image:width" content="600">
<meta property="og:image:height" content="315">
<meta name="twitter:card" content="summary_large_image">` : ''}
${o.url ? `<meta property="og:url" content="${esc(o.url)}">` : ''}
<meta name="theme-color" content="#2b1e12">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English+SC&family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
${o.body}
${o.script ? `<script type="module" src="/static/${o.script}.js"></script>` : ''}
</body>
</html>`
}

export function homeBody(): string {
  return `<main class="page" id="home">
  <header class="masthead">
    <p class="eyebrow">Capstone tracker for thesis teams</p>
    <h1>Bote sa Bote</h1>
    <p class="lede">Your whole capstone as a ship in a bottle. Every milestone is a sail. Every finished task raises the sea. One link, pasted once in your Messenger group chat, stays current for everyone.</p>
  </header>
  <section class="panel" id="launch-panel" aria-labelledby="launch-title">
    <h2 id="launch-title">Launch a bottle</h2>
    <form id="launch-form" novalidate>
      <label>Thesis title<input name="title" required maxlength="80" autocomplete="off" placeholder="e.g. Smart Queue System for STI Lipa Registrar"></label>
      <label>Team or section<input name="team" maxlength="80" autocomplete="off" placeholder="e.g. BSIT 3A · Group 4"></label>
      <label>Members, one per line<textarea name="members" rows="4" maxlength="600"></textarea></label>
      <label>Milestones, one per line<textarea name="milestones" rows="6" maxlength="1200">Chapter 1: Introduction
Chapter 2: Review of Related Literature
Chapter 3: Methodology
System prototype
Testing and evaluation
Final defense</textarea></label>
      <p class="hint">The milestone list is a starting template. Rename or delete any of it later.</p>
      <button type="submit" class="btn primary">Launch bottle</button>
      <p class="form-error" id="launch-error" role="alert" hidden></p>
    </form>
  </section>
  <section class="panel" id="launched" hidden aria-live="polite">
    <h2>Bottle launched</h2>
    <p>Keep the <strong>captain link</strong> private: it can edit. Share the <strong>view link</strong> in your group chat.</p>
    <label>Captain link (edit)<input id="edit-link" readonly></label>
    <button class="btn" data-copy="edit-link">Copy captain link</button>
    <label>View link (share in Messenger)<input id="view-link" readonly></label>
    <button class="btn" data-copy="view-link">Copy view link</button>
    <p><a class="btn primary" id="open-edit" href="#">Open my bottle</a></p>
  </section>
  <section class="panel" id="recent" hidden>
    <h2>Bottles on this device</h2>
    <ul id="recent-list"></ul>
  </section>
</main>`
}

export function projectBody(slug: string): string {
  return `<main class="page" id="project" data-slug="${esc(slug)}">
  <header class="masthead">
    <p class="eyebrow" id="team"></p>
    <h1 id="title">Loading bottle…</h1>
    <p class="sync" id="sync" aria-live="polite">Connecting…</p>
  </header>
  <section class="bottle-wrap" aria-labelledby="pct-label">
    <figure class="bottle-figure">
      <svg id="bottle" viewBox="0 0 640 300" role="img" aria-labelledby="bottle-desc"><desc id="bottle-desc">Ship in a bottle. Sea level shows overall progress.</desc></svg>
    </figure>
    <div class="readout">
      <p class="pct" id="pct-label"><span id="pct">0</span><span class="unit">%</span></p>
      <p class="pct-detail" id="pct-detail"></p>
    </div>
  </section>
  <nav class="share" aria-label="Share">
    <button class="btn primary" id="share-btn">Share to group chat</button>
    <button class="btn" id="copy-summary">Copy progress text</button>
    <button class="btn" id="copy-link">Copy view link</button>
  </nav>
  <p class="hint" id="share-note" aria-live="polite"></p>
  <section class="panel" aria-labelledby="ms-title">
    <h2 id="ms-title">Sails · milestones</h2>
    <ol id="milestones" class="milestones"></ol>
    <form id="add-milestone" class="inline-form editor-only" hidden>
      <label class="grow">New milestone<input name="title" maxlength="60" required></label>
      <label>Weight<input name="weight" type="number" min="1" max="100" value="1" inputmode="numeric"></label>
      <label>Due<input name="due_date" type="date"></label>
      <button class="btn">Add sail</button>
    </form>
  </section>
  <section class="panel" aria-labelledby="crew-title">
    <h2 id="crew-title">Crew</h2>
    <ul id="crew" class="crew"></ul>
    <form id="add-member" class="inline-form editor-only" hidden>
      <label class="grow">Name<input name="name" maxlength="40" required></label>
      <label class="grow">Role<input name="role" maxlength="40" placeholder="e.g. Lead programmer"></label>
      <button class="btn">Add member</button>
    </form>
  </section>
  <section class="panel" aria-labelledby="log-title">
    <h2 id="log-title">Ship's log</h2>
    <ul id="activity" class="activity"></ul>
  </section>
  <section class="panel captain" id="captain-panel">
    <h2>Captain access</h2>
    <p id="captain-status">View only. Paste the captain key to edit.</p>
    <form id="key-form" class="inline-form">
      <label class="grow">Captain key<input name="key" autocomplete="off" spellcheck="false"></label>
      <button class="btn">Unlock</button>
    </form>
    <button class="btn" id="lock-btn" hidden>Lock this device</button>
  </section>
  <footer class="foot"><a href="/">Launch another bottle</a></footer>
</main>`
}
