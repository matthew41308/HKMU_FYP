# src/uml_controller.py
import os
import base64
import traceback
from pathlib import Path
from typing import Tuple

from flask import jsonify
import graphviz

from config.external_ai_config import get_prompt, get_openai, upload_file_for_chat


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



def generate_uml(document_type: str, json_dir: str):
    try:
        # ─── STEP 1: build the prompt ───────────────────────────────────────────
        prompt = get_prompt(document_type)
        file_name, exported_text = load_latest_txt(json_dir)
        print(f"uml_controller file name : {file_name}")
        # ─── STEP 2: call OpenAI for DOT code ───────────────────────────────────
        client = get_openai()

        file_id = upload_file_for_chat(client, file_name, exported_text)

        response = client.chat.completions.create(
            
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in generating optimized Code of Graphviz diagrams."
                    "Return ONLY valid DOT or digraph code."
                },
                {"role": "user", 
                 "content": prompt,
                 "file_ids":[file_id]
                 },
            ],
            model="o3-mini",
            max_completion_tokens=10000
        )

        ai_reply = response.choices[0].message.content.strip()
        client.files.delete(file_id)
        if ai_reply == "0":
            return jsonify({"error": "AI determined this is not a valid technical document"}), 400

        # ─── STEP 3: sanitise Graphviz code ─────────────────────────────────────
        gv_code = (
            ai_reply.replace("```graphviz", "")
            .replace("```dot", "")
            .replace("```", "")
            .strip()
        )

        if not (gv_code.lstrip().startswith("digraph") or gv_code.lstrip().startswith("graph")):
            gv_code = f"digraph G {{\n{gv_code}\n}}"

        # ─── STEP 4: render as PDF in-memory ────────────────────────────────────
        try:
            dot = graphviz.Source(gv_code, format="pdf")
            pdf_output: bytes = dot.pipe()
        except Exception as e:
            return jsonify({"error": f"Graphviz PDF generation failed: {e}"}), 500

        encoded_pdf = base64.b64encode(pdf_output).decode("utf-8")

        return jsonify(
            {
                "pdf": encoded_pdf,
                "dot": gv_code,
            }
        )

    except ValueError as ve:
        # Custom 404 for “no txt files”
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