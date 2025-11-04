# SPOT Church Attendance Automation (AWS SAM + Lambda Container + Selenium)

Automates EasyTithe Plus attendance workflows for Saint Paul Ethiopian Orthodox Tewahedo Church (SPOT Church). The Lambda function logs in headlessly, navigates to Attendance Reports, and can switch tabs (e.g., Absences). Credentials are stored in AWS Secrets Manager.

## Architecture
- AWS SAM project (container image)
- AWS Lambda (Python 3.11) on x86_64
- Docker image (Debian bullseye) installs Chromium + ChromeDriver + required libs
- Selenium 3.141.0 with `urllib3<1.27` for compatibility
- AWS Secrets Manager for `{ "username": "...", "password": "..." }`
- CloudWatch Logs for observability

Key files:
- `easytithe_bot/hello_world/app.py` – Lambda handler (login, navigation, helpers)
- `easytithe_bot/hello_world/Dockerfile` – Container image with Chromium + ChromeDriver
- `easytithe_bot/template.yaml` – SAM template (`PackageType: Image`)
- `easytithe_bot/hello_world/requirements.txt` – Python deps

## Prerequisites
- Docker Desktop
- AWS CLI + credentials
- AWS SAM CLI
- (Apple Silicon) set `DOCKER_DEFAULT_PLATFORM=linux/amd64` when building/running

## Configuration
- Secret in AWS Secrets Manager (e.g., `easytithe/login-creds`) with contents:
```json
{ "username": "your_email", "password": "your_password" }
```
- `SECRET_NAME` is set in `template.yaml` under `Globals -> Function -> Environment -> Variables`.
- Region resolution in code: `REGION` → `AWS_REGION` → `AWS_DEFAULT_REGION` → `us-east-1`.

## Local run
```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64   # Apple Silicon only
cd easytithe_bot
sam build -t template.yaml
sam local invoke HelloWorldFunction -e events/event.json
```
- Look for `[NAV]` lines in output to see the current URL at each step.

## Deploy
```bash
cd easytithe_bot
sam build -t template.yaml
sam deploy --guided   # first time; creates ECR repo, saves samconfig
# subsequent updates
sam deploy
```
- Use the same Stack Name to update the existing function.

## Development notes
- Headless Chrome flags are tuned for Lambda: `--headless`, `--no-sandbox`, `--disable-dev-shm-usage`, `--single-process`, window size, and `/tmp` directories for cache/user-data.
- Navigation helpers:
  - Menu hover via ActionChains/JS, direct URL fallback to `/reports/attendance`.
  - `assert_on_attendance_reports(driver, wait)` verifies URL + tabs/table.
  - `click_attendance_tab(driver, wait, "Absences")` selects tabs reliably.
- URL breadcrumb logging: `log_url(driver, logger, msg)`.

## Troubleshooting
- Selenium 3 + urllib3 2.x ValueError:
  - Fixed by pinning `urllib3<1.27` in requirements.
- Binary/lib mismatch errors (e.g., exit 127, libX11) in zip-based Lambda:
  - Solved by using a container image that installs Chromium + ChromeDriver + libs.
- Element not interactable / zero-size menu items:
  - Use hover (ActionChains or JS `mouseover`) and JS `click()`; fall back to direct URL.
- Memory/timeouts:
  - Increase `Globals -> Function -> MemorySize` and `Timeout` in `template.yaml`.


