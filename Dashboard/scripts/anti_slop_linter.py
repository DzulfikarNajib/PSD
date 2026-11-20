#!/usr/bin/env python3
"""AutoMatch Anti-Slop Linter & Quality Gate.

Automated enforcement of AutoMatch Design System, Anti-Slop Guidelines,
and quality rules (R-01 through R-38).

Usage:
    python scripts/anti_slop_linter.py [--fix] [--strict]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# ANSI colors for beautiful terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

FORBIDDEN_BUZZWORDS = [
    r"\bcutting[- ]edge\b",
    r"\brevolutionary\b",
    r"\bgame[- ]changer\b",
    r"\bnext[- ]gen\b",
    r"\bultra[- ]modern\b",
    r"\bai[- ]powered\b",
    r"\bseamlessly\b",
    r"\bmagic\b",
    r"\bunleash\b",
]

DEFAULT_ACTIVE_FILES = [
    "app.py",
    "pages/ikhtisar_pasar.py",
    "pages/eksplorasi_data.py",
    "pages/preprocessing_segmentasi.py",
    "pages/evaluasi_model.py",
    "pages/cek_harga_iklan.py",
    "pages/kesimpulan.py",
    "src/styles.py",
    "src/ui_components.py",
    "src/ui.py",
]


class Violation:
    def __init__(self, rule: str, file: str, line_no: int, snippet: str, message: str, severity: str = "ERROR"):
        self.rule = rule
        self.file = file
        self.line_no = line_no
        self.snippet = snippet
        self.message = message
        self.severity = severity  # "ERROR" or "WARN"

    def __str__(self) -> str:
        color = RED if self.severity == "ERROR" else YELLOW
        return (
            f"  {color}[{self.severity}] {self.rule}{RESET} in {BOLD}{self.file}:{self.line_no}{RESET}\n"
            f"    -> {self.message}\n"
            f"    {CYAN}|{RESET} {self.snippet.strip()}"
        )


def check_em_dash(file_path: Path, content: str) -> list[Violation]:
    """Rule R-02: Dilarang keras menggunakan karakter em dash (—)."""
    violations = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        if "—" in line:
            violations.append(
                Violation(
                    rule="R-02 (Anti-Slop Typography)",
                    file=str(file_path),
                    line_no=idx,
                    snippet=line,
                    message="Karakter em dash ('—') dilarang keras. Gunakan tanda hubung biasa ('-') atau kurung.",
                    severity="ERROR",
                )
            )
    return violations


def check_cliche_buzzwords(file_path: Path, content: str) -> list[Violation]:
    """Anti-Slop Copywriting: Hindari kata klise dan basa-basi generik AI."""
    violations = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # Ignore comments or internal docstring definitions
        if line.strip().startswith("#"):
            continue
        for pattern in FORBIDDEN_BUZZWORDS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                violations.append(
                    Violation(
                        rule="Anti-Slop Copywriting",
                        file=str(file_path),
                        line_no=idx,
                        snippet=line,
                        message=f"Ditemukan kata klise generik AI: '{match.group(0)}'. Gunakan bahasa faktual berbasis data.",
                        severity="ERROR",
                    )
                )
    return violations


def check_dummy_data_in_pages(file_path: Path, content: str) -> list[Violation]:
    """Rule R-17/R-38: Tidak boleh ada data dummy di halaman analitis aktif."""
    violations = []
    # Only check active user pages
    if not str(file_path).startswith("pages"):
        return violations

    lines = content.splitlines()
    dummy_patterns = [
        (r"\bnp\.random\.normal\b", "Penggunaan distribusi normal buatan (dummy)"),
        (r"\bnp\.random\.rand", "Penggunaan angka acak random (dummy)"),
        (r"dummy_data\s*=", "Deklarasi variabel data dummy"),
    ]
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            continue
        for pattern, desc in dummy_patterns:
            if re.search(pattern, line):
                violations.append(
                    Violation(
                        rule="R-17/R-38 (Data Integrity Guardrail)",
                        file=str(file_path),
                        line_no=idx,
                        snippet=line,
                        message=f"{desc} pada visualisasi aktif dilarang. Wajib menggunakan data aktual.",
                        severity="ERROR",
                    )
                )
    return violations


def check_excessive_emojis(file_path: Path, content: str) -> list[Violation]:
    """Rule Restraint: Hindari penggunaan emoji berlebihan pada heading."""
    violations = []
    lines = content.splitlines()
    emoji_regex = re.compile(
        r"[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF]"
    )
    for idx, line in enumerate(lines, start=1):
        # Check title / section markdown strings
        if line.strip().startswith(("st.title", "st.header", "st.subheader", "section_card", "page_header")):
            emojis = emoji_regex.findall(line)
            if len(emojis) > 1:
                violations.append(
                    Violation(
                        rule="Rule Restraint (Visual Noise)",
                        file=str(file_path),
                        line_no=idx,
                        snippet=line,
                        message=f"Terlalu banyak emoji ({len(emojis)} ditemukan) dalam satu judul. Maksimal 1 icon.",
                        severity="WARN",
                    )
                )
    return violations


def autofix_em_dash(file_path: Path) -> int:
    """Auto-replace forbidden em dashes with normal hyphens."""
    content = file_path.read_text(encoding="utf-8")
    count = content.count("—")
    if count > 0:
        fixed = content.replace("—", "-")
        file_path.write_text(fixed, encoding="utf-8")
    return count


def run_anti_slop_audit(
    root_dir: Path,
    target_rel_files: list[str] | None = None,
    auto_fix: bool = False,
    strict: bool = False,
) -> int:
    """Run all Anti-Slop checks across the specified files."""
    print(f"\n{BOLD}{BLUE}================================================================={RESET}")
    print(f"{BOLD}{BLUE}          AUTOMATCH ANTI-SLOP LINTER & QUALITY GATE             {RESET}")
    print(f"{BOLD}{BLUE}================================================================={RESET}\n")

    files_to_check = target_rel_files or DEFAULT_ACTIVE_FILES
    all_violations: list[Violation] = []
    total_scanned = 0
    total_fixed = 0

    for rel_path in files_to_check:
        full_path = root_dir / rel_path
        if not full_path.exists():
            continue

        total_scanned += 1
        content = full_path.read_text(encoding="utf-8")

        # Run checks
        all_violations.extend(check_em_dash(full_path, content))
        all_violations.extend(check_cliche_buzzwords(full_path, content))
        all_violations.extend(check_dummy_data_in_pages(full_path, content))
        all_violations.extend(check_excessive_emojis(full_path, content))

        if auto_fix:
            fixed_count = autofix_em_dash(full_path)
            if fixed_count > 0:
                total_fixed += fixed_count
                print(f"  {GREEN}[AUTO-FIX]{RESET} Replaced {fixed_count} em dash(es) in {rel_path}")

    # Report results
    errors = [v for v in all_violations if v.severity == "ERROR"]
    warnings = [v for v in all_violations if v.severity == "WARN"]

    print(f"File Terpindai: {BOLD}{total_scanned}{RESET} berkas")
    print(f"Status Pelanggaran: {RED}{len(errors)} Errors{RESET}, {YELLOW}{len(warnings)} Warnings{RESET}\n")

    if all_violations:
        print(f"{BOLD}Detail Pelanggaran Anti-Slop:{RESET}")
        for v in all_violations:
            print(v)
            print()

    if errors or (strict and warnings):
        print(f"{RED}{BOLD}[FAIL] Kepatuhan Anti-Slop Ditolak. Harap perbaiki pelanggaran di atas.{RESET}\n")
        return 1

    print(f"{GREEN}{BOLD}[PASS] 100% Bebas AI-Slop. Kode mematuhi standar desain AutoMatch!{RESET}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="AutoMatch Anti-Slop Linter")
    parser.add_argument("--fix", action="store_true", help="Otomatis perbaiki pelanggaran yang bisa difix (misal em dash)")
    parser.add_argument("--strict", action="store_true", help="Perlakukan warning sebagai error")
    parser.add_argument("--files", nargs="*", help="Daftar file spesifik untuk diperiksa")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    exit_code = run_anti_slop_audit(
        root_dir=root,
        target_rel_files=args.files,
        auto_fix=args.fix,
        strict=args.strict,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
