#!/usr/bin/env python3
"""Generate self-signed SSL certificate for HTTPS."""

import os
import subprocess
from pathlib import Path


def generate_self_signed_cert():
    """Generate a self-signed certificate using OpenSSL."""
    # Create certs directory
    certs_dir = Path(__file__).parent.parent / "certs"
    certs_dir.mkdir(exist_ok=True)

    cert_file = certs_dir / "cert.pem"
    key_file = certs_dir / "key.pem"

    print("Generating self-signed SSL certificate...")
    print(f"Certificate: {cert_file}")
    print(f"Private key: {key_file}")

    # Generate certificate using OpenSSL
    # Valid for 365 days
    cmd = [
        "openssl", "req", "-x509",
        "-newkey", "rsa:4096",
        "-keyout", str(key_file),
        "-out", str(cert_file),
        "-days", "365",
        "-nodes",
        "-subj", "/CN=localhost/O=ADO AI Web Service/C=US"
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("\n✓ Certificate generated successfully!")
        print(f"\nCertificate location: {cert_file}")
        print(f"Private key location: {key_file}")
        print("\nIMPORTANT: This is a self-signed certificate.")
        print("Your browser will show a security warning. This is expected.")
        print("You can safely proceed by accepting the certificate.")
        print("\nThe web service will now be available at: https://localhost:8000")

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error generating certificate: {e}")
        print(f"STDERR: {e.stderr}")
        print("\nMake sure OpenSSL is installed:")
        print("  macOS: brew install openssl")
        print("  Ubuntu/Debian: apt-get install openssl")
        print("  Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        return False
    except FileNotFoundError:
        print("\n✗ OpenSSL not found!")
        print("Please install OpenSSL:")
        print("  macOS: brew install openssl")
        print("  Ubuntu/Debian: apt-get install openssl")
        print("  Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        return False

    return True


if __name__ == "__main__":
    generate_self_signed_cert()
