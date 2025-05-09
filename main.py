
from flask import Flask, request, jsonify
from flask_cors import CORS
from workers import processar_importacao

app = Flask(__name__)
CORS(app)

@app.route("/api/processar", methods=["POST"])
def importar():
    data = request.json
    url = data.get("url")
    usuario_id = data.get("usuario_id")
    loja_id = data.get("loja_id")
    loja_token = data.get("loja_token")
    presets = data.get("presets", {})

    try:
        processar_importacao(url, usuario_id, loja_id, loja_token, presets)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
