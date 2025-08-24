# test_shutil_copy2.py
import shutil
import os

# Create empty test file
with open("test_empty.txt", "w") as f:
    pass

# Check sizes
print(f"Source size: {os.path.getsize('test_empty.txt')} bytes")

# Copy using same method as your app
shutil.copy2("test_empty.txt", "test_copy.txt")

# Check target
print(f"Target size: {os.path.getsize('test_copy.txt')} bytes")

# Check for corruption
with open("test_copy.txt", "rb") as f:
    content = f.read()
    if content:
        print(f"CORRUPTION: {len(content)} bytes of garbage found!")
        print(f"First 20 bytes: {content[:20]}")
    else:
        print("OK: File remained empty")
