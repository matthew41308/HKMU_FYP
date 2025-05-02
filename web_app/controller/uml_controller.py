# src/uml_controller.py
import os
import base64
import subprocess
import traceback
from pathlib import Path
from typing import Tuple

from flask import jsonify, current_app
from config.external_ai_config import get_prompt, get_openai


# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────
def load_latest_txt(json_dir: str) -> Tuple[str, str]:
    """
    Return (file_name, file_content) for the newest *.txt file in `json_dir`.
    Raises ValueError if none exist.
    """
    txt_files = sorted(
        (p for p in Path(json_dir).glob("*.txt") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    if not txt_files:
        raise ValueError("No .txt file found in Json_toAI folder")

    latest = txt_files[-1]
    return latest.name, latest.read_text(encoding="utf-8")


def render_plantuml_to_pdf(uml_code: str, jar_path: str) -> bytes:
    """
    Run `plantuml.jar` in `-tpdf -pipe` mode and return the generated PDF bytes.
    Raises RuntimeError on non-zero exit.
    """
    cmd = ["java", "-jar", jar_path, "-DPLANTUML_LIMIT_SIZE=8192", "-tpdf", "-pipe", "-charset", "UTF-8"]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate(input=uml_code.encode("utf-8"), timeout=60)

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8") or "PlantUML rendering failed")

    return stdout


def sanitise_plantuml(raw: str) -> str:
    """
    Strip Markdown fences, ensure @startuml / @enduml are present.
    """
    code = (
        raw.replace("```plantuml", "")
        .replace("```uml", "")
        .replace("```", "")
        .strip()
    )

    if not code.lower().startswith("@startuml"):
        code = "@startuml\n" + code
    if not code.lower().rstrip().endswith("@enduml"):
        code = code.rstrip() + "\n@enduml"

    return code


# ────────────────────────────────────────────────────────────────────────────────
# Public entry point
# ────────────────────────────────────────────────────────────────────────────────
def generate_uml(document_type: str, json_dir: str):
    try:
        # ─── STEP 1: build prompt with file content ────────────────────────────
        file_name, exported_text = load_latest_txt(json_dir)
        prompt = get_prompt(document_type, exported_text)
        print(f"[uml_controller] sending file {file_name} ({len(exported_text)} bytes)")

        # ─── STEP 2: call OpenAI for PlantUML code ─────────────────────────────
        client = get_openai()

        response = client.chat.completions.create(
            model="o3-mini",
            max_completion_tokens=10_000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in generating optimized PlantUML diagrams. "
                        "Return ONLY valid PlantUML code wrapped in @startuml/@enduml. "
                        "No comments, no explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        ai_reply = response.choices[0].message.content.strip()
        if ai_reply == "0":
            return jsonify({"error": "AI determined this is not a valid technical document"}), 400

        # ─── STEP 3: sanitise PlantUML code ───────────────────────────────────
        uml_code = sanitise_plantuml(ai_reply)

        # ─── STEP 4: render PDF via PlantUML JAR ───────────────────────────────
        jar_path = current_app.config["PLANTUML_JAR_PATH"]
        if not os.path.isfile(jar_path):
            return jsonify({"error": f"PlantUML jar not found at {jar_path}"}), 500

        try:
            pdf_bytes = render_plantuml_to_pdf(uml_code, jar_path)
        except Exception as e:
            return jsonify({"error": f"PlantUML PDF generation failed: {e}"}), 500

        encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        return jsonify(
            {
                "pdf": encoded_pdf,
                "plantuml": uml_code,
            }
        )

    # ─── Error handling ────────────────────────────────────────────────────────
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            ),
            500,
        )