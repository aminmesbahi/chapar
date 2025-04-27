list1_path = "list1.txt"
list2_path = "list2.txt"

with open(list2_path, encoding="utf-8") as f:
    list2_emails = set(line.strip().lower() for line in f if line.strip())

with open(list1_path, encoding="utf-8") as f:
    filtered = [line for line in f if line.strip() and line.strip().lower() not in list2_emails]

with open(list1_path, "w", encoding="utf-8") as f:
    f.writelines(filtered)