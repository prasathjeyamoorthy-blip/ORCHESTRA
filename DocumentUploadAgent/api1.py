import os
import tempfile
from flask import Flask, request, send_from_directory, jsonify, abort

import main as ppp_main

app = Flask(__name__, static_folder="static", static_url_path="/static")

# serve the simple frontend
@app.route("/")
def home():
    return app.send_static_file("index.html")


def _save_temp(upload) -> str:
    suffix = os.path.splitext(upload.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = upload.read()
        tmp.write(content)
        return tmp.name


@app.route("/validate", methods=["POST"])
def validate():
    # at least one document should be provided; others are optional
    if not request.files:
        abort(400, "No files uploaded")

    # gather files if present
    aadhaar_file = request.files.get("aadhaar")
    ration_file = request.files.get("ration")
    address_file = request.files.get("address")

    # check types of provided files
    for label, f in [("aadhaar", aadhaar_file), ("ration", ration_file),
                     ("address", address_file)]:
        if f and f.content_type != "application/pdf":
            abort(400, f"{label} file must be a PDF")

    # save them temporarily
    paths = {}
    if aadhaar_file:
        paths['aadhaar'] = _save_temp(aadhaar_file)
    if ration_file:
        paths['ration'] = _save_temp(ration_file)
    if address_file:
        paths['address'] = _save_temp(address_file)

    try:
        result = ppp_main.process_documents(
            paths.get('aadhaar'),
            paths.get('ration'),
            paths.get('address')
        )
    except Exception as exc:
        abort(500, str(exc))
    finally:
        # cleanup
        for path in paths.values():
            try:
                os.remove(path)
            except Exception:
                pass

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
