"""Check setup without network I/O; send a test only with explicit confirmation."""
import argparse
import json

from app.core.config import settings
from app.services.notifications import configuration_status, send_test_email


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-test", action="store_true", help="Send one test; does not enable alert delivery")
    parser.add_argument("--confirm-recipient", help="Must match one address in NOTIFICATION_EMAIL_TO")
    args = parser.parse_args(argv)
    status = configuration_status(settings)
    print(json.dumps(status))
    if not args.send_test:
        print("Configuration check only. No SMTP connection or email attempted.")
        return 0 if status["configured"] else 1
    if not args.confirm_recipient:
        parser.error("--send-test requires --confirm-recipient")
    try:
        send_test_email(args.confirm_recipient, settings)
    except Exception as exc:
        # Exception messages from providers may contain sensitive details.
        print(json.dumps({"test": "failed", "error_type": type(exc).__name__}))
        return 1
    print("SMTP accepted the test. Check the recipient inbox/spam; acceptance is not proof of delivery.")
    print("No alert records were queued or modified. Automatic delivery settings are unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
