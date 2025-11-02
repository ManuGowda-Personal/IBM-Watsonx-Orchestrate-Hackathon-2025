from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import subprocess
import platform
import os
import requests
import logging
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for Watsonx/Postman/browser access

# --- ✅ Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# --- 1️⃣ Endpoint to run your monitoring script ---
@app.route('/run-monitor', methods=['POST'])
def run_monitor():
    script_path = r"C:\Users\MCTS-BLR-2067\monitor.sh"

    try:
        if platform.system() == "Windows":
            bash_path = r"C:\Program Files\Git\bin\bash.exe"
            if not os.path.exists(bash_path):
                return jsonify({"error": f"Git Bash not found at {bash_path}"}), 500

            result = subprocess.check_output(
                [bash_path, script_path],
                stderr=subprocess.STDOUT
            )
        else:
            result = subprocess.check_output(
                ["/bin/bash", script_path],
                stderr=subprocess.STDOUT
            )

        output = result.decode('utf-8')
        app.logger.info(f"✅ monitor.sh output:\n{output}")
        return jsonify({"output": output}), 200

    except subprocess.CalledProcessError as e:
        err = e.output.decode('utf-8')
        app.logger.error(f"❌ Script error: {err}")
        return jsonify({"error": err}), 500
    except Exception as e:
        app.logger.exception("Unexpected error running script")
        return jsonify({"error": str(e)}), 500


# --- 2️⃣ Universal Kubernetes API Proxy ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_k8s_any(path):
    kube_api = "https://127.0.0.1:59707"
    target_url = f"{kube_api}/{path}"

    # --- Copy headers safely ---
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}

    # --- Fix Content-Type for PATCH /scale ---
    if request.method.upper() == "PATCH" and path.endswith("/scale"):
        logging.info("🧩 Forcing Content-Type to application/merge-patch+json")
        headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        headers["Content-Type"] = "application/merge-patch+json"

    # --- Determine request body ---
    request_data = request.data

    if request.method.upper() == "PATCH" and path.endswith("/scale"):
        if not request_data or request_data == b'':
            # Try to parse replica count dynamically from Watsonx text or query
            import re
            desired_replicas = request.args.get("replicas", default=None, type=int)

            if not desired_replicas:
                # Watsonx often phrases: "Scaling bankapp deployment ... to 3 replicas"
                # So extract from natural language headers or query
                text = (
                    request.headers.get("X-Ibm-Wo-Transaction-Id", "") +
                    " " + request.full_path
                )
                match = re.search(r"\bto\s+(\d+)\b", text)
                if match:
                    desired_replicas = int(match.group(1))
                else:
                    desired_replicas = 2  # default fallback

            logging.warning(f"⚠️ Injecting dynamic body for scale: replicas={desired_replicas}")
            default_body = {"spec": {"replicas": desired_replicas}}
            request_data = json.dumps(default_body).encode("utf-8")

        logging.info(f"📦 Forwarding body: {request_data.decode()}")

    # --- Forward the request ---
    try:
        req_func = getattr(requests, request.method.lower())
        resp = req_func(
            target_url,
            headers=headers,
            data=request_data,
            verify=False
        )

        logging.info(f"⬅️ Response {resp.status_code}: {resp.text[:200]}")

        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json")
        )
    except Exception as e:
        logging.exception("Proxy error")
        return jsonify({"error": str(e)}), 500

        # --- 🔍 DEBUG: Log everything Watsonx sends ---
    logging.info("===== 🛰️ Incoming request from Watsonx =====")
    logging.info(f"➡️  Method: {request.method}")
    logging.info(f"➡️  Path: /{path}")
    logging.info(f"➡️  Headers:\n{json.dumps(dict(request.headers), indent=2)}")
    try:
        body_text = request.get_data(as_text=True)
        logging.info(f"➡️  Body:\n{body_text}")
    except Exception as e:
        logging.warning(f"Could not read body: {e}")
    logging.info("============================================")




# --- 3️⃣ App Runner ---
if __name__ == "__main__":
    app.logger.info("🚀 Starting monitor proxy server on port 8080...")
    app.run(host="0.0.0.0", port=8080)

