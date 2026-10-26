# Run COOLForge on AWS Graviton

This is the deployment procedure, not evidence of a completed deployment. No AWS
resource is provisioned by the local build. The operator owns instance costs and access.

1. Subscribe to the official [OpenCV Graviton4 Marketplace offering](https://aws.amazon.com/marketplace/pp/prodview-fdvbfiewzuehs).
   Select a release containing OpenCV 5. Region-specific AMI IDs are intentionally not baked in.
2. Launch a compatible Arm instance from that AMI. The vendor lists c8g/m8g/r8g
   families. Choose capacity within your budget; record instance type, region, AMI release,
   vCPU count, CPU model, and COOL version alongside measurements.
3. Restrict SSH to your IP. Use the AMI's documented SSH account/key. Do not put keys
   or AWS credentials in this repository. An IAM role is unnecessary for this app.
4. Clone your private repository using your normal authorized GitHub access. Enter its directory.
5. Run the application-only installer:

```bash
bash deploy/aws/install_on_cool_ami.sh
source /opt/cool/venvs/python_3.12/bin/activate
python scripts/verify_cool.py --json results/environment.json --require-cool
python scripts/evaluate.py --dataset data/eval
python scripts/autotune.py --dataset data/eval --max-iterations 12
python scripts/benchmark_worker.py --name cool --dataset data/eval --warmups 5 --iterations 30 --output results/cool.json
python -m streamlit run app.py --server.address 127.0.0.1
```

The installer generates 50 images if no dataset exists, runs tests, and evaluates a
smoke workload. It installs application dependencies only; OpenCV stays supplied by
the AMI. If its Python path differs, set `COOL_PYTHON` to the actual vendor interpreter.
Do not use the project's `local` installation extra on this AMI.

## Stock baseline

Prepare a separate Python environment with stock OpenCV 5 of the same upstream version
on this same instance. Use the official OpenCV build instructions for that version;
record source revision and build flags. A generic OpenCV 4 wheel is not a final baseline.
Do not copy COOL's `PYTHONPATH`/`LD_LIBRARY_PATH` into the stock shell. Confirm its
`cv2.__file__` is outside `/opt/cool`, and its build is independent of COOL.

```bash
# Set this to the actual interpreter you prepared; no imaginary default is assumed.
export STOCK_PYTHON=/absolute/path/to/your/stock/python
python scripts/benchmark_matrix.py --stock-python "$STOCK_PYTHON" --cool-python /opt/cool/venvs/python_3.12/bin/python --dataset data/eval --warmups 5 --iterations 30
python scripts/benchmark_matrix.py --stock-python "$STOCK_PYTHON" --cool-python /opt/cool/venvs/python_3.12/bin/python --dataset data/eval --warmups 5 --iterations 30 --order cool-first
```

Inspect both worker logs and generated reports under `results/matrix/`. Repeat pairs
on an otherwise idle host. See [benchmark methodology](../../BENCHMARKS.md).

## Demo access

For a private demo, keep the app on localhost and use an SSH tunnel:

```bash
ssh -L 8501:127.0.0.1:8501 ubuntu@YOUR_INSTANCE_PUBLIC_IP
```

Open `http://localhost:8501`. Replace the account if your AMI uses a different one.
For a public-IP demo, install Nginx and use [the supplied proxy config](../nginx/coolforge.conf).
Allow inbound TCP 80 only from intended viewers where possible; do not expose 8501.
HTTP public-IP demos are for nonsensitive synthetic images. Use TLS and appropriate
authentication before accepting private uploads. A domain is not required for the demo.

For persistence, copy the repository to `/srv/coolforge`, create an unprivileged
`coolforge` service account with read access to the repository and vendor Python, and
install [the systemd template](../systemd/coolforge.service). Adjust its paths if needed.
Make `/srv/coolforge/results` writable by that account. Validate Nginx with `sudo nginx -t`
before reload. Run `sudo systemctl daemon-reload` and `sudo systemctl enable --now coolforge`.
Inspect `journalctl -u coolforge` and the endpoint before sharing it.

Stop/terminate the EC2 instance after judging, and remove unused volumes/IP allocations.
No cloud cost or Graviton acceleration claim is made until your actual artifacts exist.

## Verification limits and sources

The verifier requires Arm64, OpenCV 5, the COOL installation root, a loaded `cv2`
inside that root, and affirmative acceleration build markers. Some vendor builds may
not expose these markers and will conservatively remain unverified. Preserve the
full build information and consult the vendor; do not weaken the gate to get a green card.
Build provenance is not a proof that every operation dispatched to an accelerated kernel.

Deployment paths and compatible families were checked against the official Marketplace
usage instructions on 2026-10-26. Also see [OpenCV COOL](https://opencv.org/COOL/).
