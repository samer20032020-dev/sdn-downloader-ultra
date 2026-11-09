import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('ui/index.html', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(3099, 3375):
    line = lines[i]
    if 'id=' in line or 'class=' in line or '<h' in line or '<button' in line or '<select' in line or '<input' in line:
        print(f'{i+1}: {line.strip()[:100]}')
