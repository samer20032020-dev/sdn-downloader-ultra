const fs = require('fs');
const vm = require('vm');

function validateHtmlScripts(filePath, label) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }
  const html = fs.readFileSync(filePath, 'utf8');
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
    .map(match => match[1])
    .filter(Boolean);

  if (!scripts.length) {
    throw new Error(`No inline script found in ${label} (${filePath})`);
  }

  scripts.forEach((source, index) => {
    new vm.Script(source, { filename: `${label}-inline-${index}.js` });
  });

  console.log(`✅ ${label} JavaScript parsed successfully (${scripts.length} block)`);
}

validateHtmlScripts('ui/index.html', 'PC UI');
validateHtmlScripts('www/index.html', 'Mobile UI');
