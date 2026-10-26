
from fastapi_mail import FastMail, MessageSchema
import secrets
import time
import sqlite3

from app.core.config import config


class OTP:
    def __init__(self):
        self.OTP_EXPIRY_SECONDS = config.OTP_EXPIRY_SECONDS
        self.DB_NAME = config.DB_NAME

        self.CONN_CONFIG = config.email_conf

    def init_db(self):
        """Create the database and table if they don't exist."""
        with sqlite3.connect(self.DB_NAME) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS otp_verification (
                    email TEXT NOT NULL,
                    otp TEXT NOT NULL,
                    contact_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'verified', 'expired')),
                    created_at INTEGER NOT NULL
                )
            """)


    async def send_otp_email(self, otp: str, email: str):
        """
        Send OTP to requesting user.

        Args: 
            otp: str = OTP code generated
            email: str = Email of recepient.
        
        Returns:
            Email sending status.
        """
        message = MessageSchema(
            subject="RTD Huttons",
            recipients=[email],
            body=f"""
            <html>
                <body>
                    <h2>RTD Hub Email Verification OTP</h2>
                    <p>Your email verification code is:</p>
                    <h1>{otp}</h1>
                    <p>Please do not share this code with anyone.</p>
                </body>
            </html>
            """,
            subtype="html",
        )

        try:
            await FastMail(self.CONN_CONFIG).send_message(message)
            return {
                "Status": True,
                "Message": "OTP sent."
            }
        except Exception as e:
            print(e)
            return {
                "Status": False,
                "Message": e
            }

    async def generate_otp(self, email: str, contact_id: str) -> str:
        """
        Generate an OTP for the same chat ID and email.

        Args: 
            email: str = Email of recepient.
            contact_id: str = Contact ID of the user.
        
        Returns:
            Generated OTP.
        """
        email = email.strip().lower()
        contact_id = contact_id.strip()

        if not email or not contact_id:
            return "Email and contact_id are required."

        otp = f"{secrets.randbelow(1_000_000):06d}"
        created_at = int(time.time())

        with sqlite3.connect(self.DB_NAME, timeout=10) as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT email, status
                FROM otp_verification
                WHERE contact_id = ?
                """,
                (contact_id,)
            ).fetchone()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO otp_verification
                        (email, otp, contact_id, status, created_at)
                    VALUES (?, ?, ?, 'pending', ?)
                    """,
                    (email, otp, contact_id, created_at)
                )
                await self.send_otp_email(otp, email)
                return {
                    "Status": True,
                    "OTP": otp
                }

            stored_email, status = row

            if stored_email.strip().lower() != email:
                return {
                    "Status": False,
                    "Message": "This chat ID is already registered with a different email."
                }

            if status == "verified":
                return {
                    "Status": False,
                    "Message": "This email has already been verified for this chat ID."
                }

            conn.execute(
                """
                UPDATE otp_verification
                SET otp = ?, status = 'pending', created_at = ?
                WHERE contact_id = ?
                """,
                (otp, created_at, contact_id)
            )
        await self.send_otp_email(otp, email)
        return {
            "Status": True,
            "OTP": otp
        }


    async def verify_otp(self, contact_id: str, otp: str) -> str:
        """
        Verify an OTP and return its status.

        Args: 
            contact_id: str = Contact ID of the user.
            otp: str = Generated OTP.

        Returns:
            "verified"  - OTP successfully verified.
            "pending"   - OTP is incorrect but has not expired.
            "expired"   - OTP has expired.
            "not_found" - No record exists for this contact ID.
        """
        with sqlite3.connect(self.DB_NAME, timeout=10) as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT otp, created_at, status
                FROM otp_verification
                WHERE contact_id = ?
                """,
                (contact_id.strip(),)
            ).fetchone()

            if row is None:
                return "not_found"

            stored_otp, created_at, status = row

            if status == "verified":
                return "verified"

            if status == "expired":
                return "expired"

            if status != "pending":
                return f"unknown_status: {status}"

            if time.time() - created_at >= self.OTP_EXPIRY_SECONDS:
                conn.execute(
                    """
                    UPDATE otp_verification
                    SET status = 'expired'
                    WHERE contact_id = ?
                    """,
                    (contact_id.strip(),)
                )
                return "expired"

            if not secrets.compare_digest(stored_otp, otp.strip()):
                return "pending"

            conn.execute(
                """
                UPDATE otp_verification
                SET status = 'verified'
                WHERE contact_id = ?
                """,
                (contact_id.strip(),)
            )

            return "verified"

otp_service = OTP()

otp_service.init_db()

async def test():
    otp_ser = OTP()

    email = input("Enter email address: ").strip()
    contact_id = input("Enter chat ID: ").strip()

    try:
        otp = await otp_ser.generate_otp(email, contact_id)
        print("Generated OTP:", otp)
        print("Send this OTP to the email using your email service.")

        entered_otp = input("Enter OTP to verify: ").strip()

        if await otp_ser.verify_otp(contact_id, entered_otp):
            print("OTP verified successfully!")
        else:
            print("Invalid, expired, or already-used OTP.")

    except ValueError as e:
        print(f"Request rejected: {e}")
