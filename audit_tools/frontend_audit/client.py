"""Send a recorded audit interaction from stdin to the isolated GUI process."""
import json
import sys
import urllib.request

request = urllib.request.Request('http://127.0.0.1:18763/',
    json.dumps({'code': sys.stdin.read()}).encode('utf-8'),
    {'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=55) as response:
    print(response.read().decode('utf-8'))
