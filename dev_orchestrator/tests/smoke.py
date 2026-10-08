"""Comando inocuo real: archivo en run exclusivo, prueba unittest y métrica/hash."""
import argparse
import hashlib
import json
from pathlib import Path
import unittest

PAYLOAD=b'MotorSim development infrastructure smoke test\n'


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run-dir',type=Path,required=True)
    run=parser.parse_args().run_dir
    payload=run/'artifacts/payload.txt'
    with payload.open('xb') as stream: stream.write(PAYLOAD)
    class Smoke(unittest.TestCase):
        def runTest(self): self.assertEqual(payload.read_bytes(),PAYLOAD)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([Smoke()]))
    actual=hashlib.sha256(payload.read_bytes()).hexdigest()
    expected=hashlib.sha256(PAYLOAD).hexdigest()
    data=dict(checks=[dict(id='artifact_hash',passed=actual==expected,kind='test',reason=actual)],
              metrics=dict(payload_bytes=payload.stat().st_size,tests_run=result.testsRun),scientific_change_required=False)
    (run/'artifacts/dummy.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(sha256=actual,tests_run=result.testsRun)))
    return 0 if result.wasSuccessful() and actual==expected else 1


if __name__=='__main__': raise SystemExit(main())
