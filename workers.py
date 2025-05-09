
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
from shopify import ShopifyAPI
from database import save_produto, get_produto_by_id, update_produto_status

openai = OpenAI(api_key="SUA_OPENAI_KEY")

def extrair_dados_aliexpress(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    titulo = soup.find("h1")
    descricao = soup.find("meta", {"name": "description"})
    imagens = [img["src"] for img in soup.find_all("img") if "src" in img.attrs and "jpg" in img["src"]][:5]

    return {
        "titulo_original": titulo.text.strip() if titulo else "Produto",
        "descricao_original": descricao["content"] if descricao else "",
        "imagens": imagens,
        "preco_original": 0
    }

def gerar_conteudo_ia(titulo, descricao, nicho, tom, idioma):
    prompt = f"""
    Você é um especialista em e-commerce. Reescreva o título e a descrição abaixo para um produto da categoria '{nicho}', com um tom '{tom}'. Responda em {idioma}. Também gere até 10 tags SEO:

    Título: {titulo}
    Descrição: {descricao}
    """
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )
    texto = response.choices[0].message.content
    linhas = texto.split("\n")
    return {
        "titulo_ia": linhas[0].strip(),
        "descricao_ia": "\n".join(linhas[1:-1]).strip(),
        "tags_ia": linhas[-1].replace("Tags:", "").strip().split(",")
    }

def enviar_para_shopify(produto, loja_token):
    api = ShopifyAPI(token=loja_token)
    api.post_product({
        "title": produto.titulo_ia,
        "body_html": produto.descricao_ia,
        "tags": ",".join(produto.tags_ia),
        "images": [{"src": url} for url in produto.imagens],
        "variants": [{"price": produto.preco_original}]
    })

def processar_importacao(url, usuario_id, loja_id, loja_token, presets):
    try:
        dados = extrair_dados_aliexpress(url)
        produto_id = save_produto(dados, usuario_id, loja_id)
        update_produto_status(produto_id, "gerando")

        ia_resultado = gerar_conteudo_ia(
            dados["titulo_original"],
            dados["descricao_original"],
            presets.get("nicho", "geral"),
            presets.get("tom", "amigável"),
            presets.get("idioma", "português")
        )

        produto = get_produto_by_id(produto_id)
        produto.titulo_ia = ia_resultado["titulo_ia"]
        produto.descricao_ia = ia_resultado["descricao_ia"]
        produto.tags_ia = ia_resultado["tags_ia"]

        update_produto_status(produto_id, "importando")
        enviar_para_shopify(produto, loja_token)

        update_produto_status(produto_id, "importado")
    except Exception as e:
        print("Erro:", e)
        update_produto_status(produto_id, "erro")
