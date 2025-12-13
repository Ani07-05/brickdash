"""Test Supabase connection with detailed error reporting."""
import os
from pathlib import Path

# Load .env
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

url = os.environ.get('SUPABASE_DB_URL')
print(f"Connection string loaded: {url is not None}")
if url:
    print(f"Full URL: {url}")
    print(f"URL preview: {url[:50]}...")
    
    # Parse the URL to show components
    if url.startswith('postgresql://'):
        parts = url.replace('postgresql://', '').split('@')
        print(f"Parts after split: {len(parts)}")
        if len(parts) >= 2:
            # Take the last @ for hostname (in case @ appears in password)
            hostpart = parts[-1]
            creds = '@'.join(parts[:-1])
            user = creds.split(':')[0] if ':' in creds else creds
            host = hostpart.split(':')[0] if ':' in hostpart else hostpart.split('/')[0]
            port = hostpart.split(':')[1].split('/')[0] if ':' in hostpart else '5432'
            print(f"User: {user}")
            print(f"Host: {host}")
            print(f"Port: {port}")
    
    # Try connecting
    try:
        import psycopg
        print("\nAttempting connection...")
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"✅ Connected successfully!")
                print(f"Postgres version: {version[0][:50]}...")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if you have internet connectivity")
        print("2. Verify the Supabase URL is correct in .env")
        print("3. Ensure your password special characters are URL-encoded")
        print("   @ becomes %40, # becomes %23, _ stays as _")
        print("4. Check if your firewall/antivirus is blocking port 5432")
else:
    print("❌ SUPABASE_DB_URL not found in environment")
