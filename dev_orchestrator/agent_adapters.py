"""Small verified command adapters for the local roadmap supervisor."""
from dataclasses import dataclass
import shutil

@dataclass(frozen=True)
class AgentAdapter:
    name: str
    executable: str
    command: tuple
    def available(self): return shutil.which(self.executable) is not None

def codex_adapter(repo):
    return AgentAdapter('codex','codex',('codex','exec','-C',str(repo),'--dangerously-bypass-approvals-and-sandbox','-'))

def opencode_adapter(repo):
    return AgentAdapter('opencode','opencode',('opencode','run','--dir',str(repo),'--auto','--pure'))
