"""Job dependency tracking — ensures dependent jobs run after their parents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from cronwatch.config import CronwatchConfig


@dataclass
class DependencyGraph:
    """Directed graph of job dependencies."""

    # job_name -> list of job names it depends on
    _deps: Dict[str, List[str]] = field(default_factory=dict)

    def add(self, job: str, depends_on: List[str]) -> None:
        """Register that *job* must run after all jobs in *depends_on*."""
        self._deps[job] = list(depends_on)

    def dependencies_of(self, job: str) -> List[str]:
        """Return the direct dependencies of *job* (empty list if none)."""
        return list(self._deps.get(job, []))

    def all_jobs(self) -> Set[str]:
        """Return every job name mentioned in the graph."""
        names: Set[str] = set()
        for job, deps in self._deps.items():
            names.add(job)
            names.update(deps)
        return names

    def has_cycle(self) -> bool:
        """Return True if the dependency graph contains a cycle."""
        visited: Set[str] = set()
        stack: Set[str] = set()

        def _dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for neighbour in self._deps.get(node, []):
                if neighbour not in visited:
                    if _dfs(neighbour):
                        return True
                elif neighbour in stack:
                    return True
            stack.discard(node)
            return False

        for job in list(self._deps):
            if job not in visited:
                if _dfs(job):
                    return True
        return False


def build_graph(cfg: CronwatchConfig) -> DependencyGraph:
    """Build a DependencyGraph from a loaded CronwatchConfig."""
    graph = DependencyGraph()
    for job in cfg.jobs:
        deps = getattr(job, "depends_on", None) or []
        if deps:
            graph.add(job.name, deps)
    return graph


def blocking_dependencies(
    job: str,
    graph: DependencyGraph,
    successful_jobs: Set[str],
) -> List[str]:
    """Return dependencies of *job* that have NOT yet succeeded."""
    return [
        dep
        for dep in graph.dependencies_of(job)
        if dep not in successful_jobs
    ]
