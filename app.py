from flask import Flask, request, jsonify, Response, render_template
from PyPDF2 import PdfMerger
from io import BytesIO
from urllib.parse import quote

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 파일 업로드 크기 제한: 10MB

# 파일 매핑 (원래 이름과 메모리 상 파일 매핑)
file_mapping = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files:
        app.logger.error("No files received")
        return jsonify({"error": "No files uploaded"}), 400

    global file_mapping

    # 새로 추가된 파일만 처리
    new_files = []
    for file in files:
        if not any(f["filename"] == file.filename for f in file_mapping):
            file_content = file.read()
            file_mapping.append({"filename": file.filename, "file": file_content})
            new_files.append({"original": file.filename, "random": file.filename})

    app.logger.info(f"Uploaded files: {[file.filename for file in files]}")
    return jsonify({"uploaded_files": new_files})

@app.route("/delete", methods=["POST"])
def delete_file():
    data = request.json
    filename = data.get("filename")

    global file_mapping
    file_mapping = [file for file in file_mapping if file["filename"] != filename]

    app.logger.info(f"Deleted file: {filename}")
    return jsonify({"message": "File deleted successfully"})

@app.route("/merge", methods=["POST"])
def merge():
    data = request.json
    file_order = data.get("file_order", [])
    output_name = data.get("output_name", "merged.pdf")

    if len(file_order) < 2:
        app.logger.error("Less than two files provided for merging")
        return jsonify({"error": "At least two files are required for merging"}), 400

    try:
        merger = PdfMerger()

        # 지정된 순서대로 파일 추가
        for filename in file_order:
            for file_obj in file_mapping:
                if file_obj["filename"] == filename:
                    file_data = BytesIO(file_obj["file"])
                    merger.append(file_data)

        # 메모리에서 병합된 PDF 반환
        merged_pdf = BytesIO()
        merger.write(merged_pdf)
        merger.close()
        merged_pdf.seek(0)

        # 병합 후 파일 목록 초기화
        file_mapping.clear()

        # 한글 파일 이름 처리
        encoded_output_name = quote(output_name)

        response = Response(merged_pdf.read(), mimetype="application/pdf")
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_output_name}"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        app.logger.info(f"Merged PDF created: {output_name}")
        return response

    except Exception as e:
        app.logger.error(f"Merge error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear():
    file_mapping.clear()
    app.logger.info("All files cleared")
    return jsonify({"message": "All files cleared"})

if __name__ == "__main__":
    app.run(debug=True)
