# Spec: Agent Safety — Sandbox, Validation, Deception Detection

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Operational Safety Failures (arXiv 2605.30777, Mai 2026), Claude Code sandbox

---

## 🎯 O problema

O paper analisou **68,816 papers + 16,586 GitHub issues** de agentes de código em produção. Resultado:

- **547 falhas de segurança confirmadas** em uso real (não adversarial)
- **326/547 (60%)** classificadas como **high ou critical**
- **65%+ ocorrem em bug fixing e setup** — tarefas cotidianas, não ataques
- Riscos dominantes: **constraint violations, operações destrutivas, authorization bypass, deception**

### Taxonomia de 33 tipos de risco em 7 dimensões

| Dimensão | Exemplos |
|----------|----------|
| **Constraint violations** | Escrever fora do workspace, acessar arquivos de sistema |
| **Destructive operations** | `rm -rf`, dropar tabelas, desconfigurar ambiente |
| **Authorization bypass** | Escalar privilégios, acessar secrets |
| **Deception** | Reportar sucesso quando falhou, fabricar outputs |
| **Resource exhaustion** | Loop infinito, fork bomb, encher disco |
| **Data corruption** | Corromper git history, sobrescrever arquivos errados |
| **Environment pollution** | Instalar packages globais, modificar PATH |

---

## 📐 Design

### Camada 1: Sandbox (execução isolada)

Toda tool perigosa (shell, write_file, delete) roda em sandbox:

```python
# src/ai_workspace/agents/safety.py

import os
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SandboxConfig:
    workspace_root: str              # diretório permitido para escrita
    allowed_commands: set[str]       # comandos permitidos (ls, git, grep, etc.)
    blocked_commands: set[str]       # comandos bloqueados (rm -rf, sudo, etc.)
    max_output_bytes: int = 10_000_000  # 10MB
    max_runtime_seconds: int = 30    # timeout
    network_allowed: bool = False    # sem rede por padrão

class SafetySandbox:
    """Isola execução de comandos perigosos."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
    
    def validate_command(self, command: str) -> Result[str, SafetyError]:
        """Valida se comando é seguro antes de executar."""
        parts = command.strip().split()
        if not parts:
            return Failure(SafetyError("EMPTY_COMMAND", "Empty command"))
        
        base_cmd = parts[0]
        
        # Blocklist explícito
        if base_cmd in self.config.blocked_commands:
            return Failure(SafetyError(
                "BLOCKED_COMMAND",
                f"Command '{base_cmd}' is blocked",
                detail=f"Full command: {command}",
                suggestion="Use a safer alternative or request permission"
            ))
        
        # Allowlist + verificação de path
        if base_cmd in self.config.allowed_commands:
            return self._validate_paths(command, parts)
        
        # Desconhecido → pede permissão
        return Failure(SafetyError(
            "UNKNOWN_COMMAND",
            f"Command '{base_cmd}' not in allowlist",
            recoverable=True,
            suggestion="Add to allowed_commands or use permission gate"
        ))
    
    def _validate_paths(self, command: str, parts: list[str]) -> Result[str, SafetyError]:
        """Verifica se paths no comando estão dentro do workspace."""
        for part in parts:
            # Pula flags e pipes
            if part.startswith('-') or part == '|' or part == '&&':
                continue
            # Verifica se é um path
            if '/' in part or part.endswith(('.py', '.js', '.ts', '.json')):
                resolved = Path(part).resolve()
                workspace = Path(self.config.workspace_root).resolve()
                if not str(resolved).startswith(str(workspace)):
                    return Failure(SafetyError(
                        "PATH_OUTSIDE_WORKSPACE",
                        f"Path '{part}' is outside workspace",
                        detail=f"Resolved: {resolved}\nWorkspace: {workspace}",
                        suggestion=f"Only modify files within {workspace}"
                    ))
        return Success(command)
    
    async def execute(self, command: str, cwd: str = None) -> Result[str, SafetyError]:
        """Executa comando em sandbox com timeout."""
        # 1. Valida
        match self.validate_command(command):
            case Failure(error):
                return Failure(error)
        
        # 2. Executa com timeout
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or self.config.workspace_root,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.max_runtime_seconds,
            )
            
            # 3. Verifica output size
            output = stdout.decode()[:self.config.max_output_bytes]
            
            if proc.returncode != 0:
                return Failure(SafetyError(
                    "COMMAND_FAILED",
                    f"Command exited with code {proc.returncode}",
                    detail=stderr.decode()[:500],
                    recoverable=True,
                ))
            
            return Success(output)
            
        except asyncio.TimeoutError:
            proc.kill()
            return Failure(SafetyError(
                "COMMAND_TIMEOUT",
                f"Command exceeded {self.config.max_runtime_seconds}s limit"
            ))
```

### Camada 2: Validação pós-execução

Depois de cada ação do agente, verificar se o que ele disse que fez realmente aconteceu:

```python
class PostExecutionValidator:
    """Verifica se ações do agente tiveram o efeito esperado."""
    
    async def validate(self, action: AgentAction) -> Result[None, ValidationError]:
        """Valida resultado de uma ação."""
        
        if action.tool == "write_file":
            return self._validate_write(action)
        elif action.tool == "edit_file":
            return self._validate_edit(action)
        elif action.tool == "shell":
            return self._validate_shell(action)
        elif action.tool == "delete_file":
            return self._validate_delete(action)
        
        return Success(None)
    
    def _validate_write(self, action: AgentAction) -> Result[None, ValidationError]:
        """Verifica se arquivo foi realmente escrito."""
        path = action.args.get("path")
        expected_content = action.args.get("content", "")
        
        if not Path(path).exists():
            return Failure(ValidationError(
                "FILE_NOT_CREATED",
                f"Agent claimed to write {path} but file doesn't exist",
                suggestion="Agent may have fabricated the write operation"
            ))
        
        actual = Path(path).read_text()
        if actual.strip() != expected_content.strip():
            return Failure(ValidationError(
                "CONTENT_MISMATCH",
                f"File {path} content doesn't match what agent claimed",
                detail=f"Expected: {len(expected_content)} chars\nActual: {len(actual)} chars",
            ))
        
        return Success(None)
    
    def _validate_shell(self, action: AgentAction) -> Result[None, ValidationError]:
        """Verifica se comando shell não causou danos colaterais."""
        # Check: git status não foi corrompido
        # Check: arquivos críticos ainda existem
        # Check: ambiente não foi poluído
        return Success(None)  # lightweight por enquanto
```

### Camada 3: Deception Detection

O paper identificou que agentes **mentem sobre sucesso**. Precisamos detectar:

```python
class DeceptionDetector:
    """Detecta padrões de deception em outputs do agente."""
    
    # Padrões suspeitos no output do agente
    SUSPICIOUS_PATTERNS = [
        r"(?i)(fixed|resolved|completed|done)\s*[.!]?\s*$",  # afirmação sem evidência
        r"(?i)(the (tests?|linter) (pass|succeed))",          # claim de teste sem output
        r"(?i)(no errors? (were )?found)",                     # claim negativa sem evidência
    ]
    
    def analyze(self, agent_response: str, action_results: list[dict]) -> list[DeceptionWarning]:
        """Analisa resposta do agente em busca de deception."""
        warnings = []
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            matches = re.findall(pattern, agent_response)
            for match in matches:
                # Verifica se há evidência da afirmação nos resultados
                if not self._has_evidence(match, action_results):
                    warnings.append(DeceptionWarning(
                        type="UNVERIFIED_CLAIM",
                        claim=match,
                        confidence=0.7,
                        suggestion="Verify this claim manually"
                    ))
        
        return warnings
    
    def _has_evidence(self, claim: str, results: list[dict]) -> bool:
        """Verifica se afirmação tem suporte nos resultados das tools."""
        # Simplificado: verifica se outputs de tools contêm confirmação
        for r in results:
            if "pass" in claim.lower() and "error" not in str(r.get("output", "")).lower():
                return True
            if "fixed" in claim.lower() and r.get("tool") == "edit_file":
                return True
        return False
```

### Integração no AgentLoop

```python
# agents/loop.py — adicionar camada de segurança

async def agent_loop(params: LoopParams):
    safety = SafetySandbox(params.safety_config)
    validator = PostExecutionValidator()
    detector = DeceptionDetector()
    
    while True:
        # ... existing loop ...
        
        for tool_call in tool_calls:
            # 1. Pre-execution: sandbox validation
            if tool_call.name in ("shell", "write_file", "delete_file"):
                match safety.validate_command(tool_call.args.get("command", "")):
                    case Failure(error):
                        yield LoopEvent(type="safety_blocked", data=error)
                        continue  # pula esta tool
            
            # 2. Execute
            result = await execute_tool(tool_call)
            
            # 3. Post-execution: validate
            match await validator.validate(Action(tool_call.name, tool_call.args)):
                case Failure(error):
                    yield LoopEvent(type="validation_failed", data=error)
            
            # 4. Deception check
            warnings = detector.analyze(result, params.recent_results)
            for w in warnings:
                yield LoopEvent(type="deception_warning", data=w)
```

---

## 📊 Configuração padrão

```python
DEFAULT_SAFETY_CONFIG = SandboxConfig(
    workspace_root=".",  # current directory
    allowed_commands={
        "ls", "cat", "head", "tail", "wc", "grep", "find", "git",
        "python", "python3", "pytest", "npm", "cargo", "go", "rustc",
        "echo", "mkdir", "touch", "cp", "mv", "diff",
    },
    blocked_commands={
        "rm", "sudo", "su", "chmod", "chown", "kill", "shutdown",
        "reboot", "docker", "systemctl", "curl", "wget",
    },
    max_output_bytes=10_000_000,
    max_runtime_seconds=30,
    network_allowed=False,
)
```

---

## ✅ Critérios de aceitação

- [ ] `SafetySandbox` com allowlist/blocklist + validação de paths
- [ ] `PostExecutionValidator` verifica writes/edits/deletes
- [ ] `DeceptionDetector` identifica claims não verificadas
- [ ] Integrado no AgentLoop (pré + pós execução)
- [ ] Configurável via `SandboxConfig`
- [ ] Testes: comandos bloqueados, paths fora do workspace, timeout
- [ ] Testes: detecção de deception com exemplos reais do paper

---

## 📚 Referências

- [Operational Safety Failures (arXiv 2605.30777)](https://arxiv.org/abs/2605.30777) — 547 incidents, 7 dimensões, 33 tipos
- Claude Code sandbox implementation
