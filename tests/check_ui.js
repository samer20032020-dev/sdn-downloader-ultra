const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('ui/index.html', 'utf8');
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map(match => match[1])
  .filter(Boolean);

if (!scripts.length) {
  throw new Error('No inline UI script was found');
}

scripts.forEach((source, index) => {
  new vm.Script(source, { filename: `ui-inline-${index}.js` });
});

console.log(`UI JavaScript parsed successfully (${scripts.length} block)`);
