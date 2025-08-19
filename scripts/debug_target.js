// Simple debug target you can run and set breakpoints in.
// Usage:
//  - In VS Code: open this file, set breakpoints, Run & Debug -> "Launch debug_target.js"
//  - From terminal: node --inspect-brk scripts/debug_target.js

console.log('debug_target: start');

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function inner(i) {
  // BREAKPOINT: inner start
  await sleep(10);
  // BREAKPOINT: before return
  return i * i;
}

async function compute(n) {
  let sum = 0;
  for (let i = 0; i < n; i++) {
    // Useful breakpoint: inside loop to inspect `i` and `sum`
    const v = await inner(i);
    sum += v;
    if (i % 5 === 0) console.log(`progress: i=${i}`);
  }
  // BREAKPOINT: compute finished
  return sum;
}

async function main() {
  console.log('main: entering');
  const n = Number(process.env.DEBUG_TARGET_N) || 20;
  const result = await compute(n);
  console.log('main: result =', result);

  // Optional wait so you can attach a debugger or flip breakpoints
  if (process.argv.includes('--wait')) {
    console.log('main: waiting 10s before exit (debug attach window)');
    await sleep(10000);
  }

  console.log('main: exiting');
}

main().catch(err => {
  console.error('Unhandled error in debug_target:', err);
  process.exit(1);
});
