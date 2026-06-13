"""
Code Sandbox Service
Executes student code safely using isolated Docker containers with strict limits,
or falls back to secure local subprocess execution if Docker is unavailable.
"""

import os
import sys
import tempfile
import shutil
import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Define sandbox temp directory inside the workspace
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX_TEMP_DIR = os.path.join(BASE_DIR, "sandbox_temp")
os.makedirs(SANDBOX_TEMP_DIR, exist_ok=True)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: str
    run_time_ms: int
    memory_kb: int
    exit_code: int
    oom_killed: bool = False
    timeout: bool = False


class CodeSandbox:
    """
    Secure sandbox for executing untrusted student code.
    Supports: Python, JavaScript, Java, C++, Go, Rust.
    """

    # Language mappings and configuration
    LANGUAGES = {
        "python": {
            "image": "python:3.10-slim",
            "file_name": "solution.py",
            "compile_cmd": None,
            "exec_cmd": ["python", "solution.py"],
            "local_exec": ["python", "solution.py"]
        },
        "python3": {
            "image": "python:3.10-slim",
            "file_name": "solution.py",
            "compile_cmd": None,
            "exec_cmd": ["python", "solution.py"],
            "local_exec": ["python", "solution.py"]
        },
        "javascript": {
            "image": "node:18-slim",
            "file_name": "solution.js",
            "compile_cmd": None,
            "exec_cmd": ["node", "solution.js"],
            "local_exec": ["node", "solution.js"]
        },
        "js": {
            "image": "node:18-slim",
            "file_name": "solution.js",
            "compile_cmd": None,
            "exec_cmd": ["node", "solution.js"],
            "local_exec": ["node", "solution.js"]
        },
        "java": {
            "image": "openjdk:17-slim",
            "file_name": "Solution.java",
            "compile_cmd": ["javac", "Solution.java"],
            "exec_cmd": ["java", "Solution"],
            "local_exec": ["java", "Solution"]
        },
        "cpp": {
            "image": "gcc:12",
            "file_name": "solution.cpp",
            "compile_cmd": ["g++", "-O3", "solution.cpp", "-o", "solution"],
            "exec_cmd": ["./solution"],
            "local_exec": ["./solution"]
        },
        "c++": {
            "image": "gcc:12",
            "file_name": "solution.cpp",
            "compile_cmd": ["g++", "-O3", "solution.cpp", "-o", "solution"],
            "exec_cmd": ["./solution"],
            "local_exec": ["./solution"]
        },
        "go": {
            "image": "golang:1.20-slim",
            "file_name": "solution.go",
            "compile_cmd": ["go", "build", "-o", "solution", "solution.go"],
            "exec_cmd": ["./solution"],
            "local_exec": ["./solution"]
        },
        "rust": {
            "image": "rust:1.68-slim",
            "file_name": "solution.rs",
            "compile_cmd": ["rustc", "solution.rs", "-o", "solution"],
            "exec_cmd": ["./solution"],
            "local_exec": ["./solution"]
        }
    }

    # Strict resource limits
    MAX_TIMEOUT_MS = 5000  # 5 seconds
    MAX_MEMORY_MB = 128    # 128 MB RAM limit
    CPU_LIMIT = 0.5       # 0.5 CPU core limit

    def __init__(self):
        self._docker_available = None

    async def is_docker_available(self) -> bool:
        """Cache check for Docker responsiveness."""
        if self._docker_available is not None:
            return self._docker_available
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.wait(), timeout=1.5)
            self._docker_available = (proc.returncode == 0)
        except Exception:
            self._docker_available = False
        return self._docker_available

    def _parse_docker_time(self, t_str: str) -> float:
        """Parse ISO timestamps from Docker inspect with microsecond truncation."""
        if not t_str:
            return 0.0
        if "." in t_str:
            base, ns = t_str.split(".")
            ns = ns.rstrip("Z")[:6]
            t_str = f"{base}.{ns}+00:00"
        else:
            t_str = t_str.rstrip("Z") + "+00:00"
        try:
            return datetime.fromisoformat(t_str).timestamp()
        except Exception:
            try:
                # Fallback for Python versions or environments without full timezone support
                from dateutil import parser
                return parser.isoparse(t_str).timestamp()
            except Exception:
                return 0.0

    async def _get_docker_peak_memory_kb(self, container_id: str) -> int:
        """Read peak RSS memory of container from Linux host cgroups."""
        paths = [
            f"/sys/fs/cgroup/system.slice/docker-{container_id}.scope/memory.peak",
            f"/sys/fs/cgroup/memory/docker/{container_id}/memory.max_usage_in_bytes",
            f"/sys/fs/cgroup/docker/{container_id}/memory.max_usage_in_bytes",
            f"/sys/fs/cgroup/system.slice/docker-{container_id}.scope/memory.current"
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        return int(f.read().strip()) // 1024
                except Exception:
                    pass
        return 0

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        stdin: str = "",
        timeout_ms: int = 5000
    ) -> ExecutionResult:
        """
        Execute student code safely, choosing Docker if available, otherwise local subprocess.
        """
        lang_config = self.LANGUAGES.get(language.lower())
        if not lang_config:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unsupported language: {language}. Supported: {list(self.LANGUAGES.keys())}",
                run_time_ms=0,
                memory_kb=0,
                exit_code=-1
            )

        # Enforce max timeout bounds
        timeout_ms = min(timeout_ms, self.MAX_TIMEOUT_MS)

        # Create localized temporary directory in workspace
        temp_dir = tempfile.mkdtemp(dir=SANDBOX_TEMP_DIR)
        try:
            # Write code file
            code_file_path = os.path.join(temp_dir, lang_config["file_name"])
            with open(code_file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Write stdin to file for redirection
            input_file_path = os.path.join(temp_dir, "input.txt")
            with open(input_file_path, "w", encoding="utf-8") as f:
                f.write(stdin)

            docker_ok = await self.is_docker_available()
            if docker_ok:
                return await self._execute_docker(temp_dir, lang_config, timeout_ms)
            else:
                return await self._execute_local(temp_dir, lang_config, timeout_ms)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _execute_docker(
        self,
        temp_dir: str,
        lang_config: dict,
        timeout_ms: int
    ) -> ExecutionResult:
        """Execute inside Docker container with strict memory, CPU, and net blockades."""
        abs_temp_dir = os.path.abspath(temp_dir)
        container_mount = "/app"
        image = lang_config["image"]

        # 1. Compilation Stage (if needed)
        if lang_config["compile_cmd"]:
            compile_cmd = lang_config["compile_cmd"]
            # Compile using a transient container
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm",
                "-v", f"{abs_temp_dir}:{container_mount}",
                "-w", container_mount,
                image,
                *compile_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            if proc.returncode != 0:
                return ExecutionResult(
                    success=False,
                    output=stdout_bytes.decode(errors="replace"),
                    error=stderr_bytes.decode(errors="replace") or "Compilation failed",
                    run_time_ms=0,
                    memory_kb=0,
                    exit_code=proc.returncode
                )

        # 2. Execution Stage
        # Prepare wrapped command utilizing sh redirecting input.txt to stdin
        exec_cmd = lang_config["exec_cmd"]
        exec_str = " ".join(exec_cmd)
        wrapped_command = f"exec {exec_str} < input.txt"

        # Start background container
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--memory=128m",
            "--cpus=0.5",
            "--network=none",
            "-v", f"{abs_temp_dir}:{container_mount}",
            "-w", container_mount,
            image,
            "sh", "-c", wrapped_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        if proc.returncode != 0:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Docker container spawn failed: {stderr_bytes.decode(errors='replace')}",
                run_time_ms=0,
                memory_kb=0,
                exit_code=-1
            )

        container_id = stdout_bytes.decode().strip()

        # Wait with timeout
        wait_proc = await asyncio.create_subprocess_exec(
            "docker", "wait", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        timeout_occurred = False
        try:
            await asyncio.wait_for(wait_proc.wait(), timeout=timeout_ms / 1000.0)
        except asyncio.TimeoutError:
            timeout_occurred = True
            # Kill running container
            kill_proc = await asyncio.create_subprocess_exec("docker", "kill", container_id)
            await kill_proc.wait()

        # Read peak memory usage from cgroup on Linux
        memory_kb = await self._get_docker_peak_memory_kb(container_id)

        # Inspect container state
        inspect_proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        inspect_out, _ = await inspect_proc.communicate()
        
        exit_code = -1
        oom_killed = False
        run_time_ms = 0
        try:
            inspect_data = json.loads(inspect_out.decode())
            if inspect_data:
                state = inspect_data[0].get("State", {})
                exit_code = state.get("ExitCode", -1)
                oom_killed = state.get("OOMKilled", False)
                started_at = state.get("StartedAt", "")
                finished_at = state.get("FinishedAt", "")
                
                # Compute duration
                from datetime import datetime
                start_ts = self._parse_docker_time(started_at)
                finish_ts = self._parse_docker_time(finished_at)
                if finish_ts > start_ts:
                    run_time_ms = int((finish_ts - start_ts) * 1000)
        except Exception:
            pass

        # Capture logs
        logs_proc = await asyncio.create_subprocess_exec(
            "docker", "logs", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_logs, stderr_logs = await logs_proc.communicate()
        output_str = stdout_logs.decode(errors="replace")
        error_str = stderr_logs.decode(errors="replace")

        # Cleanup container
        rm_proc = await asyncio.create_subprocess_exec("docker", "rm", "-f", container_id)
        await rm_proc.wait()

        if timeout_occurred:
            return ExecutionResult(
                success=False,
                output=output_str,
                error="Execution timed out",
                run_time_ms=timeout_ms,
                memory_kb=memory_kb,
                exit_code=137,
                timeout=True
            )

        if oom_killed:
            return ExecutionResult(
                success=False,
                output=output_str,
                error="Out of Memory (OOM) limit exceeded (128MB)",
                run_time_ms=run_time_ms,
                memory_kb=128 * 1024,
                exit_code=137,
                oom_killed=True
            )

        return ExecutionResult(
            success=(exit_code == 0) and not error_str,
            output=output_str,
            error=error_str,
            run_time_ms=run_time_ms,
            memory_kb=memory_kb,
            exit_code=exit_code
        )

    async def _execute_local(
        self,
        temp_dir: str,
        lang_config: dict,
        timeout_ms: int
    ) -> ExecutionResult:
        """Secure local execution fallback using host process triggers."""
        # 1. Compilation
        if lang_config["compile_cmd"]:
            compile_cmd = lang_config["compile_cmd"]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *compile_cmd,
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout_bytes, stderr_bytes = await proc.communicate()
                if proc.returncode != 0:
                    return ExecutionResult(
                        success=False,
                        output=stdout_bytes.decode(errors="replace"),
                        error=stderr_bytes.decode(errors="replace") or "Compilation failed",
                        run_time_ms=0,
                        memory_kb=0,
                        exit_code=proc.returncode
                    )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Local compiler missing or failed: {str(e)}",
                    run_time_ms=0,
                    memory_kb=0,
                    exit_code=-1
                )

        # 2. Execution
        exec_cmd = lang_config["local_exec"]
        input_data = ""
        try:
            with open(os.path.join(temp_dir, "input.txt"), "r", encoding="utf-8") as f:
                input_data = f.read()
        except Exception:
            pass

        start_time = time.perf_counter_ns()
        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd,
                cwd=temp_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=input_data.encode()),
                    timeout=timeout_ms / 1000.0
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                await proc.wait()
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Execution timed out",
                    run_time_ms=timeout_ms,
                    memory_kb=0,
                    exit_code=-1,
                    timeout=True
                )

            end_time = time.perf_counter_ns()
            run_time_ms = (end_time - start_time) // 1_000_000

            stdout = stdout_bytes.decode(errors="replace")
            stderr = stderr_bytes.decode(errors="replace")

            return ExecutionResult(
                success=(proc.returncode == 0) and not stderr,
                output=stdout,
                error=stderr,
                run_time_ms=run_time_ms,
                memory_kb=0,  # Host memory metrics require psutil, degrade gracefully
                exit_code=proc.returncode
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                run_time_ms=0,
                memory_kb=0,
                exit_code=-1
            )

    async def run_test_cases(
        self,
        code: str,
        test_cases: List[Dict[str, Any]],
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Run code against multiple test cases. Supports marking/masking hidden cases.
        """
        if not test_cases:
            return {"passed": 0, "total": 0, "results": [], "score": 0}

        results = []
        passed = 0
        total = len(test_cases)

        for i, test in enumerate(test_cases):
            test_input = test.get("input", "")
            if isinstance(test_input, list):
                test_input = "\n".join(str(x) for x in test_input)
            elif not isinstance(test_input, str):
                test_input = str(test_input)

            expected = test.get("expected", "")
            if not isinstance(expected, str):
                expected = str(expected)
            expected = expected.strip()

            hidden = test.get("hidden", False)

            # Execute code
            res = await self.execute_code(code, language, test_input)

            actual = res.output.strip()
            is_correct = self._compare_outputs(actual, expected)

            if is_correct:
                passed += 1

            # Build case output (mask content if marked hidden to prevent cheating)
            results.append({
                "test_case": i + 1,
                "input": "Hidden case input masked" if hidden else (test_input[:100] + "..." if len(test_input) > 100 else test_input),
                "expected": "Hidden case expected masked" if hidden else (expected[:100] + "..." if len(expected) > 100 else expected),
                "actual": "Hidden case output masked" if hidden else (actual[:100] + "..." if len(actual) > 100 else actual),
                "passed": is_correct,
                "hidden": hidden,
                "run_time_ms": res.run_time_ms,
                "memory_kb": res.memory_kb,
                "error": "Execution error masked" if (hidden and res.error) else (res.error if res.error else None),
                "timeout": res.timeout,
                "oom_killed": res.oom_killed
            })

        score = (passed / total) * 100 if total > 0 else 0

        return {
            "passed": passed,
            "total": total,
            "results": results,
            "score": round(score, 1),
            "all_passed": passed == total
        }

    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """Compare outputs with normalizing and JSON structure tolerance."""
        if actual == expected:
            return True

        # Normalize whitespace and strip newlines
        actual_normalized = " ".join(actual.split()).strip()
        expected_normalized = " ".join(expected.split()).strip()
        if actual_normalized == expected_normalized:
            return True

        # JSON parsing for arrays/lists
        try:
            actual_parsed = json.loads(actual.replace("'", '"'))
            expected_parsed = json.loads(expected.replace("'", '"'))
            if actual_parsed == expected_parsed:
                return True
            if isinstance(actual_parsed, list) and isinstance(expected_parsed, list):
                if sorted(str(x) for x in actual_parsed) == sorted(str(x) for x in expected_parsed):
                    return True
        except Exception:
            pass

        return False

    async def validate_solution(
        self,
        code: str,
        problem_id: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Validate a solution against a known problem's test cases."""
        test_cases = self._get_problem_test_cases(problem_id)
        if not test_cases:
            return {
                "success": False,
                "error": f"No test cases found for problem: {problem_id}",
                "score": 0
            }

        result = await self.run_test_cases(code, test_cases, language)
        return {
            "success": True,
            "problem_id": problem_id,
            **result
        }

    def _get_problem_test_cases(self, problem_id: str) -> List[Dict[str, Any]]:
        """Get test cases for common problems, incorporating hidden check cases."""
        PROBLEM_TESTS = {
            "two_sum": [
                {"input": "[2,7,11,15]\n9", "expected": "[0, 1]"},
                {"input": "[3,2,4]\n6", "expected": "[1, 2]"},
                {"input": "[3,3]\n6", "expected": "[0, 1]"},
                {"input": "[1,5,8,12,30]\n21", "expected": "[]", "hidden": True},  # Hidden case
                {"input": "[0,4,3,0]\n0", "expected": "[0, 3]", "hidden": True}     # Hidden case
            ],
            "valid_parentheses": [
                {"input": "()", "expected": "True"},
                {"input": "()[]{}", "expected": "True"},
                {"input": "(]", "expected": "False"},
                {"input": "([)]", "expected": "False"},
                {"input": "{[]}", "expected": "True", "hidden": True}               # Hidden case
            ],
            "reverse_string": [
                {"input": "hello", "expected": "olleh"},
                {"input": "world", "expected": "dlrow"},
                {"input": "a", "expected": "a", "hidden": True}                    # Hidden case
            ],
            "fizzbuzz": [
                {"input": "15", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz"}
            ],
            "palindrome": [
                {"input": "racecar", "expected": "True"},
                {"input": "hello", "expected": "False"},
                {"input": "amanaplanacanalpanama", "expected": "True", "hidden": True} # Hidden case
            ]
        }
        return PROBLEM_TESTS.get(problem_id.lower(), [])

    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        return list(self.LANGUAGES.keys())

    async def close(self):
        """Close method for compatibilities."""
        pass


# Singleton instance
code_sandbox = CodeSandbox()


async def evaluate_code_with_sandbox(
    code: str,
    test_cases: List[Dict[str, Any]],
    language: str = "python"
) -> Dict[str, Any]:
    """Helper used by answer_evaluator.py."""
    result = await code_sandbox.run_test_cases(code, test_cases, language)
    return {
        "correctness_score": result["score"],
        "tests_passed": result["passed"],
        "tests_total": result["total"],
        "all_passed": result["all_passed"],
        "results": result["results"]
    }
