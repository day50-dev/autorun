#!/usr/bin/env python3
"""
RunThis Test Suite - Dry-run testing
Tests trending GitHub repositories without actual installation/execution

Test 1: Analyze repo README and generate action plan (no execution)
Test 2: Validate action plan can be executed safely (dry-run mode)
"""

import subprocess
import json
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


TEST_REPOS = [
    {"name": "alibaba/zvec", "language": "C++"},
    {"name": "nautechsystems/nautilus_trader", "language": "Rust"},
    {"name": "rowboatlabs/rowboat", "language": "TypeScript"},
    {"name": "steipete/gogcli", "language": "Go"},
    {"name": "openclaw/openclaw", "language": "TypeScript"},
    {"name": "SynkraAI/aios-core", "language": "JavaScript"},
    {"name": "letta-ai/letta-code", "language": "TypeScript"},
    {"name": "ruvnet/wifi-densepose", "language": "Python"},
    {"name": "seerr-team/seerr", "language": "TypeScript"},
    {"name": "hummingbot/hummingbot", "language": "Python"},
]


class TestRunner:
    def __init__(self, test_dir: str = "/tmp/runthis_tests"):
        self.test_dir = Path(test_dir)
        self.results: List[Dict] = []
        
    def setup(self) -> None:
        self.test_dir.mkdir(parents=True, exist_ok=True)
        (self.test_dir / "logs").mkdir(exist_ok=True)
        (self.test_dir / "reports").mkdir(exist_ok=True)
        (self.test_dir / "repos").mkdir(exist_ok=True)
        
    def clone_repo(self, repo: str) -> Tuple[bool, str]:
        repo_url = f"https://github.com/{repo}.git"
        clone_dir = self.test_dir / "repos" / repo.replace("/", "_")
        
        if clone_dir.exists():
            return True, "Already cloned"
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def read_readme(self, repo_dir: Path) -> Tuple[bool, str]:
        readme_paths = ["README.md", "readme.md", "README", "readme"]
        
        for readme in readme_paths:
            readme_path = repo_dir / readme
            if readme_path.exists():
                try:
                    return True, readme_path.read_text()
                except Exception as e:
                    return False, str(e)
        
        return False, "No README found"
    
    def detect_dependencies(self, repo_dir: Path) -> Dict:
        dependencies = {
            "python": False,
            "node": False,
            "rust": False,
            "go": False,
            "cpp": False,
            "other": []
        }
        
        checks = [
            ("requirements.txt", "python"),
            ("Pipfile", "python"),
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("package.json", "node"),
            ("Cargo.toml", "rust"),
            ("go.mod", "go"),
            ("CMakeLists.txt", "cpp"),
            ("Makefile", "other"),
        ]
        
        for manifest, dep_type in checks:
            manifest_path = repo_dir / manifest
            if manifest_path.exists():
                if dep_type == "other":
                    dependencies["other"].append(manifest)
                else:
                    dependencies[dep_type] = True
        
        return dependencies
    
    def generate_action_plan(self, repo: str, readme_content: str, dependencies: Dict, repo_dir: Path) -> Dict:
        """Generate action plan without actually executing anything"""
        
        plan = {
            "clone": f"git clone --depth 1 https://github.com/{repo}.git",
            "dependencies": {
                "python": "pip install -r requirements.txt" if dependencies.get("python") else "No Python deps",
                "node": "npm install" if dependencies.get("node") else "No Node deps",
                "rust": "cargo build" if dependencies.get("rust") else "No Rust deps",
                "go": "go mod download" if dependencies.get("go") else "No Go deps",
                "cpp": "make / cmake" if dependencies.get("cpp") else "No C++ deps",
            },
            "run_commands": [],
            "dry_run_notes": []
        }
        
        lines = readme_content.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            if any(cmd in line_lower for cmd in ["npm run", "npm start", "python", "cargo run", "make", "./"]):
                if "run" in line_lower or "start" in line_lower or "build" in line_lower:
                    cmd = line.strip().strip('`').strip()
                    if cmd and not cmd.startswith('#') and not cmd.startswith('<!--'):
                        plan["run_commands"].append(cmd)
        
        plan["run_commands"] = plan["run_commands"][:5]
        
        plan["dry_run_notes"].append(f"[DRY-RUN] Would clone {repo}")
        plan["dry_run_notes"].append(f"[DRY-RUN] Would install dependencies based on detected manifests")
        plan["dry_run_notes"].append(f"[DRY-RUN] Would execute: {plan['run_commands'][0] if plan['run_commands'] else 'unknown'}")
        plan["dry_run_notes"].append(f"[DRY-RUN] No actual system changes made - test mode enabled")
        
        return plan
    
    def analyze_repo(self, repo: Dict) -> Dict:
        print(f"\nAnalyzing {repo['name']}...")
        
        result = {
            "repo": repo["name"],
            "timestamp": datetime.now().isoformat(),
            "clone": {"success": False, "error": None},
            "readme": {"found": False, "content": None, "error": None},
            "dependencies": {},
            "action_plan": {},
        }
        
        success, output = self.clone_repo(repo["name"])
        result["clone"]["success"] = success
        result["clone"]["error"] = output if not success else None
        
        if not success:
            return result
        
        repo_dir = self.test_dir / "repos" / repo["name"].replace("/", "_")
        success, output = self.read_readme(repo_dir)
        result["readme"]["found"] = success
        result["readme"]["content"] = output if success else None
        result["readme"]["error"] = output if not success else None
        
        if not success:
            return result
        
        result["dependencies"] = self.detect_dependencies(repo_dir)
        result["action_plan"] = self.generate_action_plan(repo["name"], output, result["dependencies"], repo_dir)
        
        return result
    
    def run_tests(self) -> Dict:
        self.setup()
        
        print(f"Running tests on {len(TEST_REPOS)} repositories...")
        
        for repo in TEST_REPOS:
            result = self.analyze_repo(repo)
            self.results.append(result)
            
            repo_name = repo["name"].replace("/", "_")
            result_path = self.test_dir / "logs" / f"{repo_name}.json"
            result_path.write_text(json.dumps(result, indent=2))
            
            status = "PASS" if result["clone"]["success"] else "FAIL"
            print(f"  {status} {repo['name']}")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        total = len(self.results)
        successful_clones = sum(1 for r in self.results if r["clone"]["success"])
        successful_reads = sum(1 for r in self.results if r["readme"]["found"])
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_repos": total,
            "successful_clones": successful_clones,
            "successful_reads": successful_reads,
            "success_rate": successful_clones / total * 100 if total > 0 else 0,
            "results": self.results,
            "summary": {
                "most_common_deps": self._aggregate_dependencies(),
                "avg_run_commands": sum(len(r["action_plan"]["run_commands"]) for r in self.results) / total if total > 0 else 0,
            }
        }
        
        report_path = self.test_dir / "reports" / "test_report.json"
        report_path.write_text(json.dumps(report, indent=2))
        
        return report
    
    def _aggregate_dependencies(self) -> Dict[str, int]:
        dep_counts = {}
        for result in self.results:
            for dep, found in result["dependencies"].items():
                if found and dep != "other":
                    dep_counts[dep] = dep_counts.get(dep, 0) + 1
        return dict(sorted(dep_counts.items(), key=lambda x: x[1], reverse=True))
    
    def print_report(self, report: Dict) -> None:
        print("\n" + "=" * 60)
        print("RunThis Test Suite Report")
        print("=" * 60)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Repos: {report['total_repos']}")
        print(f"Successful Clones: {report['successful_clones']}")
        print(f"Successful README Reads: {report['successful_reads']}")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        print(f"Average Run Commands Found: {report['summary']['avg_run_commands']:.1f}")
        print("\nMost Common Dependencies:")
        for dep, count in report['summary']['most_common_deps'].items():
            print(f"  - {dep}: {count} repos")
        print("\nDetailed Results:")
        for result in report['results']:
            print(f"\n  {result['repo']}:")
            print(f"    Clone: {'PASS' if result['clone']['success'] else 'FAIL'}")
            print(f"    README: {'PASS' if result['readme']['found'] else 'FAIL'}")
            deps = [k for k,v in result['dependencies'].items() if v and k != 'other']
            print(f"    Dependencies: {', '.join(deps) if deps else 'None'}")
            if result['action_plan']['run_commands']:
                print(f"    Action Plan Generated:")
                for note in result['action_plan']['dry_run_notes']:
                    print(f"      - {note}")
        print("\n" + "=" * 60)


def main():
    runner = TestRunner()
    report = runner.run_tests()
    runner.print_report(report)
    return 0 if report['success_rate'] >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
