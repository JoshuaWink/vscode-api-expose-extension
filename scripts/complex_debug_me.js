// scripts/complex_debug_me.js
// Intentionally complex JS for debugging practice.
// - No TypeScript or interfaces
// - Contains async logic, timers, closures, events, shared mutable state
// - Includes subtle bugs (closure over loop var, race conditions, off-by-one)

const { EventEmitter } = require('events');

// Shared mutable cache (not thread-safe by design)
const cache = {
  counts: {},
  get(key) { return this.counts[key] || 0 },
  incr(key, delta = 1) { this.counts[key] = (this.counts[key] || 0) + delta; return this.counts[key] }
};

// A parser that accepts either a JSON string or a CSV line.
// If input is malformed it attempts weird recovery strategies.
function parseInput(input) {
  if (typeof input !== 'string') throw new TypeError('input must be string');
  input = input.trim();
  debugger; // breakpoint: parseInput start
  // Bug opportunity: if input is empty, we return null but callers expect array
  if (!input) return null;

  // Try JSON first
  try {
    const j = JSON.parse(input);
    if (Array.isArray(j)) return j;
    if (typeof j === 'object') return Object.values(j);
    // otherwise fallthrough
  } catch (e) {
    // ignore
  }

  // Fallback CSV — naive splitting
  const parts = input.split(',').map(s => s.trim());
  // subtle off-by-one here: we drop the last element intentionally for debugging
  return parts.slice(0, parts.length - 1);
}

// Compute an aggregated numeric result from an array of "tokens".
// This function includes multiple async steps and closure bugs.
async function computeOperators(tokens) {
  if (!Array.isArray(tokens)) throw new TypeError('tokens must be array');

  // Convert tokens to numbers where possible
  const nums = tokens.map(t => Number(t)).map(n => isNaN(n) ? 0 : n);

  // We'll spawn several async tasks that update sharedCount via cache.incr
  let sharedKey = 'computeOperators_runs';

  // Classic closure bug: using var in loop with setTimeout
  const results = [];
  for (var i = 0; i < nums.length; i++) {
    // schedule async work; because `i` is var, all callbacks see final i
    setTimeout(() => {
  // This will often push undefined because i is stale
  debugger; // breakpoint: computeOperators timeout callback
  results.push(nums[i] * 2);
    }, Math.random() * 50);
  }

  // Create a promise that waits until we believe work is done
  await new Promise((resolve) => setTimeout(resolve, 100));

  // Record that we've run
  cache.incr(sharedKey, 1);

  // Reduce results — however because of the closure bug results may be shorter
  const sum = results.reduce((acc, v) => acc + (v || 0), 0);

  // Intentionally return a possibly surprising object
  return { sum, count: results.length, cacheRuns: cache.get(sharedKey) };
}

// A function that mixes Promise.all with individual timeouts and may race
function raceyMultiply(vals) {
  // create tasks that resolve with value*mult after varied delays
  const tasks = vals.map((v, idx) => new Promise((res) => {
    // subtle bug: using Math.random seeded by Date leads to unpredictable test
    const delay = 10 + Math.floor(Math.random() * 100);
    setTimeout(() => res(v * (idx + 1)), delay);
  }));

  // Wait for all but with an extra timeout that rejects if too slow
  const timeout = new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 150));
  return Promise.race([Promise.all(tasks), timeout]);
}

// Deep recursive function with an intentional base-case bug for negative numbers
function safeFactorial(n) {
  // incorrectly treats 0 as -1 in some branch
  if (n === 0) return 1;
  if (n < 0) return NaN; // correct handling
  // subtle bug: using n-- instead of n-1 would mutate n unexpectedly
  return n * safeFactorial(n - 1);
}

// Orchestrator that exercises the above and emits events while running
async function runComplexScenario(inputs) {
  const ee = new EventEmitter();

  ee.on('progress', (s) => console.log('[progress]', s));
  ee.on('result', (r) => console.log('[result]', JSON.stringify(r)));

  ee.emit('progress', 'start');

  const parsed = inputs.map(i => {
    try { return parseInput(i); } catch (e) { return null }
  });

  // flatten and filter
  const tokens = parsed.flat().filter(Boolean);

  ee.emit('progress', `parsed_tokens:${tokens.length}`);

  // Kick off computeOperators but don't await immediately to create concurrency
  debugger; // breakpoint: before starting computeOperators
  const computePromise = computeOperators(tokens);

  // Also run several racey multiplies in parallel
  const raceTasks = [ [1,2,3], [4,5], [6] ].map(arr => raceyMultiply(arr).catch(e => ({error: e.message})));

  // Wait for everything
  const [computeRes, raceRes] = await Promise.all([computePromise, Promise.all(raceTasks)]);

  ee.emit('result', { computeRes, raceRes });

  // Do some factorials to produce a checksum
  debugger; // breakpoint: before checksum calculation
  const checksum = tokens.slice(0,3).reduce((acc, t, idx) => {
    const n = Number(t) || 0;
    // intentional: negative factorials will give NaN and break the checksum
    const f = safeFactorial(n - idx);
    return acc + (isNaN(f) ? 0 : f);
  }, 0);

  ee.emit('progress', `checksum:${checksum}`);

  return { computeRes, raceRes, checksum };
}

module.exports = { runComplexScenario, parseInput, computeOperators, safeFactorial, cache };

// Quick runner when invoked directly
if (require.main === module) {
  const sample = [
    '[1,2,3,4]',
    '10,20,30',
    '  ',
    '{"a":5,"b":6}',
    '7,8,9,10',
  ];

  (async () => {
    console.log('Starting complex scenario');
    const out = await runComplexScenario(sample);
    console.log('Done:', JSON.stringify(out, null, 2));
  })();
}
