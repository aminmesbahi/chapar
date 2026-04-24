import argparse
import shutil


def deduplicate(list1_path: str, list2_path: str) -> None:
    """Remove emails in list2 from list1, writing the result back to list1.

    A backup of list1 is created as <list1_path>.bak before overwriting.
    """
    try:
        with open(list2_path, encoding="utf-8") as f:
            list2_emails = {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        raise SystemExit(f"Error: file not found: {list2_path}")

    try:
        with open(list1_path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise SystemExit(f"Error: file not found: {list1_path}")

    filtered = [line for line in lines if line.strip() and line.strip().lower() not in list2_emails]
    removed = len(lines) - len(filtered)

    # Back up list1 before overwriting
    shutil.copy2(list1_path, list1_path + ".bak")

    with open(list1_path, "w", encoding="utf-8") as f:
        f.writelines(filtered)

    print(f"Removed {removed} duplicate(s). {len(filtered)} entries remaining in {list1_path}.")
    print(f"Backup saved to {list1_path}.bak")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove emails in list2 from list1")
    parser.add_argument("list1", nargs="?", default="list1.txt", help="Path to the primary list (will be modified)")
    parser.add_argument("list2", nargs="?", default="list2.txt", help="Path to the exclusion list")
    args = parser.parse_args()
    deduplicate(args.list1, args.list2)