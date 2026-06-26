from pathlib import Path

# Update security.py to remove duplicate definition
security_path = Path("src/better_telegram_mcp/backends/security.py")
security_content = security_path.read_text()

# We know the duplicate is right at the top
find_duplicate = """_DNS_CACHE_TTL = 60.0

def clear_dns_cache() -> None:
    \"\"\"Clear the global DNS cache.\"\"\"
    _DNS_CACHE.clear()

def clear_dns_cache() -> None:
    \"\"\"Clear the global DNS cache.\"\"\"
    _DNS_CACHE.clear()"""

replace_duplicate = """_DNS_CACHE_TTL = 60.0

def clear_dns_cache() -> None:
    \"\"\"Clear the global DNS cache.\"\"\"
    _DNS_CACHE.clear()"""

security_content = security_content.replace(find_duplicate, replace_duplicate)
security_path.write_text(security_content)

print("patched")
