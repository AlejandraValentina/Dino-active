"""Send a recorded audit interaction from stdin to the isolated GUI process."""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

request = urllib.request.Request('http://127.0.0.1:18773/',
    json.dumps({'code': sys.stdin.buffer.read().decode('utf-8')}).encode('utf-8'),
    {'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=55) as response:
    print(response.read().decode('utf-8'))
