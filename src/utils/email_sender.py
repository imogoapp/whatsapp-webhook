import requests

def send_reset_email(nome, email, senha):
    payload = {
        "nome": nome,
        "email": email,
        "senha": senha
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.post("https://smtp.josuejuca.com/imogoSenha", json=payload, headers=headers)
    return response.status_code == 200