import subprocess, sys
from pathlib import Path

def test_invalid_output_byte_is_captured_without_decode(tmp_path):
    out=tmp_path/'stdout.log'; err=tmp_path/'stderr.log'
    code="import sys;sys.stdout.buffer.write(b'\\x81');sys.stderr.buffer.write(b'\\xff');sys.stdout.flush()"
    with out.open('wb') as fo, err.open('wb') as fe:
        p=subprocess.Popen([sys.executable,'-c',code],stdout=fo,stderr=fe)
        assert p.wait(timeout=5)==0
    assert out.read_bytes()==bytes([0x81]) and err.read_bytes()==bytes([0xff])
