"""
One-command seed: runs ALL seed scripts in the correct order.
Usage: python seed_all.py
"""
import subprocess, sys
scripts = ["seed_iuc.py", "seed_structure.py", "seed_classes_students.py", "seed_timetable.py", "prepare_demo.py"]
for s in scripts:
    print(f"\n{'='*60}\nRUNNING: {s}\n{'='*60}")
    result = subprocess.run([sys.executable, s], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR in {s}:")
        print(result.stderr)
        sys.exit(1)
    if result.stderr and "ERROR" in result.stderr:
        print(result.stderr)
print(f"\n{'='*60}\nALL SEED SCRIPTS COMPLETE\n{'='*60}")
print("\nDemo credentials:")
print("  Admin:    A001 / admin123")
print("  Teacher:  T002 / teacher123 (or any Txxx)")
print("  Student:  S0010 / student123 (or any Sxxxx)")
print("  Employer: E002 / employer123 (or any Exxx)")
