# cronwatch

Lightweight daemon that monitors cron job execution and sends alerts on failure or missed runs.

## Installation

```bash
pip install cronwatch
```

## Usage

Define your monitored jobs in a YAML config file:

```yaml
# cronwatch.yml
jobs:
  - name: daily-backup
    schedule: "0 2 * * *"
    alert_after: 10m
    notify:
      - email: ops@example.com

  - name: hourly-sync
    schedule: "0 * * * *"
    alert_after: 5m
    notify:
      - slack: "#alerts"
```

Start the daemon:

```bash
cronwatch --config cronwatch.yml
```

Wrap your existing cron commands to report status:

```bash
# In your crontab
0 2 * * * cronwatch-run daily-backup /usr/local/bin/backup.sh
```

cronwatch will send an alert if a job fails, exits with a non-zero code, or does not run within the expected window.

## Configuration Options

| Key | Description | Default |
|---|---|---|
| `schedule` | Standard cron expression for expected run time | *(required)* |
| `alert_after` | Grace period before a missed run triggers an alert | `5m` |
| `notify` | List of alert channels (email, slack, webhook) | *(required)* |
| `timeout` | Kill the job and alert if it runs longer than this duration | *(none)* |
| `retries` | Number of times to retry a failed job before alerting | `0` |

## License

MIT
