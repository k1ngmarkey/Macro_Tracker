/*
  Home page and View Day page.

  Layout:
    1. settings   - goals, backend url, where the other pages live
    2. api        - the ONLY part that talks to the backend
    3. helpers    - small functions for totals, progress bars, dates
    4. pages      - home() and dayPage(), each returns an html string
    5. router     - swaps the page based on the # in the url
*/


/* ---------- 1. settings ---------- */

// Daily targets used for the progress bars. Hardcoded for now.
// When the backend stores goals per user, fetch them in the api section
// and use them in place of this object (it's read in macroBars() and home()).
const GOALS = {cal: 2200, p: 160, c: 240, f: 70};

// Meal sections on the day page, in the order they show up.
// Must match the "type" value on each meal coming from the backend.
const TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snacks'];

// Where the backend lives. Change this one line when the server is up.
const API_URL = 'http://localhost:3000/api';

// Links to the other two pages. Right now they point at placeholder routes
// inside this file. See "connecting the other pages" in the router section.
// (The same two links are also in the nav in index.html.)
const LINKS = {add: '#add', recipe: '#recipe'};


/* ---------- 2. api (backend connection) ---------- */

// If the backend names the fields differently (calories, protein, mealType...)
// fix it here and nowhere else. This turns whatever the backend sends
// into the shape the pages above expect.
function normalizeDay(raw) {
  return {
    date: raw.date,
    meals: (raw.meals || []).map(m => ({
      type: m.type,
      name: m.name,
      cal: m.cal,
      p: m.p,
      c: m.c,
      f: m.f
    }))
  };
}

const api = {
  // Every day that has been logged, newest first. Used by the recent days list on Home.
  async listDays() {
    const res = await fetch(`${API_URL}/days`);
    if (!res.ok) throw new Error('could not load days (' + res.status + ')');
    const rows = await res.json();
    return rows.map(normalizeDay);
  },

  // One day by its date key ("YYYY-MM-DD"). A day with nothing logged
  // can come back as a 404 from the backend, so treat that as an empty day
  // instead of an error.
  async getDay(dateKey) {
    const res = await fetch(`${API_URL}/days/${dateKey}`);
    if (res.status === 404) return {date: dateKey, meals: []};
    if (!res.ok) throw new Error('could not load day (' + res.status + ')');
    return normalizeDay(await res.json());
  }
};


/* ---------- 3. helpers ---------- */

// Turns a Date into "YYYY-MM-DD" using local time. This is the format the
// backend gets and the format to remember which day is selected.
function keyOf(d) {
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

// Turns "YYYY-MM-DD" back into a Date at midnight local time.
function fromKey(key) {
  return new Date(key + 'T00:00');
}

// Date to show in the header, like "Tue, Nov 24".
function fmt(key) {
  return fromKey(key).toLocaleDateString('en-CA', {weekday: 'short', month: 'short', day: 'numeric'});
}

// Escapes text before it goes into an html string, so a meal named "<b>" can't break the page.
// Use it on anything that comes from the backend or from the user.
function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
}

// Adds up calories and macros for a list of meals.
function sum(meals) {
  return meals.reduce(
    (t, m) => ({cal: t.cal + m.cal, p: t.p + m.p, c: t.c + m.c, f: t.f + m.f}),
    {cal: 0, p: 0, c: 0, f: 0}
  );
}

// Makes a text progress bar like [#####.....]  50%. Stops at 100% even if you go over.
function bar(value, goal, width = 24) {
  const ratio = Math.min(value / goal, 1);
  const filled = Math.round(ratio * width);
  return '[' + '#'.repeat(filled) + '.'.repeat(width - filled) + '] ' +
    String(Math.round(value / goal * 100)).padStart(3) + '%';
}

// The four bars (calories, protein, carbs, fat) for a set of totals.
// Used on both pages. The spacing inside the template is on purpose, it lines up the bars.
function macroBars(t) {
  return `<div class="bar">CAL  ${bar(t.cal, GOALS.cal)}  ${t.cal}/${GOALS.cal}
PRO  ${bar(t.p, GOALS.p)}  ${t.p}g/${GOALS.p}g
CARB ${bar(t.c, GOALS.c)}  ${t.c}g/${GOALS.c}g
FAT  ${bar(t.f, GOALS.f)}  ${t.f}g/${GOALS.f}g</div>`;
}


/* ---------- 4. pages ---------- */

// Which day the View Day page is showing. Changes when you click a day
// on Home or use the < > buttons. Defaults to today.
const todayKey = keyOf(new Date());
let selected = todayKey;

// Home page: today's bars, quick links, and the last 7 logged days.
async function home() {
  const [today, days] = await Promise.all([api.getDay(todayKey), api.listDays()]);
  const t = sum(today.meals);
  const left = Math.max(GOALS.cal - t.cal, 0);

  const rows = days.slice(0, 7).map(d => {
    const s = sum(d.meals);
    return `<a data-day="${d.date}">
      <span>${esc(fmt(d.date))}${d.date === todayKey ? ' (today)' : ''}</span>
      <span>${s.cal} cal</span>
      <span class="dim">${s.p}p ${s.c}c ${s.f}f</span>
    </a>`;
  }).join('') || '<div class="dim">no days logged yet</div>';

  return `
  <p class="cursor">Welcome back. ${left} cal left today</p>
  <h2>Today</h2>
  <div class="box">${macroBars(t)}</div>
  <div class="pick">
    <a href="${LINKS.add}">[ + Add a meal ]</a>
    <a data-day="${todayKey}">[ View today ]</a>
    <a href="${LINKS.recipe}">[ New recipe ]</a>
  </div>
  <h2>Recent days</h2>
  <div class="box list">${rows}</div>`;
}

// View Day page: totals for the selected day, then a table for each meal type.
async function dayPage() {
  const d = await api.getDay(selected);
  const t = sum(d.meals);

  const sections = TYPES.map(type => {
    const meals = d.meals.filter(m => m.type === type);
    const s = sum(meals);

    const body = meals.length
      ? meals.map(m => `<div class="row">
          <span>${esc(m.name)}</span><span>${m.cal}</span><span>${m.p}</span><span>${m.c}</span><span>${m.f}</span>
        </div>`).join('') +
        `<div class="row sub"><span>subtotal</span><span>${s.cal}</span><span>${s.p}</span><span>${s.c}</span><span>${s.f}</span></div>`
      : '<div class="dim">nothing logged yet</div>';

    return `<h2>${type}</h2>
      <div class="box">
        <div class="row h"><span></span><span>cal</span><span>P</span><span>C</span><span>F</span></div>
        ${body}
        <div style="margin-top:6px"><a href="${LINKS.add}">[ + add food ]</a></div>
      </div>`;
  }).join('');

  return `
  <div class="pick" style="margin-top:6px">
    <button data-step="-1" aria-label="Previous day">&lt;</button>
    <span style="font-size:28px">${esc(fmt(d.date))}${d.date === todayKey ? ' (today)' : ''}</span>
    <button data-step="1" aria-label="Next day">&gt;</button>
    <a href="#home">[ home ]</a>
  </div>
  <h2>Totals</h2>
  <div class="box">${macroBars(t)}</div>
  ${sections}`;
}

// Placeholder shown for the Add a meal and New Recipe routes until
// the real pages are connected. Delete this once both are hooked up.
function stub(name) {
  return `<h2>${name}</h2>
    <div class="box">Placeholder, this page isn't connected yet.</div>
    <a href="#home">[ back home ]</a>`;
}


/* ---------- 5. router ---------- */

/*
  Connecting the other pages. Two ways, depends on how they were built:

  A) They're their own files (add.html, recipe.html):
       - in index.html change the nav hrefs to "add.html" and "recipe.html"
       - change the two values in LINKS at the top of this file the same way
       - delete the 'add' and 'recipe' lines in render() below, and stub() above
       - those files need the same <nav> as index.html so the menu stays the same

  B) They're functions that return html like home() and dayPage() do:
       - copy the functions into the pages section above
       - in render() replace the stub line for that route with a call to the function
       - leave the hrefs as they are (#add and #recipe)
*/

const app = document.getElementById('app');

// Looks at the # in the url, builds the matching page, puts it on screen.
// Runs on load and every time the hash changes.
async function render() {
  const route = (location.hash || '#home').slice(1);

  // underline the nav item for the current page
  document.querySelectorAll('nav a[data-r]').forEach(a => {
    a.classList.toggle('on', a.dataset.r === route);
  });

  try {
    let html;
    if (route === 'day') html = await dayPage();
    else if (route === 'add') html = stub('Add a meal');       // swap for the real page (see above)
    else if (route === 'recipe') html = stub('New Recipe');    // swap for the real page (see above)
    else html = await home();
    app.innerHTML = html;
  } catch (err) {
    //  means the backend isn't running or API_URL is wrong
    app.innerHTML = `<h2>Error</h2><div class="box">Couldn't load data from the backend.<br><span class="dim">${esc(err.message)}</span></div>`;
  }
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', render);

// One click handler for the whole page so we don't have to rebind after every render.
document.addEventListener('click', e => {
  // clicking a day on Home: remember it and go to the day page
  const dayLink = e.target.closest('[data-day]');
  if (dayLink) {
    selected = dayLink.dataset.day;
    if (location.hash === '#day') render();
    else location.hash = '#day';
    return;
  }

  // the < > buttons on the day page: move one day back or forward (no going into the future)
  const step = e.target.closest('[data-step]');
  if (step) {
    const d = fromKey(selected);
    d.setDate(d.getDate() + Number(step.dataset.step));
    if (keyOf(d) <= todayKey) {
      selected = keyOf(d);
      render();
    }
  }
});

render();
