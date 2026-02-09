"""Tests for TOTP utility functions."""

import re

from app.auth.totp import (
    generate_qr_code_svg,
    generate_totp_secret,
    get_provisioning_uri,
    verify_totp_code,
)


class TestTotpUtilities:
    """Tests for TOTP utility functions."""

    def test_generate_secret(self):
        """generate_totp_secret should return a base32 string."""
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0
        # Base32 characters
        assert re.match(r"^[A-Z2-7]+=*$", secret)

    def test_generate_secret_unique(self):
        """Each call should produce a different secret."""
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        assert s1 != s2

    def test_provisioning_uri(self):
        """get_provisioning_uri should return an otpauth URI."""
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "testuser")
        assert uri.startswith("otpauth://totp/")
        assert "testuser" in uri
        assert "MeshManager" in uri

    def test_provisioning_uri_custom_issuer(self):
        """get_provisioning_uri should use custom issuer."""
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "testuser", issuer="CustomApp")
        assert "CustomApp" in uri

    def test_generate_qr_code_svg(self):
        """generate_qr_code_svg should return SVG markup."""
        secret = generate_totp_secret()
        uri = get_provisioning_uri(secret, "testuser")
        svg = generate_qr_code_svg(uri)
        assert isinstance(svg, str)
        assert "<svg" in svg.lower()
        assert "</svg>" in svg.lower()

    def test_verify_valid_code(self):
        """verify_totp_code should accept valid codes."""
        import pyotp

        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp_code(secret, code) is True

    def test_verify_invalid_code(self):
        """verify_totp_code should reject invalid codes."""
        secret = generate_totp_secret()
        assert verify_totp_code(secret, "000000") is False
