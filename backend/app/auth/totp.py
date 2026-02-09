"""TOTP/MFA utility functions."""

import io

import pyotp
import qrcode
import qrcode.image.svg


def generate_totp_secret() -> str:
    """Generate a random TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, username: str, issuer: str = "MeshManager") -> str:
    """Get the otpauth:// provisioning URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_qr_code_svg(uri: str) -> str:
    """Generate an SVG QR code for the given URI."""
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(uri, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code against the secret, allowing +-1 time window."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
