"""Apply the gallery's keepalive configuration to cron-job.org."""

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def mismatched_fields(expected, actual):
    for key, value in expected.items():
        observed = actual.get(key)
        if isinstance(value, dict) and isinstance(observed, dict):
            for child in mismatched_fields(value, observed):
                yield f"{key}.{child}"
        elif value != observed:
            yield key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--job-id", type=int, help="Update the existing job")
    args = parser.parse_args()

    api_key = os.environ.get("CRON_JOB_ORG_API_KEY")
    if not api_key:
        parser.error("Set CRON_JOB_ORG_API_KEY in the environment.")
    if args.job_id is not None and args.job_id <= 0:
        parser.error("--job-id must be positive.")

    config = Path(__file__).resolve().parents[1] / "monitoring/render-keepalive.json"
    url = "https://api.cron-job.org/jobs"
    if args.job_id is not None:
        url = f"{url}/{args.job_id}"
    payload = config.read_bytes()
    request = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="PUT" if args.create else "PATCH",
    )
    try:
        with urlopen(request, timeout=30) as response:
            job_id = json.load(response)["jobId"] if args.create else args.job_id
        verification = Request(
            f"https://api.cron-job.org/jobs/{job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urlopen(verification, timeout=30) as response:
            actual = json.load(response)["jobDetails"]
        mismatches = list(mismatched_fields(json.loads(payload)["job"], actual))
        if mismatches:
            parser.exit(1, "Job settings differ after update: " + ", ".join(mismatches) + "\n")
    except HTTPError as error:
        parser.exit(1, f"cron-job.org returned HTTP {error.code}.\n")
    except (URLError, TimeoutError):
        parser.exit(1, "Could not confirm the update. Check the console before retrying.\n")

    except (ValueError, KeyError, TypeError, AttributeError):
        parser.exit(1, "Unexpected API response. Check the job in the console.\n")

    print(f"Applied and verified keepalive configuration to cron-job.org job {job_id}.")


if __name__ == "__main__":
    main()
