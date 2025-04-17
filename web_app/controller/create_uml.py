import os
import traceback
import base64
from flask import jsonify, current_app
from config.external_ai_config import get_prompt, get_openai
import graphviz

def generate_uml_controller(document_type: str, json_dir):
    try:
        # STEP 0: Configure the environment for Graphviz.
        # Set the custom Graphviz folder location.
        # Assuming your custom Graphviz installation is located at /graphviz,
        # and the dot executable is at /graphviz/usr/bin/dot:
        custom_dot_path = "/graphviz/usr/bin"
        
        
        os.environ["GRAPHVIZ_DOT"] = os.path.join(custom_dot_path, "dot")
        
        # STEP 1: Generate the full prompt for AI.
        prompt_template = get_prompt(document_type)
        txt_files = [f for f in os.listdir(json_dir) if f.endswith(".txt")]
        if not txt_files:
            return jsonify({"error": "No .txt file found in Json_toAI folder"}), 404

        txt_path = os.path.join(json_dir, txt_files[-1])
        with open(txt_path, "r", encoding="utf-8") as f:
            exported_text = f.read()

        full_prompt = (
            f"Please help me generate this document type: {document_type}. "
            "If it is not a technical document for project management, please respond with 0 only.\n\n"
            + prompt_template
            + exported_text
        )

        # STEP 2: Get the Graphviz (DOT) code from the AI using the OpenAI API.
        client = get_openai()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in generating optimized Graphviz diagrams."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0,
            max_tokens=4096
        )

        ai_reply = response.choices[0].message.content.strip()
        if ai_reply == "0":
            return jsonify({"error": "AI determines this is not a valid technical document"}), 400

        # Clean up the Graphviz code from the response (remove triple backticks, if any).
        gv_code = ai_reply.replace("```graphviz", "").replace("```", "").strip()

        # Check if the code starts with a valid Graphviz directive.
        if not (gv_code.startswith("digraph") or gv_code.startswith("graph")):
            # Assume the returned code is the body of a digraph and wrap it.
            gv_code = "digraph G {\n" + gv_code + "\n}"

        # STEP 3: Generate the diagram in-memory using Graphviz as a PDF.
        try:
            # Create a Graphviz source object with the DOT code, set format to pdf.
            dot = graphviz.Source(gv_code, format="pdf")
            pdf_output = dot.pipe()  # Returns a bytes object.
        except Exception as e:
            return jsonify({"error": f"Graphviz PDF generation failed: {str(e)}"}), 500

        # Encode the PDF file to a base64 string.
        encoded_pdf = base64.b64encode(pdf_output).decode("utf-8")

        # Return a JSON response containing both the PDF and the DOT text.
        return jsonify({
            "pdf": encoded_pdf,
            "dot": gv_code
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500