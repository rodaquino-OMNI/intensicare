with open('/tmp/intensicare/src/intensicare/config.py', 'r') as f:
    content = f.read()

# Fix the merged line
content = content.replace(
    'return f"redis://{self.redis_host}:***@lru_cache\ndef get_settings',
    'return f"redis://{self.redis_host}:***@lru_cache\n\ndef get_settings'
)

with open('/tmp/intensicare/src/intensicare/config.py', 'w') as f:
    f.write(content)

print("Fixed!")
