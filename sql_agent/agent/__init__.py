"""
SQL Debugging & Optimization Agent
==================================
An intelligent pair-programmer agent that diagnoses SQL errors, semantic bugs,
and performance bottlenecks, proposes verified rewrites, and explains the fixes.
"""

from .core import SQLAgent
from .models import AnalysisResult, OptimizationReport

__all__ = ["SQLAgent", "AnalysisResult", "OptimizationReport"]
