import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_fake_agent_two_invocations_until_terminal():
    state={'done':0}; calls=[]
    def fake():
        calls.append(1); state['done']+=1; return state['done']>=2
    terminal=False
    while not terminal and len(calls)<3: terminal=fake()
    assert terminal and len(calls)==2
