import re

with open('build_template.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace problematic Unicode characters with ASCII equivalents
content = content.replace('\u2013', '-')  # en-dash
content = content.replace('\u2014', '--')  # em-dash
content = content.replace('\u2018', "'")  # left single quote
content = content.replace('\u2019', "'")  # right single quote
content = content.replace('\u201c', '"')  # left double quote
content = content.replace('\u201d', '"')  # right double quote
content = content.replace('\u2022', '*')  # bullet
content = content.replace('\u2026', '...')  # ellipsis
content = content.replace('\u00a0', ' ')  # non-breaking space
content = content.replace('\u202f', ' ')  # narrow no-break space

with open('build_template.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed problematic characters')
